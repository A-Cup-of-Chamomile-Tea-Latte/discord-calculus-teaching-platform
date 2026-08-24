import json
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from discord_course_bots.domain.titles import cycle_title
from discord_course_bots.migrations import MIGRATIONS, MigrationError
from discord_course_bots.repository import SQLITE_BUSY_TIMEOUT_MILLISECONDS, Repository


def test_fresh_database_has_versioned_migration_ledger(tmp_path: Path) -> None:
    database_path = tmp_path / "fresh.sqlite3"
    repo = Repository(database_path)

    assert repo.schema_version == MIGRATIONS[-1].version
    history = repo.migration_history()
    assert [row["version"] for row in history] == [migration.version for migration in MIGRATIONS]
    assert all(len(str(row["checksum"])) == 64 for row in history)
    table_names = {
        str(row[0])
        for row in repo._connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert table_names == {
        "schema_migrations",
        "runtime_config",
        "drafts",
        "cases",
        "private_support",
        "private_dump_jobs",
        "case_lifecycle_events",
        "inbound_commands",
        "projection_outbox",
        "sync_state",
        "service_health",
        "discord_lifecycle_jobs",
        "private_open_requests",
        "discord_dm_outbox",
        "join_applications",
        "join_application_events",
        "reviewer_grants",
            "course_role_jobs",
            "course_alias_allocations",
        }


def test_repository_sets_explicit_busy_timeout(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "busy-timeout.sqlite3")
    configured = int(repo._connection.execute("PRAGMA busy_timeout").fetchone()[0])
    assert configured == SQLITE_BUSY_TIMEOUT_MILLISECONDS


def test_repository_waits_for_short_writer_contention(tmp_path: Path) -> None:
    database_path = tmp_path / "contention.sqlite3"
    repo = Repository(database_path)
    locker = sqlite3.connect(database_path, check_same_thread=False)
    locker.execute("PRAGMA busy_timeout = 1000")
    locker.execute("BEGIN IMMEDIATE")

    def release_lock() -> None:
        time.sleep(0.15)
        locker.rollback()
        locker.close()

    release = threading.Thread(target=release_lock)
    release.start()
    started = time.monotonic()
    repo.set_config("contention.probe", "released")
    elapsed = time.monotonic() - started
    release.join(timeout=2)

    assert repo.get_config("contention.probe") == "released"
    assert elapsed >= 0.1
    assert elapsed < 2


def test_repeated_migration_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "repeat.sqlite3"
    first = Repository(database_path)
    first.set_config("sentinel", "preserved")
    first_history = [tuple(row) for row in first.migration_history()]
    first.close()

    second = Repository(database_path)
    assert second.get_config("sentinel") == "preserved"
    assert [tuple(row) for row in second.migration_history()] == first_history
    assert second.schema_version == MIGRATIONS[-1].version


def test_migration_checksum_mismatch_fails_closed(tmp_path: Path) -> None:
    database_path = tmp_path / "tampered.sqlite3"
    repo = Repository(database_path)
    repo.close()
    connection = sqlite3.connect(database_path)
    connection.execute("UPDATE schema_migrations SET checksum = 'tampered' WHERE version = 1")
    connection.commit()
    connection.close()

    with pytest.raises(MigrationError, match="checksum or name does not match"):
        Repository(database_path)


def test_draft_to_case(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "test.sqlite3")
    repo.create_draft(
        thread_id=1,
        forum_channel_id=2,
        author_id=3,
        original_title="Question",
        starter_message_id=1,
    )
    assert repo.get_draft(1) is not None
    repo.create_case(
        case_id="case-1",
        thread_id=1,
        author_id=3,
        module_code="M1",
        keyword="test",
        ai_content_permission=False,
        canonical_title="[M1] [test] Question",
        initial_snapshot={"body": "hello"},
        class_code="01",
    )
    case = repo.get_case_by_thread(1)
    assert case is not None
    assert case["status"] == "OPEN"
    assert repo.claim_case(1, 9) is not None
    closed = repo.close_case(1)
    assert closed is not None
    assert closed["status"] == "CLOSED"
    close_job = repo._connection.execute(
        "SELECT transition, cycle_number, status FROM discord_lifecycle_jobs"
    ).fetchone()
    assert tuple(close_job) == ("CLOSE", 1, "PENDING")
    reopened = repo.reopen_case(1)
    assert reopened is not None
    assert reopened["status"] == "TRACKED"
    assert reopened["reopen_count"] == 1
    assert reopened["base_title"] == "[M1] [test] Question"
    reopen_job = repo._connection.execute(
        "SELECT transition, cycle_number, status FROM discord_lifecycle_jobs "
        "WHERE transition = 'REOPEN'"
    ).fetchone()
    assert tuple(reopen_job) == ("REOPEN", 2, "PENDING")
    assert cycle_title(str(reopened["base_title"]), int(reopened["reopen_count"])) == (
        "[M1] [test] Question 2"
    )


def test_lifecycle_queue_claim_completion_and_status_are_safe(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "lifecycle.sqlite3")
    repo.create_case(
        case_id="case-1",
        thread_id=1,
        author_id=3,
        module_code="M1",
        keyword="test",
        ai_content_permission=False,
        canonical_title="[M1] [test] Question",
        initial_snapshot={"body": "hello"},
        class_code="01",
    )
    assert repo.claim_case(1, 9) is not None
    assert repo.close_case(1) is not None
    assert repo.close_case(1) is None

    before_status = repo._connection.total_changes
    snapshot = repo.safe_runtime_status()
    assert repo._connection.total_changes == before_status
    assert snapshot["schema_version"] == MIGRATIONS[-1].version
    assert snapshot["queues"]["discord"] == 1
    assert snapshot["failures"]["discord"] == 0

    claim = repo.claim_discord_lifecycle_job("test-worker")
    assert claim is not None
    assert repo.mark_discord_lifecycle_stage(
        claim.job_id, claim.claim_token, "NOTICE_SENT", control_message_id=99
    )
    assert repo.complete_discord_lifecycle_job(claim.job_id, claim.claim_token)
    completed = repo.get_discord_lifecycle_job(claim.job_id)
    assert completed is not None
    assert completed["status"] == "COMPLETED"
    assert completed["control_message_id"] == 99
    assert repo.safe_runtime_status()["queues"]["discord"] == 0


def test_reopen_requires_closed_and_never_mutates_a_tracked_case(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "test.sqlite3")
    repo.create_case(
        case_id="case-1",
        thread_id=1,
        author_id=3,
        module_code="M1",
        keyword="test",
        ai_content_permission=False,
        canonical_title="[M1] [test] Question 7",
        initial_snapshot={"title": "[M1] [test] Question 7", "body": "hello"},
        class_code="01",
    )

    assert repo.reopen_case(1) is None
    tracked = repo.get_case_by_thread(1)
    assert tracked is not None
    assert tracked["status"] == "OPEN"
    assert tracked["reopen_count"] == 0
    assert tracked["canonical_title"] == "[M1] [test] Question 7"
    assert repo.claim_case(1, 9) is not None

    for expected_count, expected_title in (
        (1, "[M1] [test] Question 7 2"),
        (2, "[M1] [test] Question 7 3"),
        (3, "[M1] [test] Question 7 4"),
    ):
        assert repo.close_case(1) is not None
        reopened = repo.reopen_case(1)
        assert reopened is not None
        assert reopened["reopen_count"] == expected_count
        actual_title = cycle_title(str(reopened["base_title"]), int(reopened["reopen_count"]))
        assert actual_title == expected_title

        assert repo.reopen_case(1) is None
        still_tracked = repo.get_case_by_thread(1)
        assert still_tracked is not None
        assert still_tracked["reopen_count"] == expected_count
        assert still_tracked["canonical_title"] == "[M1] [test] Question 7"


def test_migration_populates_base_title_from_initial_snapshot(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE cases (
            case_id TEXT PRIMARY KEY,
            case_number TEXT NOT NULL UNIQUE,
            thread_id INTEGER NOT NULL UNIQUE,
            author_id INTEGER NOT NULL,
            module_code TEXT NOT NULL,
            keyword TEXT NOT NULL,
            ai_content_permission INTEGER NOT NULL,
            canonical_title TEXT NOT NULL,
            status TEXT NOT NULL,
            reopen_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            closed_at TEXT,
            last_staff_response_at TEXT,
            initial_snapshot_json TEXT NOT NULL,
            dump_version INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    connection.execute(
        """
        INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy-case",
            "C00-ABC123-0101-0000",
            1,
            3,
            "M1",
            "test",
            0,
            "[M1] [test] Question 7 2",
            "CLOSED",
            1,
            "2026-01-01T00:00:00+00:00",
            "2026-01-02T00:00:00+00:00",
            None,
            json.dumps({"title": "[M1] [test] Question 7", "body": "hello"}),
            0,
        ),
    )
    connection.commit()
    connection.close()

    repo = Repository(database_path)
    migrated = repo.get_case_by_thread(1)
    assert migrated is not None
    assert migrated["base_title"] == "[M1] [test] Question 7"
    assert migrated["canonical_title"] == "[M1] [test] Question 7 2"
    assert migrated["status"] == "CLOSED"
    assert migrated["reopen_count"] == 1
