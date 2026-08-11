from __future__ import annotations

from pathlib import Path

import pytest

from discord_course_bots.data_lab.carrier import ensure_staging_carrier, open_staging_repository
from discord_course_bots.data_lab.fixtures import get_fixture
from discord_course_bots.data_lab.projection import build_pending_envelope, project_once
from discord_course_bots.data_lab.transport import FakeGasTransport

FINGERPRINT = "SYNTHETIC-SHEET-FINGERPRINT"
BASIC = "fixture://public/basic-v1"


def root(tmp_path: Path) -> Path:
    return tmp_path / "phase2b-data-lab"


def seed(root_path: Path) -> None:
    paths = ensure_staging_carrier(root_path)
    repository = open_staging_repository(paths)
    try:
        fixture = get_fixture(BASIC)
        fixture["fixtureRef"] = BASIC
        repository.apply_fixture(fixture)
    finally:
        repository.close()


def test_projection_dry_run_has_zero_cloud_and_sqlite_mutation(tmp_path: Path) -> None:
    root_path = root(tmp_path)
    seed(root_path)
    transport = FakeGasTransport(FINGERPRINT)
    paths = ensure_staging_carrier(root_path)
    before = paths.database.read_bytes()
    preview = project_once(root_path, transport, apply=False)
    assert preview["dryRun"] is True
    assert preview["cloudMutation"] is False
    assert transport.mutation_count == 0
    assert paths.database.read_bytes() == before
    assert preview["row_counts"] == {
        "Overview": 2,
        "CaseBoard": 1,
        "Operations": 1,
        "History": 1,
    }


def test_projection_apply_reuses_preview_bundle_and_completes_work(tmp_path: Path) -> None:
    root_path = root(tmp_path)
    seed(root_path)
    transport = FakeGasTransport(FINGERPRINT)
    preview = project_once(root_path, transport, apply=False)
    receipt = project_once(
        root_path,
        transport,
        apply=True,
        confirmation_nonce=str(preview["confirmation_nonce"]),
    )
    assert receipt["status"] == "APPLIED"
    assert receipt["completedWorkCount"] == 4
    assert receipt["cloudMutation"] is False
    assert receipt["transport"] == "FAKE_LOCAL"
    assert transport.mutation_count == 1
    assert len(transport.views["CaseBoard"]) == 1
    assert len(transport.views["History"]) == 1


def test_projection_nonce_mismatch_is_fail_closed(tmp_path: Path) -> None:
    root_path = root(tmp_path)
    seed(root_path)
    transport = FakeGasTransport(FINGERPRINT)
    with pytest.raises(RuntimeError, match="CONFIRMATION_NONCE_MISMATCH"):
        project_once(root_path, transport, apply=True, confirmation_nonce="wrong")
    assert transport.mutation_count == 0


def test_current_state_coalesces_but_history_does_not(tmp_path: Path) -> None:
    root_path = root(tmp_path)
    paths = ensure_staging_carrier(root_path)
    repository = open_staging_repository(paths)
    try:
        fixture = get_fixture(BASIC)
        fixture["fixtureRef"] = BASIC
        fixture["occurredAt"] = "2026-08-11T05:00:00Z"
        repository.apply_fixture(fixture)
        fixture["occurredAt"] = "2026-08-11T05:01:00Z"
        repository.apply_fixture(fixture, requested_status="CLOSED")
        fixture["occurredAt"] = "2026-08-11T05:02:00Z"
        repository.apply_fixture(fixture, requested_status="OPEN")
        envelope, pending = build_pending_envelope(repository, FINGERPRINT)
        assert envelope is not None
        assert len(pending) == 12
        assert envelope["rowCounts"]["CaseBoard"] == 1
        assert envelope["rowCounts"]["Overview"] == 2
        assert envelope["rowCounts"]["Operations"] == 1
        assert envelope["rowCounts"]["History"] == 3
        assert [row["eventType"] for row in envelope["rows"]["History"]] == [
            "OPEN",
            "CLOSE",
            "REOPEN",
        ]
    finally:
        repository.close()


def test_projection_batch_is_capped_at_fifty(tmp_path: Path) -> None:
    root_path = root(tmp_path)
    paths = ensure_staging_carrier(root_path)
    repository = open_staging_repository(paths)
    try:
        fixture = get_fixture(BASIC)
        fixture["fixtureRef"] = BASIC
        for index in range(13):
            fixture["caseRef"] = f"TST-BATCH-{index:03d}"
            fixture["occurredAt"] = f"2026-08-11T05:{index:02d}:00Z"
            repository.apply_fixture(fixture)
        _, pending = build_pending_envelope(repository, FINGERPRINT)
        assert len(pending) == 50
    finally:
        repository.close()
