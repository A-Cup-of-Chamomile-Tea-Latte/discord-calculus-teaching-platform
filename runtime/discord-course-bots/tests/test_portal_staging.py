from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from discord_course_bots.apps_script_transport import AppsScriptApiError
from discord_course_bots.portal_backend import (
    CASE_LOOKUP_PATH,
    EMAIL_START_PATH,
    SESSION_PATH,
    PortalRequest,
)
from discord_course_bots.portal_staging import (
    CapturingEmailTransport,
    SyntheticStagingError,
    create_synthetic_staging,
)

ORIGIN = "https://staging.portal.example"
HOST = "staging.portal.example"


def issue_scope(backend, scope: str) -> tuple[str, str]:
    response = backend.handle(
        PortalRequest(
            method="POST",
            target=SESSION_PATH,
            headers={
                "Host": HOST,
                "Origin": ORIGIN,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body=f"scope={scope}".encode(),
            client_key="synthetic-browser",
        )
    )
    assert response.status == 201
    cookies = response.headers["Set-Cookie"]
    assert isinstance(cookies, tuple)
    session = cookies[0].split(";", 1)[0]
    csrf_pair = cookies[1].split(";", 1)[0]
    return f"{session}; {csrf_pair}", csrf_pair.split("=", 1)[1]


def issue_lookup(backend) -> tuple[str, str]:
    return issue_scope(backend, "LOOKUP")


def lookup(backend, cookies: str, csrf: str, case_number: str):
    return backend.handle(
        PortalRequest(
            method="POST",
            target=CASE_LOOKUP_PATH,
            headers={
                "Host": HOST,
                "Origin": ORIGIN,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookies,
                "X-CSRF-Token": csrf,
            },
            body=f"caseNumber={case_number}".encode(),
            client_key="synthetic-browser",
        )
    )


def test_synthetic_staging_is_isolated_idempotent_and_supports_minimal_lookup(
    tmp_path: Path,
) -> None:
    root = tmp_path / "portal-staging"
    staging = create_synthetic_staging(
        root,
        origin=ORIGIN,
        session_secret=b"s" * 32,
    )
    original_numbers = (staging.general_case_number, staging.private_case_number)
    try:
        assert staging.database_path.parent == root
        assert staging.audit_database_path.parent == root
        assert staging.database_path != staging.audit_database_path
        assert staging.store.repository.get_config("portal.synthetic_only") == "1"
        assert staging.store.repository.get_config("portal.environment") == "STAGING"
        assert staging.store.repository.get_config("live_discord_enabled") == "0"
        cookies, csrf = issue_lookup(staging.backend)
        general = lookup(staging.backend, cookies, csrf, staging.general_case_number)
        private = lookup(staging.backend, cookies, csrf, staging.private_case_number)

        assert general.status == private.status == 200
        assert general.json()["case"]["caseType"] == "GENERAL"
        assert private.json()["case"]["caseType"] == "PRIVATE_SUPPORT"
        assert "synthetic staging content" not in general.body.decode()
        assert "synthetic staging content" not in private.body.decode()
        assert general.headers["Cache-Control"] == private.headers["Cache-Control"] == "no-store"
        assert general.headers["Referrer-Policy"] == "no-referrer"
    finally:
        staging.close()

    resumed = create_synthetic_staging(
        root,
        origin=ORIGIN,
        session_secret=b"n" * 32,
    )
    try:
        assert (resumed.general_case_number, resumed.private_case_number) == original_numbers
        marker = root / ".portal-synthetic-staging.json"
        assert json.loads(marker.read_text(encoding="utf-8"))["syntheticOnly"] is True
        assert stat.S_IMODE(marker.stat().st_mode) == 0o600
    finally:
        resumed.close()


def test_synthetic_staging_refuses_unmarked_or_insecure_roots(tmp_path: Path) -> None:
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "existing.txt").write_text("user data", encoding="utf-8")

    with pytest.raises(SyntheticStagingError, match="UNMARKED_NONEMPTY"):
        create_synthetic_staging(
            occupied,
            origin=ORIGIN,
            session_secret=b"s" * 32,
        )
    with pytest.raises(SyntheticStagingError, match="HTTPS_ORIGIN_REQUIRED"):
        create_synthetic_staging(
            tmp_path / "http-staging",
            origin="http://staging.portal.example",
            session_secret=b"s" * 32,
        )


def test_synthetic_staging_refuses_real_email_before_storage(tmp_path: Path) -> None:
    staging = create_synthetic_staging(
        tmp_path / "portal-staging",
        origin=ORIGIN,
        session_secret=b"s" * 32,
    )
    try:
        cookies, csrf = issue_scope(staging.backend, "JOIN")
        response = staging.backend.handle(
            PortalRequest(
                method="POST",
                target=EMAIL_START_PATH,
                headers={
                    "Host": HOST,
                    "Origin": ORIGIN,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Cookie": cookies,
                    "X-CSRF-Token": csrf,
                },
                body=b"identityType=GUEST&email=real%40example.net",
                client_key="synthetic-browser",
            )
        )
        queued = staging.store.repository._connection.execute(  # noqa: SLF001
            "SELECT COUNT(*) FROM email_delivery_outbox"
        ).fetchone()[0]
        assert response.status == 400
        assert queued == 0
    finally:
        staging.close()


def test_capturing_transport_accepts_only_named_fixture_destinations(tmp_path: Path) -> None:
    capture = CapturingEmailTransport(tmp_path / "captured.jsonl")
    delivery = {
        "deliveryId": "delivery_fixture",
        "destination": "synthetic.guest@example.com",
        "code": "123456",
        "kind": "CONTACT",
        "expiresAt": "2026-08-28T00:00:00+00:00",
    }
    receipt = capture.send_verification_email(delivery)

    assert receipt["safeResultCode"] == "SYNTHETIC_EMAIL_CAPTURED"
    record = json.loads((tmp_path / "captured.jsonl").read_text(encoding="utf-8"))
    assert record["syntheticOnly"] is True
    assert record["code"] == "123456"
    assert stat.S_IMODE((tmp_path / "captured.jsonl").stat().st_mode) == 0o600

    with pytest.raises(AppsScriptApiError, match="STAGING_DESTINATION_REFUSED"):
        capture.send_verification_email({**delivery, "destination": "real@example.net"})
