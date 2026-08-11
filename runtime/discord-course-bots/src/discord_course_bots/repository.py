from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from discord_course_bots.domain.case_numbers import generate_case_number
from discord_course_bots.jobs import PrivateDumpClaim, PrivateDumpFailureResult
from discord_course_bots.migrations import apply_migrations
from discord_course_bots.queue_engine import (
    ReliableQueueSpec,
    claim_next,
    complete_claim,
    fail_claim,
    renew_claim,
)
from discord_course_bots.repository_time import utc_now_iso

CASE_NUMBER_MAX_ATTEMPTS = 5
SAFE_JOB_ERROR_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
PRIVATE_DUMP_QUEUE = ReliableQueueSpec(
    table="private_dump_jobs",
    key_column="channel_id",
    retry_column="retry_at",
    error_column="error",
    order_column="requested_at",
    retry_status="PENDING",
    terminal_failure_status="FAILED",
    reset_columns_on_claim=("failure_kind", "error"),
)


class Repository:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self._connection
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    @contextmanager
    def immediate_transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            yield self._connection
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def _migrate(self) -> None:
        apply_migrations(self._connection)

    @property
    def schema_version(self) -> int:
        return int(self._connection.execute("PRAGMA user_version").fetchone()[0])

    def migration_history(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                "SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version"
            ).fetchall()
        )

    def close(self) -> None:
        self._connection.close()

    def set_config(self, key: str, value: str | int) -> None:
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO runtime_config(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                WHERE runtime_config.value IS NOT excluded.value
                """,
                (key, str(value), utc_now_iso()),
            )

    def get_config(self, key: str) -> str | None:
        row = self._connection.execute(
            "SELECT value FROM runtime_config WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None else str(row["value"])

    def get_config_int(self, key: str) -> int | None:
        value = self.get_config(key)
        return None if value is None else int(value)

    def config_snapshot(self) -> dict[str, str]:
        rows = self._connection.execute(
            "SELECT key, value FROM runtime_config ORDER BY key"
        ).fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}

    def create_draft(
        self,
        *,
        thread_id: int,
        forum_channel_id: int,
        author_id: int,
        original_title: str,
        starter_message_id: int | None,
    ) -> None:
        with self.transaction() as db:
            db.execute(
                """
                INSERT OR IGNORE INTO drafts(
                    thread_id, forum_channel_id, author_id, original_title,
                    starter_message_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    forum_channel_id,
                    author_id,
                    original_title,
                    starter_message_id,
                    utc_now_iso(),
                ),
            )

    def set_draft_setup_message(self, thread_id: int, message_id: int) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE drafts SET setup_message_id = ? WHERE thread_id = ?",
                (message_id, thread_id),
            )

    def get_draft(self, thread_id: int) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM drafts WHERE thread_id = ?", (thread_id,)
        ).fetchone()

    def pending_drafts(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                """
                SELECT * FROM drafts
                WHERE deleted_at IS NULL
                  AND thread_id NOT IN (SELECT thread_id FROM cases)
                ORDER BY created_at
                """
            ).fetchall()
        )

    def mark_draft_reminded(self, thread_id: int) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE drafts SET reminded_at = ? WHERE thread_id = ?",
                (utc_now_iso(), thread_id),
            )

    def mark_draft_deleted(self, thread_id: int, reason: str) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE drafts SET deleted_at = ?, delete_reason = ? WHERE thread_id = ?",
                (utc_now_iso(), reason, thread_id),
            )

    def create_case(
        self,
        *,
        case_id: str,
        thread_id: int,
        author_id: int,
        module_code: str,
        keyword: str,
        ai_content_permission: bool,
        canonical_title: str,
        initial_snapshot: dict[str, Any],
    ) -> str:
        for _ in range(CASE_NUMBER_MAX_ATTEMPTS):
            case_number = generate_case_number()
            try:
                with self.transaction() as db:
                    db.execute(
                        """
                        INSERT INTO cases(
                            case_id, case_number, thread_id, author_id, module_code, keyword,
                            ai_content_permission, canonical_title, base_title, status, created_at,
                            initial_snapshot_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'TRACKED', ?, ?)
                        """,
                        (
                            case_id,
                            case_number,
                            thread_id,
                            author_id,
                            module_code,
                            keyword,
                            int(ai_content_permission),
                            canonical_title,
                            canonical_title,
                            utc_now_iso(),
                            json.dumps(initial_snapshot, ensure_ascii=False, sort_keys=True),
                        ),
                    )
            except sqlite3.IntegrityError as exc:
                if "cases.case_number" not in str(exc):
                    raise
            else:
                return case_number
        raise RuntimeError("無法產生不重複的公開案件編號，請稍後再試。")

    def get_case_by_thread(self, thread_id: int) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM cases WHERE thread_id = ?", (thread_id,)
        ).fetchone()

    def tracked_cases(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                "SELECT * FROM cases WHERE status = 'TRACKED' ORDER BY created_at"
            ).fetchall()
        )

    def close_case(self, thread_id: int) -> sqlite3.Row | None:
        with self.transaction() as db:
            db.execute(
                """
                UPDATE cases
                SET status = 'CLOSED', closed_at = ?
                WHERE thread_id = ? AND status = 'TRACKED'
                """,
                (utc_now_iso(), thread_id),
            )
        return self.get_case_by_thread(thread_id)

    def reopen_case(self, thread_id: int) -> sqlite3.Row | None:
        with self.transaction() as db:
            result = db.execute(
                """
                UPDATE cases
                SET status = 'TRACKED', closed_at = NULL, reopen_count = reopen_count + 1
                WHERE thread_id = ? AND status = 'CLOSED'
                """,
                (thread_id,),
            )
            if result.rowcount != 1:
                return None
            return db.execute("SELECT * FROM cases WHERE thread_id = ?", (thread_id,)).fetchone()

    def update_case_title(self, thread_id: int, title: str) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE cases SET canonical_title = ? WHERE thread_id = ?",
                (title, thread_id),
            )

    def create_private_support(
        self, channel_id: int, requester_id: int, ai_content_permission: bool
    ) -> str:
        for _ in range(CASE_NUMBER_MAX_ATTEMPTS):
            case_number = generate_case_number(private_support=True)
            try:
                with self.transaction() as db:
                    db.execute(
                        """
                        INSERT INTO private_support(
                            channel_id, case_number, requester_id, ai_content_permission,
                            status, created_at
                        ) VALUES (?, ?, ?, ?, 'OPEN', ?)
                        """,
                        (
                            channel_id,
                            case_number,
                            requester_id,
                            int(ai_content_permission),
                            utc_now_iso(),
                        ),
                    )
            except sqlite3.IntegrityError as exc:
                if "private_support.case_number" not in str(exc):
                    raise
            else:
                return case_number
        raise RuntimeError("無法產生不重複的私人案件編號，請稍後再試。")

    def get_private_support(self, channel_id: int) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM private_support WHERE channel_id = ?", (channel_id,)
        ).fetchone()

    def close_private_support(self, channel_id: int) -> sqlite3.Row | None:
        with self.transaction() as db:
            result = db.execute(
                """UPDATE private_support SET status = 'CLOSED', closed_at = ?
                WHERE channel_id = ? AND status = 'OPEN'""",
                (utc_now_iso(), channel_id),
            )
            if result.rowcount != 1:
                return None
            return db.execute(
                "SELECT * FROM private_support WHERE channel_id = ?", (channel_id,)
            ).fetchone()

    def queue_private_dump(self, channel_id: int, requested_by: int) -> bool:
        requested_at = utc_now_iso()
        with self.transaction() as db:
            result = db.execute(
                """INSERT INTO private_dump_jobs(
                    channel_id, status, requested_by, requested_at, updated_at
                )
                SELECT channel_id, 'PENDING', ?, ?, ? FROM private_support
                WHERE channel_id = ? AND status = 'CLOSED'
                ON CONFLICT(channel_id) DO NOTHING""",
                (requested_by, requested_at, requested_at, channel_id),
            )
            return result.rowcount == 1

    def claim_private_dump_job(
        self,
        *,
        worker_id: str,
        now: datetime | None = None,
        lease_seconds: int = 900,
    ) -> PrivateDumpClaim | None:
        with self.immediate_transaction() as db:
            claim = claim_next(
                db,
                PRIVATE_DUMP_QUEUE,
                worker_id=worker_id,
                now=now,
                lease_seconds=lease_seconds,
            )
            if claim is None:
                return None
            channel_id = int(claim.key)
            row = db.execute(
                """
                SELECT job.*, support.case_number
                FROM private_dump_jobs AS job
                JOIN private_support AS support USING(channel_id)
                WHERE job.channel_id = ?
                """,
                (channel_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("Claimed private dump job has no support record")
            return PrivateDumpClaim(
                channel_id=channel_id,
                case_number=str(row["case_number"]),
                claim_token=claim.claim_token,
                claimed_by=claim.claimed_by,
                attempt_count=claim.attempt_count,
                lease_expires_at=claim.lease_expires_at,
            )

    def renew_private_dump_lease(
        self,
        *,
        channel_id: int,
        claim_token: str,
        now: datetime | None = None,
        lease_seconds: int = 900,
    ) -> bool:
        with self.transaction() as db:
            return renew_claim(
                db,
                PRIVATE_DUMP_QUEUE,
                key=channel_id,
                claim_token=claim_token,
                now=now,
                lease_seconds=lease_seconds,
            )

    def complete_private_dump(self, channel_id: int, claim_token: str, manifest_path: str) -> bool:
        completed_at = utc_now_iso()
        with self.transaction() as db:
            return complete_claim(
                db,
                PRIVATE_DUMP_QUEUE,
                key=channel_id,
                claim_token=claim_token,
                final_status="VERIFIED",
                values={
                    "completed_at": completed_at,
                    "manifest_path": manifest_path,
                    "failure_kind": None,
                    "error": None,
                    "updated_at": completed_at,
                },
            )

    def fail_private_dump_job(
        self,
        *,
        channel_id: int,
        claim_token: str,
        error_code: str,
        retryable: bool,
        now: datetime | None = None,
        max_attempts: int = 5,
        base_retry_seconds: int = 30,
        max_retry_seconds: int = 1800,
    ) -> PrivateDumpFailureResult | None:
        if not SAFE_JOB_ERROR_CODE.fullmatch(error_code):
            raise ValueError("error_code must be a safe uppercase identifier")
        with self.immediate_transaction() as db:
            failure = fail_claim(
                db,
                PRIVATE_DUMP_QUEUE,
                key=channel_id,
                claim_token=claim_token,
                error_code=error_code,
                retryable=retryable,
                now=now,
                max_attempts=max_attempts,
                base_retry_seconds=base_retry_seconds,
                max_retry_seconds=max_retry_seconds,
            )
            if failure is None:
                return None
            failure_kind = (
                "RETRYABLE"
                if failure.status == "PENDING"
                else "EXHAUSTED"
                if retryable
                else "PERMANENT"
            )
            db.execute(
                "UPDATE private_dump_jobs SET failure_kind = ? WHERE channel_id = ?",
                (failure_kind, channel_id),
            )
            return PrivateDumpFailureResult(
                channel_id=channel_id,
                status=failure.status,
                attempt_count=failure.attempt_count,
                failure_kind=failure_kind,
                retry_at=failure.retry_at,
            )

    def get_private_dump_job(self, channel_id: int) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM private_dump_jobs WHERE channel_id = ?", (channel_id,)
        ).fetchone()

    def pending_private_deletions(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                "SELECT * FROM private_dump_jobs WHERE status = 'VERIFIED' ORDER BY completed_at"
            ).fetchall()
        )

    def mark_private_deleted(self, channel_id: int) -> None:
        deleted_at = utc_now_iso()
        with self.transaction() as db:
            db.execute(
                "UPDATE private_support SET status = 'DELETED' WHERE channel_id = ?", (channel_id,)
            )
            db.execute(
                """UPDATE private_dump_jobs
                SET status = 'DELETED', delete_completed_at = ?, updated_at = ?
                WHERE channel_id = ? AND status = 'VERIFIED'""",
                (deleted_at, deleted_at, channel_id),
            )
