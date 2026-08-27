from __future__ import annotations

import json
from pathlib import Path

from discord_course_bots.portal_backend import (
    EMAIL_START_PATH,
    EMAIL_VERIFY_PATH,
    JOIN_CSRF_COOKIE,
    JOIN_PATH,
    JOIN_SESSION_COOKIE,
    InMemoryAuditSink,
    PortalBackend,
    PortalBackendSettings,
    PortalRequest,
    SignedSessionAuthorizer,
    SqlitePortalStore,
)
from discord_course_bots.production_bridge import BridgeSettings, deliver_verification_email_once

ORIGIN = "https://portal.test"
HOST = "portal.test"
CSRF = "local-integration-csrf"


class CapturingEmailTransport:
    """Test adapter: exercises the real queue worker without network or MailApp."""

    def __init__(self) -> None:
        self.deliveries: list[dict[str, object]] = []

    def send_verification_email(self, delivery: dict[str, object]) -> dict[str, object]:
        self.deliveries.append(dict(delivery))
        return {
            "deliveryId": delivery["deliveryId"],
            "status": "PROVIDER_ACCEPTED",
            "safeResultCode": "EMAIL_PROVIDER_ACCEPTED",
            "quotaRemainingBefore": 500,
        }


def post(session: str, path: str, payload: dict[str, str]) -> PortalRequest:
    return PortalRequest(
        method="POST",
        target=path,
        headers={
            "Host": HOST,
            "Origin": ORIGIN,
            "Content-Type": "application/json",
            "Cookie": f"{JOIN_SESSION_COOKIE}={session}; {JOIN_CSRF_COOKIE}={CSRF}",
            "X-CSRF-Token": CSRF,
        },
        body=json.dumps(payload).encode("utf-8"),
        client_key="local-browser-smoke",
    )


def bridge_settings(database: Path, tmp_path: Path) -> BridgeSettings:
    return BridgeSettings(
        database_path=database,
        deployment_id="local-test-deployment",
        credential_path=tmp_path / "unused-oauth.json",
        sheet_fingerprint="local-test-sheet",
        environment="STAGING",
        synthetic_only=True,
        interval_seconds=60,
        staging_lab_root=tmp_path / "staging",
    )


def test_join_email_journey_works_without_school_hosting_or_network(tmp_path: Path) -> None:
    database = tmp_path / "portal.sqlite3"
    store = SqlitePortalStore(database)
    sessions = SignedSessionAuthorizer(b"s" * 32)
    session = sessions.issue_for_test("local-browser-session")
    audit = InMemoryAuditSink()
    backend = PortalBackend(
        store,
        settings=PortalBackendSettings(ORIGIN, secure_cookies=False),
        sessions=sessions,
        audit=audit,
    )
    transport = CapturingEmailTransport()

    try:
        started = backend.handle(
            post(
                session,
                EMAIL_START_PATH,
                {"identityType": "GUEST", "email": "visitor@example.com"},
            )
        )
        assert started.status == 202
        challenge_id = str(started.json()["challengeId"])
        assert "code" not in started.body.decode("utf-8").casefold()

        delivered = deliver_verification_email_once(
            bridge_settings(database, tmp_path),
            transport,
        )
        assert delivered == {
            "status": "COMPLETED",
            "safeResultCode": "EMAIL_PROVIDER_ACCEPTED",
        }
        assert len(transport.deliveries) == 1
        code = str(transport.deliveries[0]["code"])

        verified = backend.handle(
            post(
                session,
                EMAIL_VERIFY_PATH,
                {"challengeId": challenge_id, "code": code},
            )
        )
        assert verified.status == 200

        submitted = backend.handle(
            post(
                session,
                JOIN_PATH,
                {
                    "identityType": "GUEST",
                    "discordUsername": "local.visitor",
                    "guestEmail": "visitor@example.com",
                    "guestReason": "本機整合測試，不連外部服務。",
                    "rulesPrivacy": "yes",
                    "emailVerificationId": challenge_id,
                },
            )
        )
        assert submitted.status == 202
        assert submitted.json()["outcome"] == "ACCEPTED"
        assert len(store.repository.pending_join_applications()) == 1

        row = store.repository._connection.execute(
            "SELECT status, destination, verification_code "
            "FROM email_delivery_outbox WHERE challenge_id = ?",
            (challenge_id,),
        ).fetchone()
        assert tuple(row) == ("COMPLETED", None, None)

        serialized_audit = json.dumps(audit.records, default=str)
        assert "visitor@example.com" not in serialized_audit
        assert code not in serialized_audit
    finally:
        store.close()
