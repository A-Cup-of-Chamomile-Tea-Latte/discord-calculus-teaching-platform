from __future__ import annotations

from pathlib import Path

import pytest

from discord_course_bots.data_lab.carrier import ensure_staging_carrier, open_staging_repository
from discord_course_bots.data_lab.contracts import build_command_envelope, validate_command_envelope
from discord_course_bots.data_lab.fixtures import get_fixture
from discord_course_bots.data_lab.repository import DataLabConflict
from discord_course_bots.data_lab.service import (
    ConfirmationError,
    apply_ingest,
    dry_run_ingest,
    file_sha256,
)

FINGERPRINT = "SYNTHETIC-SHEET-FINGERPRINT"
BASIC = "fixture://public/basic-v1"


def lab_root(tmp_path: Path) -> Path:
    return tmp_path / "phase2b-data-lab"


def test_dry_run_is_byte_preserving_and_apply_needs_same_nonce(tmp_path: Path) -> None:
    root = lab_root(tmp_path)
    plan = dry_run_ingest(root, BASIC)
    assert plan["databaseUnchanged"] is True
    assert plan["databaseSha256"] == "ABSENT"
    assert not (root / "staging.sqlite3").exists()
    with pytest.raises(ConfirmationError, match="CONFIRMATION_NONCE_MISMATCH"):
        apply_ingest(root, BASIC, "wrong")
    receipt = apply_ingest(root, BASIC, str(plan["confirmationNonce"]))
    assert receipt["status"] == "APPLIED"
    assert receipt["caseRef"] == "TST-BASIC-001"
    assert receipt["outboxCount"] == 4


def test_fixture_transition_is_atomic_and_populates_outbox(tmp_path: Path) -> None:
    paths = ensure_staging_carrier(lab_root(tmp_path))
    repository = open_staging_repository(paths)
    try:
        fixture = get_fixture(BASIC)
        fixture["fixtureRef"] = BASIC
        result = repository.apply_fixture(fixture, correlation_id="run-test")
        assert result.source_version == 1
        assert repository.counts() == {
            "cases": 1,
            "case_lifecycle_events": 1,
            "inbound_commands": 0,
            "projection_outbox": 4,
        }
        assert {row["projection_scope"] for row in repository.pending_projection_rows()} == {
            "CASEBOARD",
            "HISTORY",
            "OVERVIEW",
            "OPERATIONS",
        }
    finally:
        repository.close()


def test_command_apply_is_idempotent_and_conflicts_fail_closed(tmp_path: Path) -> None:
    paths = ensure_staging_carrier(lab_root(tmp_path))
    repository = open_staging_repository(paths)
    try:
        envelope = build_command_envelope(
            command_id="CMD-TST-001",
            command_type="CREATE_SYNTHETIC_CASE",
            payload_ref=BASIC,
            target_case_ref=None,
            idempotency_key="idem-001",
            source_version=1,
            requested_at="2026-08-11T05:00:00Z",
            source_fingerprint=FINGERPRINT,
        )
        validate_command_envelope(envelope, FINGERPRINT)
        fixture = get_fixture(BASIC)
        first = repository.apply_command(envelope, fixture)
        second = repository.apply_command(envelope, fixture)
        assert first.no_op is False
        assert second.no_op is True
        assert repository.counts()["case_lifecycle_events"] == 1
        conflicting = dict(envelope)
        conflicting["commandId"] = "CMD-TST-002"
        conflicting["payloadRef"] = "fixture://public/close-reopen-v1"
        from discord_course_bots.data_lab.contracts import with_checksum

        conflicting = with_checksum(conflicting)
        with pytest.raises(DataLabConflict, match="COMMAND_IDEMPOTENCY_CONFLICT"):
            repository.apply_command(conflicting, get_fixture(str(conflicting["payloadRef"])))
        assert repository.counts()["case_lifecycle_events"] == 1
    finally:
        repository.close()


def test_projection_claim_uses_shared_reliable_queue(tmp_path: Path) -> None:
    paths = ensure_staging_carrier(lab_root(tmp_path))
    repository = open_staging_repository(paths)
    try:
        fixture = get_fixture(BASIC)
        fixture["fixtureRef"] = BASIC
        repository.apply_fixture(fixture)
        claim = repository.claim_projection(worker_id="phase2b-test")
        assert claim is not None
        assert repository.complete_projection(str(claim.key), claim.claim_token, "a" * 64)
        row = repository._connection.execute(  # noqa: SLF001
            "SELECT status FROM projection_outbox WHERE projection_id = ?", (claim.key,)
        ).fetchone()
        assert row["status"] == "COMPLETED"
    finally:
        repository.close()


def test_stale_command_leaves_database_bytes_unchanged(tmp_path: Path) -> None:
    paths = ensure_staging_carrier(lab_root(tmp_path))
    repository = open_staging_repository(paths)
    try:
        fixture = get_fixture(BASIC)
        envelope = build_command_envelope(
            command_id="CMD-TST-001",
            command_type="CREATE_SYNTHETIC_CASE",
            payload_ref=BASIC,
            target_case_ref=None,
            idempotency_key="idem-001",
            source_version=1,
            requested_at="2026-08-11T05:00:00Z",
            source_fingerprint=FINGERPRINT,
        )
        repository.apply_command(envelope, fixture)
    finally:
        repository.close()
    before = file_sha256(paths.database)
    repository = open_staging_repository(paths)
    try:
        stale = build_command_envelope(
            command_id="CMD-TST-002",
            command_type="REOPEN_SYNTHETIC_CASE",
            payload_ref=BASIC,
            target_case_ref="TST-BASIC-001",
            idempotency_key="idem-002",
            source_version=1,
            requested_at="2026-08-11T05:01:00Z",
            source_fingerprint=FINGERPRINT,
        )
        with pytest.raises(DataLabConflict, match="SYNC_STALE_VERSION"):
            repository.apply_command(stale, fixture)
    finally:
        repository.close()
    assert file_sha256(paths.database) == before


def test_human_views_are_not_command_sources() -> None:
    source_tables = {"_CommandInbox"}
    assert "CaseBoard" not in source_tables
    assert "Overview" not in source_tables
