from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from discord_course_bots.portal_backend import (
    CASE_LOOKUP_PATH,
    EMAIL_START_PATH,
    EMAIL_VERIFY_PATH,
    HEALTH_PATH,
    JOIN_CSRF_COOKIE,
    JOIN_PATH,
    JOIN_SCOPE,
    JOIN_SESSION_COOKIE,
    LOOKUP_CSRF_COOKIE,
    LOOKUP_SCOPE,
    LOOKUP_SESSION_COOKIE,
    SESSION_PATH,
    ForwardedClientAddressError,
    InMemoryAuditSink,
    PortalBackend,
    PortalBackendSettings,
    PortalRequest,
    PortalStore,
    RateLimiter,
    SignedSessionAuthorizer,
    SQLiteAuditSink,
    SqlitePortalStore,
    resolve_client_key,
)

ORIGIN = "https://portal.example"
HOST = "portal.example"
CSRF = "csrf-token-for-tests"


def backend_for(
    tmp_path: Path,
    *,
    audit: Any | None = None,
    store: PortalStore | None = None,
    rate_limiter: RateLimiter | None = None,
) -> tuple[PortalBackend, SignedSessionAuthorizer, SqlitePortalStore | PortalStore, str]:
    actual_store = store or SqlitePortalStore(tmp_path / "portal.sqlite3")
    sessions = SignedSessionAuthorizer(b"s" * 32)
    session = sessions.issue_for_test("student-session")
    backend = PortalBackend(
        actual_store,
        settings=PortalBackendSettings(ORIGIN, secure_cookies=False),
        sessions=sessions,
        audit=audit or InMemoryAuditSink(),
        rate_limiter=rate_limiter,
    )
    return backend, sessions, actual_store, session


def request(
    session: str,
    path: str,
    payload: dict[str, str],
    *,
    origin: str | None = ORIGIN,
    host: str = HOST,
    csrf: str | None = CSRF,
    client_key: str = "test-client",
) -> PortalRequest:
    lookup = path == CASE_LOOKUP_PATH
    session_cookie = LOOKUP_SESSION_COOKIE if lookup else JOIN_SESSION_COOKIE
    csrf_cookie = LOOKUP_CSRF_COOKIE if lookup else JOIN_CSRF_COOKIE
    headers = {
        "Host": host,
        "Cookie": f"{session_cookie}={session}; {csrf_cookie}={CSRF}",
        "Content-Type": "application/json",
    }
    if origin is not None:
        headers["Origin"] = origin
    if csrf is not None:
        headers["X-CSRF-Token"] = csrf
    return PortalRequest(
        method="POST",
        target=path,
        headers=headers,
        body=json.dumps(payload).encode("utf-8"),
        client_key=client_key,
    )


def student_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "identityType": "STUDENT",
        "discordUsername": "student.name",
        "ntuEmail": "student@ntu.edu.tw",
        "classCode": "01",
        "rulesPrivacy": "yes",
    }
    payload.update(overrides)
    return payload


def lookup_payload(case_number: str) -> dict[str, str]:
    return {"caseNumber": case_number}


def session_request(
    scope: str,
    *,
    origin: str = ORIGIN,
    host: str = HOST,
    cookie: str | None = None,
    client_key: str = "test-client",
) -> PortalRequest:
    headers = {
        "Host": host,
        "Origin": origin,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if cookie:
        headers["Cookie"] = cookie
    return PortalRequest(
        method="POST",
        target=SESSION_PATH,
        headers=headers,
        body=f"scope={scope}".encode(),
        client_key=client_key,
    )


def verified_payload(
    store: SqlitePortalStore, session: str, payload: dict[str, str]
) -> dict[str, str]:
    identity = payload["identityType"]
    destination = payload["ntuEmail"] if identity == "STUDENT" else payload["guestEmail"]
    challenge_id = store.repository.start_email_verification(
        session_subject="student-session",
        destination=destination,
        email_kind="INSTITUTIONAL" if identity == "STUDENT" else "CONTACT",
    )
    row = store.repository._connection.execute(
        "SELECT verification_code FROM email_delivery_outbox WHERE challenge_id = ?",
        (challenge_id,),
    ).fetchone()
    assert row is not None
    assert store.repository.verify_email_challenge(
        challenge_id=challenge_id,
        session_subject="student-session",
        verification_code=str(row["verification_code"]),
    )
    return {**payload, "emailVerificationId": challenge_id}


def test_join_revalidates_and_uses_canonical_sqlite_store(tmp_path: Path) -> None:
    audit = InMemoryAuditSink()
    backend, _, store, session = backend_for(tmp_path, audit=audit)
    response = backend.handle(
        request(session, JOIN_PATH, verified_payload(store, session, student_payload()))
    )

    assert response.status == 202
    assert response.json()["outcome"] == "ACCEPTED"
    assert len(store.repository.pending_join_applications()) == 1  # type: ignore[union-attr]
    assert [record.event_type for record in audit.records] == [
        "PORTAL_JOIN_ATTEMPT",
        "PORTAL_JOIN_STORED",
    ]
    assert "student@ntu.edu.tw" not in json.dumps(audit.records, default=str)


def test_duplicate_join_is_idempotent_and_generic(tmp_path: Path) -> None:
    backend, _, store, session = backend_for(tmp_path)
    first = backend.handle(
        request(session, JOIN_PATH, verified_payload(store, session, student_payload()))
    )
    second = backend.handle(
        request(
            session,
            JOIN_PATH,
            verified_payload(store, session, student_payload(classCode="C02")),
        )
    )

    assert first.status == second.status == 202
    assert first.body == second.body


@pytest.mark.parametrize(
    "overrides",
    [
        {"ntuEmail": "student@example.com"},
        {"contactGmail": "student@example.com"},
        {"classCode": "C17"},
        {"discordUsername": "student name"},
        {"rulesPrivacy": "no"},
        {"guestReason": "unexpected"},
    ],
)
def test_join_rejects_invalid_fields(tmp_path: Path, overrides: dict[str, str]) -> None:
    backend, _, store, session = backend_for(tmp_path)
    response = backend.handle(request(session, JOIN_PATH, student_payload(**overrides)))

    assert response.status == 400
    assert response.json()["error"] == "INVALID_REQUEST"
    assert not store.repository.pending_join_applications()  # type: ignore[union-attr]


def test_guest_join_maps_to_visitor_and_revalidates(tmp_path: Path) -> None:
    backend, _, store, session = backend_for(tmp_path)
    payload = {
        "identityType": "GUEST",
        "discordUsername": "visitor.name",
        "guestEmail": "visitor@example.com",
        "guestReason": "我是旁聽學生，希望加入討論。",
        "rulesPrivacy": "yes",
    }
    response = backend.handle(
        request(session, JOIN_PATH, verified_payload(store, session, payload))
    )

    assert response.status == 202
    row = store.repository.pending_join_applications()[0]  # type: ignore[union-attr]
    assert row["applicant_type"] == "VISITOR"
    assert row["class_code"] is None


def test_auth_origin_and_csrf_fail_closed(tmp_path: Path) -> None:
    backend, _, _, session = backend_for(tmp_path)
    payload = student_payload()

    unauthenticated = backend.handle(request("not-a-valid-session", JOIN_PATH, payload))
    foreign_origin = backend.handle(
        request(session, JOIN_PATH, payload, origin="https://evil.example")
    )
    missing_csrf = backend.handle(request(session, JOIN_PATH, payload, csrf=None))
    wrong_host = backend.handle(request(session, JOIN_PATH, payload, host="evil.example"))

    assert unauthenticated.status == 401
    assert foreign_origin.status == 403
    assert missing_csrf.status == 403
    assert wrong_host.status == 403


def test_health_is_minimal_no_store_and_does_not_touch_store(tmp_path: Path) -> None:
    class ExplodingStore:
        def __getattribute__(self, name: str) -> Any:
            if name.startswith("__"):
                return object.__getattribute__(self, name)
            raise AssertionError(f"health touched store attribute {name}")

    backend = PortalBackend(
        ExplodingStore(),  # type: ignore[arg-type]
        settings=PortalBackendSettings(ORIGIN),
        sessions=SignedSessionAuthorizer(b"s" * 32),
        audit=InMemoryAuditSink(),
    )
    response = backend.handle(
        PortalRequest(method="GET", target=HEALTH_PATH, headers={"Host": HOST})
    )

    assert response.status == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "Set-Cookie" not in response.headers


def test_forwarded_client_is_only_used_for_an_explicit_trusted_proxy() -> None:
    trusted = frozenset({"127.0.0.1"})

    assert resolve_client_key("203.0.113.9", ("198.51.100.7",), trusted) == "203.0.113.9"
    assert resolve_client_key("127.0.0.1", ("198.51.100.7",), trusted) == "198.51.100.7"


@pytest.mark.parametrize(
    "forwarded",
    [(), ("198.51.100.7, 198.51.100.8",), (" 198.51.100.7",), ("2001:0db8::1",)],
)
def test_trusted_proxy_requires_one_canonical_forwarded_ip(
    forwarded: tuple[str, ...],
) -> None:
    with pytest.raises(ForwardedClientAddressError):
        resolve_client_key("127.0.0.1", forwarded, frozenset({"127.0.0.1"}))


def test_trusted_proxy_configuration_requires_canonical_ip_literals() -> None:
    with pytest.raises(ValueError, match="canonical"):
        PortalBackendSettings(ORIGIN, trusted_proxy_ips=frozenset({"2001:0db8::1"}))


def test_csrf_seed_is_same_origin_and_no_store(tmp_path: Path) -> None:
    backend, _, _, session = backend_for(tmp_path)
    response = backend.handle(
        PortalRequest(
            method="GET",
            target=JOIN_PATH,
            headers={"Host": HOST, "Cookie": f"{JOIN_SESSION_COOKIE}={session}"},
            client_key="test-client",
        )
    )

    assert response.status == 204
    assert response.body == b""
    assert "Set-Cookie" in response.headers
    assert response.headers["Cache-Control"] == "no-store"


def test_session_issuer_sets_separate_secure_scope_cookies(tmp_path: Path) -> None:
    store = SqlitePortalStore(tmp_path / "portal.sqlite3")
    sessions = SignedSessionAuthorizer(b"s" * 32)
    backend = PortalBackend(
        store,
        settings=PortalBackendSettings(ORIGIN),
        sessions=sessions,
        audit=InMemoryAuditSink(),
    )
    try:
        response = backend.handle(session_request(LOOKUP_SCOPE))
    finally:
        store.close()

    assert response.status == 201
    assert response.json() == {
        "schemaVersion": "1.0",
        "outcome": "ISSUED",
        "scope": LOOKUP_SCOPE,
        "expiresIn": 1_800,
    }
    cookies = response.headers["Set-Cookie"]
    assert isinstance(cookies, tuple)
    assert len(cookies) == 2
    assert cookies[0].startswith(f"{LOOKUP_SESSION_COOKIE}=")
    assert "HttpOnly" in cookies[0]
    assert "Secure" in cookies[0]
    assert cookies[1].startswith(f"{LOOKUP_CSRF_COOKIE}=")
    assert "HttpOnly" not in cookies[1]
    assert all("SameSite=Strict" in cookie for cookie in cookies)
    assert all("; Path=/;" in cookie for cookie in cookies)
    assert response.headers["Cache-Control"] == "no-store"


def test_session_issuer_is_same_origin_scoped_and_rate_limited(tmp_path: Path) -> None:
    backend, _, _, _ = backend_for(
        tmp_path,
        rate_limiter=RateLimiter(limit=10, window_seconds=60),
    )
    backend.issuer_rate_limiter = RateLimiter(limit=1, window_seconds=60)

    foreign = backend.handle(session_request(JOIN_SCOPE, origin="https://evil.example"))
    invalid = backend.handle(session_request("OWNER"))
    first = backend.handle(session_request(JOIN_SCOPE, client_key="issuer-client"))
    second = backend.handle(session_request(JOIN_SCOPE, client_key="issuer-client"))

    assert foreign.status == 403
    assert invalid.status == 400
    assert first.status == 201
    assert second.status == 429


def test_join_and_lookup_sessions_cannot_cross_scopes(tmp_path: Path) -> None:
    backend, sessions, _, _ = backend_for(tmp_path)
    join_only = sessions.issue_for_test("join-only", scopes=(JOIN_SCOPE,))
    lookup_only = sessions.issue_for_test("lookup-only", scopes=(LOOKUP_SCOPE,))

    lookup_with_join = backend.handle(
        request(join_only, CASE_LOOKUP_PATH, lookup_payload("C01-7K4M2Q-0702-1000"))
    )
    join_with_lookup = backend.handle(request(lookup_only, JOIN_PATH, student_payload()))

    assert lookup_with_join.status == 401
    assert join_with_lookup.status == 401


def test_session_signature_expiry_tamper_and_key_rotation() -> None:
    old = SignedSessionAuthorizer(
        b"o" * 32,
        key_id="old",
        max_age_seconds=300,
        clock_skew_seconds=0,
        now=lambda: 1_000,
    )
    token = old.issue_for_test("rotating-session", scopes=(LOOKUP_SCOPE,))
    request_with_token = PortalRequest(
        method="POST",
        target=CASE_LOOKUP_PATH,
        headers={"Cookie": f"{LOOKUP_SESSION_COOKIE}={token}"},
    )
    rotated = SignedSessionAuthorizer(
        b"n" * 32,
        key_id="new",
        previous_keys={"old": b"o" * 32},
        max_age_seconds=300,
        clock_skew_seconds=0,
        now=lambda: 1_100,
    )
    expired = SignedSessionAuthorizer(
        b"o" * 32,
        key_id="old",
        max_age_seconds=300,
        clock_skew_seconds=0,
        now=lambda: 1_301,
    )
    tampered_token = token[:-1] + ("A" if token[-1] != "A" else "B")
    tampered = PortalRequest(
        method="POST",
        target=CASE_LOOKUP_PATH,
        headers={"Cookie": f"{LOOKUP_SESSION_COOKIE}={tampered_token}"},
    )

    assert (
        rotated.authorize(
            request_with_token,
            required_scope=LOOKUP_SCOPE,
            cookie_name=LOOKUP_SESSION_COOKIE,
        )
        == "rotating-session"
    )
    assert (
        expired.authorize(
            request_with_token,
            required_scope=LOOKUP_SCOPE,
            cookie_name=LOOKUP_SESSION_COOKIE,
        )
        is None
    )
    assert (
        rotated.authorize(
            tampered,
            required_scope=LOOKUP_SCOPE,
            cookie_name=LOOKUP_SESSION_COOKIE,
        )
        is None
    )


def test_undocumented_get_case_status_route_is_not_available(tmp_path: Path) -> None:
    backend, _, _, session = backend_for(tmp_path)
    response = backend.handle(
        PortalRequest(
            method="GET",
            target="/api/cases/status?caseNumber=C01-7K4M2Q-0702-1000",
            headers={"Host": HOST, "Cookie": f"{LOOKUP_SESSION_COOKIE}={session}"},
            client_key="test-client",
        )
    )

    assert response.status == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_rate_limit_is_per_route_and_generic(tmp_path: Path) -> None:
    backend, _, store, session = backend_for(
        tmp_path, rate_limiter=RateLimiter(limit=1, window_seconds=60)
    )
    payload = verified_payload(store, session, student_payload())
    first = backend.handle(request(session, JOIN_PATH, payload))
    second = backend.handle(request(session, JOIN_PATH, payload))

    assert first.status == 202
    assert second.status == 429
    assert second.json() == {"error": "RATE_LIMITED", "message": "請稍後再試。"}


def test_lookup_returns_only_allowlisted_general_projection(tmp_path: Path) -> None:
    backend, _, store, session = backend_for(tmp_path)
    repo = store.repository  # type: ignore[union-attr]
    case_number = repo.create_case(
        case_id="case-portal-lookup",
        thread_id=123,
        author_id=456,
        ai_content_permission=False,
        module_code="M1",
        keyword="極限",
        canonical_title="[M1 | C01][極限] 不應公開",
        initial_snapshot={"body": "private student question"},
        class_code="01",
    )
    repo.set_case_jump_url(123, "https://discord.com/channels/100/200")
    response = backend.handle(request(session, CASE_LOOKUP_PATH, lookup_payload(case_number)))
    body = response.json()

    assert response.status == 200
    assert body["outcome"] == "FOUND"
    assert set(body["case"]) == {
        "caseNumber",
        "caseType",
        "status",
        "updatedAt",
        "teachingTeamReplied",
        "discordUrl",
    }
    assert body["case"]["caseType"] == "GENERAL"
    assert "private student question" not in json.dumps(body)
    assert "case-portal-lookup" not in json.dumps(body)


def test_private_lookup_is_content_free_and_supports_p_suffix(tmp_path: Path) -> None:
    backend, _, store, session = backend_for(tmp_path)
    repo = store.repository  # type: ignore[union-attr]
    case_number = repo.create_case(
        case_id="case-private-lookup",
        thread_id=124,
        author_id=457,
        ai_content_permission=False,
        canonical_title="[M1 | C99][隱密支援] 不應公開",
        initial_snapshot={"body": "private support body"},
        private_support=True,
    )
    repo.set_case_jump_url(124, "https://discord.com/channels/100/201")
    response = backend.handle(
        request(session, CASE_LOOKUP_PATH, lookup_payload(case_number.lower()))
    )

    assert response.status == 200
    assert response.json()["case"]["caseType"] == "PRIVATE_SUPPORT"
    assert response.json()["case"]["caseNumber"] == case_number
    assert "private support body" not in response.body.decode()


def test_lookup_invalid_and_missing_are_minimal(tmp_path: Path) -> None:
    backend, _, _, session = backend_for(tmp_path)
    invalid = backend.handle(request(session, CASE_LOOKUP_PATH, lookup_payload("not-a-case")))
    missing = backend.handle(
        request(session, CASE_LOOKUP_PATH, lookup_payload("C01-7K4M2Q-0702-1000"))
    )

    assert invalid.json()["outcome"] == "INVALID"
    assert missing.json()["outcome"] == "NOT_FOUND"
    assert invalid.json()["case"] is None
    assert missing.json()["case"] is None
    assert "cases" not in json.dumps(missing.json()).lower()


def test_lookup_and_audit_fail_closed_without_raw_error(tmp_path: Path) -> None:
    backend, _, _, session = backend_for(tmp_path)
    malformed = backend.handle(
        request(
            session,
            CASE_LOOKUP_PATH,
            {"caseNumber": "C01-7K4M2Q-0702-1000", "extra": "list-all"},
        )
    )
    assert malformed.status == 400
    assert "list-all" not in malformed.body.decode()

    class FailingStore:
        def safe_case_projection(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("raw database details must not escape")

        def submit_join_application(self, **_kwargs: Any) -> tuple[dict[str, Any], bool]:
            raise RuntimeError("storage down")

    failing_backend, _, _, failing_session = backend_for(tmp_path / "failure", store=FailingStore())
    failed = failing_backend.handle(
        request(
            failing_session,
            CASE_LOOKUP_PATH,
            lookup_payload("C01-7K4M2Q-0702-1000"),
        )
    )
    assert failed.status == 503
    assert "raw database details" not in failed.body.decode()


def test_audit_failure_fails_closed_before_join_storage(tmp_path: Path) -> None:
    class FailingAudit:
        def append(self, _record: Any) -> None:
            raise RuntimeError("audit unavailable")

    backend, _, store, session = backend_for(tmp_path, audit=FailingAudit())
    response = backend.handle(
        request(session, JOIN_PATH, verified_payload(store, session, student_payload()))
    )

    assert response.status == 503
    assert not store.repository.pending_join_applications()  # type: ignore[union-attr]


def test_sqlite_audit_sink_persists_only_metadata(tmp_path: Path) -> None:
    audit = SQLiteAuditSink(tmp_path / "audit.sqlite3")
    backend, _, store, session = backend_for(tmp_path / "operational", audit=audit)
    response = backend.handle(
        request(session, JOIN_PATH, verified_payload(store, session, student_payload()))
    )

    assert response.status == 202
    rows = audit._connection.execute(
        "SELECT event_type, route, outcome, actor_fingerprint FROM portal_audit_events"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        ("PORTAL_JOIN_ATTEMPT", JOIN_PATH, "ATTEMPT", rows[0][3]),
        ("PORTAL_JOIN_STORED", JOIN_PATH, "ACCEPTED", rows[1][3]),
    ]
    assert rows[0][3] == rows[1][3]
    assert "student@ntu.edu.tw" not in json.dumps(rows, default=str)
    assert len(store.repository.pending_join_applications()) == 1  # type: ignore[union-attr]
    audit.close()


def test_email_verification_routes_bind_code_to_session_and_hide_code(tmp_path: Path) -> None:
    backend, _, store, session = backend_for(tmp_path)
    started = backend.handle(
        request(
            session,
            EMAIL_START_PATH,
            {"identityType": "STUDENT", "email": "student@ntu.edu.tw"},
        )
    )
    assert started.status == 202
    challenge_id = started.json()["challengeId"]
    assert "verification_code" not in started.body.decode()
    row = store.repository._connection.execute(
        "SELECT verification_code FROM email_delivery_outbox WHERE challenge_id = ?",
        (challenge_id,),
    ).fetchone()
    verified = backend.handle(
        request(
            session,
            EMAIL_VERIFY_PATH,
            {"challengeId": challenge_id, "code": str(row["verification_code"])},
        )
    )
    assert verified.status == 200
    assert verified.json()["outcome"] == "VERIFIED"


def test_join_rejects_unverified_email(tmp_path: Path) -> None:
    backend, _, store, session = backend_for(tmp_path)
    challenge_id = store.repository.start_email_verification(
        session_subject="student-session",
        destination="student@ntu.edu.tw",
        email_kind="INSTITUTIONAL",
    )
    response = backend.handle(
        request(
            session,
            JOIN_PATH,
            student_payload(emailVerificationId=challenge_id),
        )
    )
    assert response.status == 400
    assert response.json()["error"] == "EMAIL_NOT_VERIFIED"
