from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from discord_course_bots.data_lab.carrier import ensure_staging_carrier, open_staging_repository
from discord_course_bots.data_lab.commands import fetch_once
from discord_course_bots.data_lab.contracts import build_command_envelope
from discord_course_bots.data_lab.service import file_sha256
from discord_course_bots.data_lab.transport import FakeGasTransport

FINGERPRINT = "SYNTHETIC-SHEET-FINGERPRINT"
BASIC = "fixture://public/basic-v1"


def root(tmp_path: Path) -> Path:
    return tmp_path / "phase2b-data-lab"


def command(source_version: int = 1) -> dict[str, object]:
    return build_command_envelope(
        command_id="CMD-TST-001",
        command_type="CREATE_SYNTHETIC_CASE",
        payload_ref=BASIC,
        target_case_ref=None,
        idempotency_key="idem-command-001",
        source_version=source_version,
        requested_at="2026-08-11T06:00:00Z",
        source_fingerprint=FINGERPRINT,
    )


def test_command_dry_run_then_apply(tmp_path: Path) -> None:
    root_path = root(tmp_path)
    transport = FakeGasTransport(FINGERPRINT)
    transport.queue_command(command())
    paths = ensure_staging_carrier(root_path)
    before = file_sha256(paths.database)
    preview = fetch_once(root_path, transport, apply=False)
    assert preview["status"] == "PREVIEW"
    assert preview["localMutation"] is False
    assert preview["cloudMutation"] is False
    assert file_sha256(paths.database) == before
    receipt = fetch_once(
        root_path,
        transport,
        apply=True,
        confirmation_nonce=str(preview["confirmationNonce"]),
    )
    assert receipt["status"] == "APPLIED"
    assert transport.commands[0]["status"] == "COMPLETED"


def test_bad_checksum_and_wrong_fingerprint_do_not_touch_local_db(tmp_path: Path) -> None:
    root_path = root(tmp_path)
    paths = ensure_staging_carrier(root_path)
    before = file_sha256(paths.database)
    for field, value, code in (
        ("checksum", "0" * 64, "SYNC_BAD_CHECKSUM"),
        ("sourceFingerprint", "wrong", "SYNC_WRONG_TARGET"),
    ):
        envelope = command()
        envelope[field] = value
        transport = FakeGasTransport(FINGERPRINT)
        transport.queue_command(envelope)
        receipt = fetch_once(root_path, transport, apply=False)
        assert receipt["safeResultCode"] == code
        assert receipt["localMutation"] is False
        assert file_sha256(paths.database) == before


def test_local_commit_then_remote_ack_failure_replays_as_noop(tmp_path: Path) -> None:
    root_path = root(tmp_path)
    transport = FakeGasTransport(FINGERPRINT)
    transport.queue_command(command())
    preview = fetch_once(root_path, transport, apply=False)
    first = fetch_once(
        root_path,
        transport,
        apply=True,
        confirmation_nonce=str(preview["confirmationNonce"]),
        simulate_ack_failure=True,
    )
    assert first["status"] == "LOCAL_APPLIED_REMOTE_ACK_PENDING"
    initial_claim = transport.commands[0]
    initial_claim["leaseExpiresAt"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    replay_preview = fetch_once(root_path, transport, apply=False)
    replay = fetch_once(
        root_path,
        transport,
        apply=True,
        confirmation_nonce=str(replay_preview["confirmationNonce"]),
    )
    assert replay["status"] == "NO_OP"
    assert replay["localMutation"] is False
    assert transport.commands[0]["status"] == "COMPLETED"


def test_expired_claim_can_be_reclaimed_but_stale_token_cannot_ack() -> None:
    transport = FakeGasTransport(FINGERPRINT)
    transport.queue_command(command())
    start = datetime(2026, 8, 11, 6, 0, tzinfo=UTC)
    first = transport.claim_command("worker-a", now=start, lease_seconds=10)
    assert first is not None
    second = transport.claim_command("worker-b", now=start + timedelta(seconds=11))
    assert second is not None
    assert second.claim_token != first.claim_token
    assert not transport.ack_command("CMD-TST-001", first.claim_token, "APPLIED")
    assert transport.ack_command("CMD-TST-001", second.claim_token, "APPLIED")


def test_replay_command_records_noop_without_new_lifecycle_event(tmp_path: Path) -> None:
    root_path = root(tmp_path)
    transport = FakeGasTransport(FINGERPRINT)
    transport.queue_command(command())
    first_preview = fetch_once(root_path, transport, apply=False)
    fetch_once(
        root_path,
        transport,
        apply=True,
        confirmation_nonce=str(first_preview["confirmationNonce"]),
    )
    replay = build_command_envelope(
        command_id="CMD-TST-002",
        command_type="REPLAY_LAST_SYNTHETIC_COMMAND",
        payload_ref=BASIC,
        target_case_ref=None,
        idempotency_key="idem-replay-002",
        source_version=2,
        requested_at="2026-08-11T06:02:00Z",
        source_fingerprint=FINGERPRINT,
    )
    transport.queue_command(replay)
    replay_preview = fetch_once(root_path, transport, apply=False)
    receipt = fetch_once(
        root_path,
        transport,
        apply=True,
        confirmation_nonce=str(replay_preview["confirmationNonce"]),
    )
    assert receipt["status"] == "NO_OP"
    repository = open_staging_repository(ensure_staging_carrier(root_path))
    try:
        assert repository.counts()["case_lifecycle_events"] == 1
        assert repository.counts()["inbound_commands"] == 2
    finally:
        repository.close()
