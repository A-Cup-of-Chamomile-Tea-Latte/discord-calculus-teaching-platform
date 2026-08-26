from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest

from discord_course_bots.dump_bot.client import classify_private_dump_error
from discord_course_bots.repository import Repository

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


def test_dump_errors_are_reduced_to_safe_codes() -> None:
    assert classify_private_dump_error(OSError("private path")) == ("FILESYSTEM_ERROR", True)
    assert classify_private_dump_error(RuntimeError("raw student content")) == (
        "EXPORT_VALIDATION_ERROR",
        True,
    )
    assert classify_private_dump_error(ValueError("unexpected raw detail")) == (
        "UNEXPECTED_ERROR",
        True,
    )


def queued_repository(database_path: Path, *, channel_id: int = 101) -> Repository:
    repo = Repository(database_path)
    repo.create_private_support(channel_id, requester_id=201, ai_content_permission=False)
    assert repo.close_private_support(channel_id) is not None
    assert repo.queue_private_dump(channel_id, requested_by=301)
    return repo


def test_only_one_worker_can_claim_a_job(tmp_path: Path) -> None:
    database_path = tmp_path / "atomic.sqlite3"
    first = queued_repository(database_path)
    second = Repository(database_path)
    barrier = Barrier(2)

    def claim(repo: Repository, worker_id: str):
        barrier.wait()
        return repo.claim_private_dump_job(worker_id=worker_id, now=NOW)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda pair: claim(*pair),
                ((first, "worker-a"), (second, "worker-b")),
            )
        )

    claims = [result for result in results if result is not None]
    assert len(claims) == 1
    assert claims[0].attempt_count == 1


def test_expired_lease_can_be_reclaimed_and_stale_worker_cannot_finish(tmp_path: Path) -> None:
    repo = queued_repository(tmp_path / "lease.sqlite3")
    first = repo.claim_private_dump_job(worker_id="worker-a", now=NOW, lease_seconds=60)
    assert first is not None
    assert (
        repo.claim_private_dump_job(
            worker_id="worker-b", now=NOW + timedelta(seconds=59), lease_seconds=60
        )
        is None
    )

    second = repo.claim_private_dump_job(
        worker_id="worker-b", now=NOW + timedelta(seconds=60), lease_seconds=60
    )
    assert second is not None
    assert second.claim_token != first.claim_token
    assert second.attempt_count == 2
    assert not repo.complete_private_dump(101, first.claim_token, "stale-manifest.json")
    assert repo.complete_private_dump(101, second.claim_token, "manifest.json")
    assert not repo.complete_private_dump(101, second.claim_token, "manifest.json")
    row = repo.get_private_dump_job(101)
    assert row is not None
    assert row["status"] == "VERIFIED"
    assert row["manifest_path"] == "manifest.json"


def test_lease_renewal_requires_live_matching_claim(tmp_path: Path) -> None:
    repo = queued_repository(tmp_path / "renew.sqlite3")
    claim = repo.claim_private_dump_job(worker_id="worker-a", now=NOW, lease_seconds=60)
    assert claim is not None
    assert not repo.renew_private_dump_lease(
        channel_id=101,
        claim_token="wrong-token",
        now=NOW + timedelta(seconds=30),
        lease_seconds=60,
    )
    assert repo.renew_private_dump_lease(
        channel_id=101,
        claim_token=claim.claim_token,
        now=NOW + timedelta(seconds=30),
        lease_seconds=60,
    )
    assert not repo.renew_private_dump_lease(
        channel_id=101,
        claim_token=claim.claim_token,
        now=NOW + timedelta(seconds=91),
        lease_seconds=60,
    )


def test_retry_backoff_and_attempt_exhaustion(tmp_path: Path) -> None:
    repo = queued_repository(tmp_path / "retry.sqlite3")

    first = repo.claim_private_dump_job(worker_id="worker", now=NOW)
    assert first is not None
    failed = repo.fail_private_dump_job(
        channel_id=101,
        claim_token=first.claim_token,
        error_code="DISCORD_HTTP_ERROR",
        retryable=True,
        now=NOW,
        max_attempts=3,
        base_retry_seconds=10,
    )
    assert failed is not None
    assert failed.status == "PENDING"
    assert failed.failure_kind == "RETRYABLE"
    assert failed.retry_at == (NOW + timedelta(seconds=10)).isoformat()
    assert repo.claim_private_dump_job(worker_id="worker", now=NOW + timedelta(seconds=9)) is None

    second = repo.claim_private_dump_job(worker_id="worker", now=NOW + timedelta(seconds=10))
    assert second is not None
    assert second.attempt_count == 2
    failed = repo.fail_private_dump_job(
        channel_id=101,
        claim_token=second.claim_token,
        error_code="DISCORD_HTTP_ERROR",
        retryable=True,
        now=NOW + timedelta(seconds=10),
        max_attempts=3,
        base_retry_seconds=10,
    )
    assert failed is not None
    assert failed.retry_at == (NOW + timedelta(seconds=30)).isoformat()

    third = repo.claim_private_dump_job(worker_id="worker", now=NOW + timedelta(seconds=30))
    assert third is not None
    assert third.attempt_count == 3
    exhausted = repo.fail_private_dump_job(
        channel_id=101,
        claim_token=third.claim_token,
        error_code="DISCORD_HTTP_ERROR",
        retryable=True,
        now=NOW + timedelta(seconds=30),
        max_attempts=3,
        base_retry_seconds=10,
    )
    assert exhausted is not None
    assert exhausted.status == "FAILED"
    assert exhausted.failure_kind == "EXHAUSTED"
    assert exhausted.retry_at is None
    assert repo.claim_private_dump_job(worker_id="worker", now=NOW + timedelta(days=1)) is None


def test_permanent_failure_and_error_code_validation(tmp_path: Path) -> None:
    repo = queued_repository(tmp_path / "permanent.sqlite3")
    claim = repo.claim_private_dump_job(worker_id="worker", now=NOW)
    assert claim is not None
    with pytest.raises(ValueError, match="safe uppercase identifier"):
        repo.fail_private_dump_job(
            channel_id=101,
            claim_token=claim.claim_token,
            error_code="student name: raw exception",
            retryable=False,
            now=NOW,
        )
    result = repo.fail_private_dump_job(
        channel_id=101,
        claim_token=claim.claim_token,
        error_code="DISCORD_FORBIDDEN",
        retryable=False,
        now=NOW,
    )
    assert result is not None
    assert result.status == "FAILED"
    assert result.failure_kind == "PERMANENT"
    row = repo.get_private_dump_job(101)
    assert row is not None
    assert row["error"] == "DISCORD_FORBIDDEN"


def test_owner_manual_attention_can_inspect_retry_and_resolve_without_content(
    tmp_path: Path,
) -> None:
    repo = queued_repository(tmp_path / "manual-attention.sqlite3")
    claim = repo.claim_private_dump_job(worker_id="worker", now=NOW)
    assert claim is not None
    assert repo.fail_private_dump_job(
        channel_id=101,
        claim_token=claim.claim_token,
        error_code="DISCORD_FORBIDDEN",
        retryable=False,
        now=NOW,
    )

    items = repo.list_manual_attention()
    assert items == [
        {
            "kind": "PRIVATE_DUMP",
            "itemKey": "101",
            "attempts": 1,
            "errorCode": "DISCORD_FORBIDDEN",
            "updatedAt": repo.get_private_dump_job(101)["updated_at"],
        }
    ]
    inspected = repo.inspect_manual_attention("PRIVATE_DUMP", "101")
    assert inspected is not None
    assert set(inspected) == {
        "kind",
        "itemKey",
        "status",
        "terminal",
        "attempts",
        "errorCode",
        "updatedAt",
        "lastOwnerAction",
        "lastReasonCode",
    }
    assert repo.retry_manual_attention(
        "PRIVATE_DUMP", "101", actor_id=999, reason_code="OWNER_RETRY"
    )
    retried = repo.get_private_dump_job(101)
    assert retried["status"] == "PENDING"
    assert retried["error"] is None


def test_migration_three_preserves_pending_legacy_job(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy-v2.sqlite3"
    repo = queued_repository(database_path)
    repo.close()

    connection = sqlite3.connect(database_path)
    connection.execute("ALTER TABLE private_dump_jobs RENAME TO private_dump_jobs_v3")
    connection.execute(
        """
        CREATE TABLE private_dump_jobs (
            channel_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL,
            requested_by INTEGER NOT NULL,
            requested_at TEXT NOT NULL,
            completed_at TEXT,
            manifest_path TEXT,
            delete_completed_at TEXT,
            error TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO private_dump_jobs(
            channel_id, status, requested_by, requested_at, completed_at,
            manifest_path, delete_completed_at, error
        )
        SELECT channel_id, status, requested_by, requested_at, completed_at,
               manifest_path, delete_completed_at, error
        FROM private_dump_jobs_v3
        """
    )
    connection.execute("DROP TABLE private_dump_jobs_v3")
    connection.execute("DELETE FROM schema_migrations WHERE version = 3")
    connection.execute("PRAGMA user_version = 2")
    connection.commit()
    connection.close()

    migrated = Repository(database_path)
    row = migrated.get_private_dump_job(101)
    assert row is not None
    assert row["status"] == "PENDING"
    assert row["attempt_count"] == 0
    assert row["updated_at"] == row["requested_at"]
    assert migrated.claim_private_dump_job(worker_id="worker", now=NOW) is not None
