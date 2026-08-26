from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from discord_course_bots.apps_script_transport import AppsScriptApiError
from discord_course_bots.data_lab.transport import FakeGasTransport
from discord_course_bots.production_bridge import (
    BridgeSettings,
    deliver_verification_email_once,
    project_once,
)
from discord_course_bots.repository import Repository

FINGERPRINT = "PRODUCTION-SHEET-FINGERPRINT"


def settings(database: Path) -> BridgeSettings:
    return BridgeSettings(
        database_path=database,
        deployment_id="deployment-fixture",
        credential_path=database.parent / "oauth-fixture.json",
        sheet_fingerprint=FINGERPRINT,
        environment="PRODUCTION",
        synthetic_only=False,
        interval_seconds=60,
        staging_lab_root=None,
    )


def test_discord_case_transition_and_projection_share_atomic_ledger(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    repository = Repository(database)
    try:
        case_number = repository.create_case(
            case_id="case-fixture",
            thread_id=123,
            author_id=456,
            module_code="M01",
            keyword="極限",
            ai_content_permission=False,
            canonical_title="極限題目",
            initial_snapshot={"title": "極限題目"},
            class_code="01",
        )
        repository.claim_case(123, 789)
        repository.close_case(123)
        repository.reopen_case(123)
        events = repository._connection.execute(  # noqa: SLF001
            "SELECT event_type, synthetic, source_kind FROM case_lifecycle_events "
            "WHERE case_ref = ? ORDER BY occurred_at, rowid",
            (case_number,),
        ).fetchall()
        assert [(row[0], row[1], row[2]) for row in events] == [
            ("OPEN", 0, "DISCORD"),
            ("TRACK", 0, "DISCORD"),
            ("CLOSE", 0, "DISCORD"),
            ("REOPEN", 0, "DISCORD"),
        ]
        assert (
            repository._connection.execute(  # noqa: SLF001
                "SELECT COUNT(*) FROM projection_outbox WHERE aggregate_ref = ?",
                (case_number,),
            ).fetchone()[0]
            == 16
        )
    finally:
        repository.close()


def test_production_projection_is_idempotent_and_contains_no_actor_ids(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    repository = Repository(database)
    try:
        case_number = repository.create_case(
            case_id="case-fixture",
            thread_id=123,
            author_id=456,
            module_code="M01",
            keyword="極限",
            ai_content_permission=True,
            canonical_title="極限題目",
            initial_snapshot={"title": "極限題目"},
            class_code="01",
        )
    finally:
        repository.close()
    transport = FakeGasTransport(
        FINGERPRINT,
        expected_environment="PRODUCTION",
        expected_synthetic_only=False,
    )
    receipt = project_once(settings(database), transport, apply=True)
    assert receipt["status"] == "APPLIED"
    assert transport.views["CaseBoard"][0]["caseNumber"] == case_number
    assert "authorId" not in transport.views["CaseBoard"][0]
    assert transport.views["CaseBoard"][0]["analysisEligible"] is True
    assert project_once(settings(database), transport, apply=True)["status"] == "NO_WORK"


class EmailTransportFixture:
    def __init__(self, error_code: str | None = None) -> None:
        self.error_code = error_code
        self.deliveries: list[dict[str, object]] = []

    def send_verification_email(self, delivery: dict[str, object]) -> dict[str, object]:
        self.deliveries.append(dict(delivery))
        if self.error_code:
            raise AppsScriptApiError(self.error_code)
        return {
            "deliveryId": delivery["deliveryId"],
            "status": "PROVIDER_ACCEPTED",
            "safeResultCode": "EMAIL_PROVIDER_ACCEPTED",
            "quotaRemainingBefore": 50,
        }


def _queue_email(database: Path) -> str:
    repository = Repository(database)
    try:
        return repository.enqueue_verification_email(
            challenge_id="email_verification_12345678",
            destination="student@example.com",
            verification_code="987654",
            email_kind="INSTITUTIONAL",
            expires_at=(datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
            delivery_id="email_delivery_12345678",
        )
    finally:
        repository.close()


def test_email_bridge_completes_and_scrubs_delivery_payload(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    delivery_id = _queue_email(database)
    transport = EmailTransportFixture()
    result = deliver_verification_email_once(settings(database), transport)  # type: ignore[arg-type]
    assert result == {
        "status": "COMPLETED",
        "safeResultCode": "EMAIL_PROVIDER_ACCEPTED",
    }
    repository = Repository(database)
    try:
        row = repository._connection.execute(
            "SELECT status, destination, verification_code FROM email_delivery_outbox "
            "WHERE delivery_id = ?",
            (delivery_id,),
        ).fetchone()
        assert tuple(row) == ("COMPLETED", None, None)
    finally:
        repository.close()


def test_email_bridge_marks_ambiguous_provider_result_for_manual_attention(
    tmp_path: Path,
) -> None:
    database = tmp_path / "runtime.sqlite3"
    delivery_id = _queue_email(database)
    transport = EmailTransportFixture("EMAIL_DELIVERY_AMBIGUOUS")
    result = deliver_verification_email_once(settings(database), transport)  # type: ignore[arg-type]
    assert result["status"] == "PERMANENT_FAILURE"
    repository = Repository(database)
    try:
        status = repository.safe_verification_email_status(delivery_id)
        assert status is not None
        assert status["status"] == "PERMANENT_FAILURE"
        assert status["last_error_code"] == "EMAIL_DELIVERY_AMBIGUOUS"
    finally:
        repository.close()
