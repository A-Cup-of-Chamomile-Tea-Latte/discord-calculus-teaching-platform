from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from discord_course_bots.portal_backend import (
    CASE_LOOKUP_PATH,
    JOIN_PATH,
    InMemoryAuditSink,
    PortalBackend,
    PortalBackendSettings,
    PortalRequest,
    PortalStore,
    RateLimiter,
    SignedSessionAuthorizer,
    SQLiteAuditSink,
    SqlitePortalStore,
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
    headers = {
        "Host": host,
        "Cookie": f"portal_session={session}; portal_csrf={CSRF}",
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


def test_join_revalidates_and_uses_canonical_sqlite_store(tmp_path: Path) -> None:
    audit = InMemoryAuditSink()
    backend, _, store, session = backend_for(tmp_path, audit=audit)
    response = backend.handle(request(session, JOIN_PATH, student_payload()))

    assert response.status == 202
    assert response.json()["outcome"] == "ACCEPTED"
    assert len(store.repository.pending_join_applications()) == 1  # type: ignore[union-attr]
    assert [record.event_type for record in audit.records] == [
        "PORTAL_JOIN_ATTEMPT",
        "PORTAL_JOIN_STORED",
    ]
    assert "student@ntu.edu.tw" not in json.dumps(audit.records, default=str)


def test_duplicate_join_is_idempotent_and_generic(tmp_path: Path) -> None:
    backend, _, _, session = backend_for(tmp_path)
    first = backend.handle(request(session, JOIN_PATH, student_payload()))
    second = backend.handle(request(session, JOIN_PATH, student_payload(classCode="C02")))

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
    response = backend.handle(
        request(
            session,
            JOIN_PATH,
            {
                "identityType": "GUEST",
                "discordUsername": "visitor.name",
                "guestEmail": "visitor@example.com",
                "guestReason": "我是旁聽學生，希望加入討論。",
                "rulesPrivacy": "yes",
            },
        )
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


def test_csrf_seed_is_same_origin_and_no_store(tmp_path: Path) -> None:
    backend, _, _, session = backend_for(tmp_path)
    response = backend.handle(
        PortalRequest(
            method="GET",
            target=JOIN_PATH,
            headers={"Host": HOST, "Cookie": f"portal_session={session}"},
            client_key="test-client",
        )
    )

    assert response.status == 204
    assert response.body == b""
    assert "Set-Cookie" in response.headers
    assert response.headers["Cache-Control"] == "no-store"


def test_rate_limit_is_per_route_and_generic(tmp_path: Path) -> None:
    backend, _, _, session = backend_for(
        tmp_path, rate_limiter=RateLimiter(limit=1, window_seconds=60)
    )
    first = backend.handle(request(session, JOIN_PATH, student_payload()))
    second = backend.handle(request(session, JOIN_PATH, student_payload()))

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
    response = backend.handle(request(session, JOIN_PATH, student_payload()))

    assert response.status == 503
    assert not store.repository.pending_join_applications()  # type: ignore[union-attr]


def test_sqlite_audit_sink_persists_only_metadata(tmp_path: Path) -> None:
    audit = SQLiteAuditSink(tmp_path / "audit.sqlite3")
    backend, _, store, session = backend_for(tmp_path / "operational", audit=audit)
    response = backend.handle(request(session, JOIN_PATH, student_payload()))

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
