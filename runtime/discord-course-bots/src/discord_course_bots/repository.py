from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from discord_course_bots.domain.case_numbers import generate_case_number
from discord_course_bots.domain.titles import closed_title, cycle_title
from discord_course_bots.jobs import (
    DiscordLifecycleClaim,
    PrivateDumpClaim,
    PrivateDumpFailureResult,
)
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
SQLITE_TIMEOUT_SECONDS = 5.0
SQLITE_BUSY_TIMEOUT_MILLISECONDS = 5_000
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
DISCORD_LIFECYCLE_QUEUE = ReliableQueueSpec(
    table="discord_lifecycle_jobs",
    key_column="job_id",
    retry_column="next_attempt_at",
    error_column="last_error_code",
    order_column="created_at",
    retry_status="RETRYABLE_FAILURE",
    terminal_failure_status="PERMANENT_FAILURE",
    reset_columns_on_claim=("last_error_code",),
)


class Repository:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            path,
            timeout=SQLITE_TIMEOUT_SECONDS,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MILLISECONDS}")
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
                    now = utc_now_iso()
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
                            now,
                            json.dumps(initial_snapshot, ensure_ascii=False, sort_keys=True),
                        ),
                    )
                    self._record_public_case_transition(
                        db,
                        case_id=case_id,
                        case_number=case_number,
                        event_type="OPEN",
                        previous_status=None,
                        new_status="TRACKED",
                        occurred_at=now,
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
        changed = False
        with self.transaction() as db:
            now = utc_now_iso()
            result = db.execute(
                """
                UPDATE cases
                SET status = 'CLOSED', closed_at = ?
                WHERE thread_id = ? AND status = 'TRACKED'
                """,
                (now, thread_id),
            )
            if result.rowcount == 1:
                changed = True
                row = db.execute(
                    "SELECT case_id, case_number, base_title, reopen_count "
                    "FROM cases WHERE thread_id = ?",
                    (thread_id,),
                ).fetchone()
                self._record_public_case_transition(
                    db,
                    case_id=str(row["case_id"]),
                    case_number=str(row["case_number"]),
                    event_type="CLOSE",
                    previous_status="TRACKED",
                    new_status="CLOSED",
                    occurred_at=now,
                )
                self._enqueue_discord_lifecycle_job(
                    db,
                    case_id=str(row["case_id"]),
                    thread_id=thread_id,
                    transition="CLOSE",
                    cycle_number=int(row["reopen_count"]) + 1,
                    desired_title=closed_title(
                        cycle_title(str(row["base_title"]), int(row["reopen_count"])),
                        automatic=False,
                    ),
                    created_at=now,
                )
        return self.get_case_by_thread(thread_id) if changed else None

    def reopen_case(self, thread_id: int) -> sqlite3.Row | None:
        with self.transaction() as db:
            now = utc_now_iso()
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
            row = db.execute("SELECT * FROM cases WHERE thread_id = ?", (thread_id,)).fetchone()
            self._record_public_case_transition(
                db,
                case_id=str(row["case_id"]),
                case_number=str(row["case_number"]),
                event_type="REOPEN",
                previous_status="CLOSED",
                new_status="TRACKED",
                occurred_at=now,
            )
            self._enqueue_discord_lifecycle_job(
                db,
                case_id=str(row["case_id"]),
                thread_id=thread_id,
                transition="REOPEN",
                cycle_number=int(row["reopen_count"]) + 1,
                desired_title=cycle_title(str(row["base_title"]), int(row["reopen_count"])),
                created_at=now,
            )
            return row

    def has_unfinished_discord_lifecycle_job(self, case_id: str) -> bool:
        row = self._connection.execute(
            """
            SELECT 1 FROM discord_lifecycle_jobs
            WHERE case_id = ? AND status != 'COMPLETED'
            LIMIT 1
            """,
            (case_id,),
        ).fetchone()
        return row is not None

    def _enqueue_discord_lifecycle_job(
        self,
        db: sqlite3.Connection,
        *,
        case_id: str,
        thread_id: int,
        transition: str,
        cycle_number: int,
        desired_title: str,
        created_at: str,
    ) -> None:
        db.execute(
            """
            INSERT INTO discord_lifecycle_jobs(
                job_id, case_id, thread_id, transition, cycle_number,
                desired_title, status, stage, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 'PENDING', ?, ?)
            ON CONFLICT(case_id, transition, cycle_number) DO NOTHING
            """,
            (
                f"discord-{uuid.uuid4().hex}",
                case_id,
                thread_id,
                transition,
                cycle_number,
                desired_title,
                created_at,
                created_at,
            ),
        )

    def get_discord_lifecycle_job(self, job_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM discord_lifecycle_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()

    def claim_discord_lifecycle_job(
        self, worker_id: str, *, lease_seconds: int = 1_200
    ) -> DiscordLifecycleClaim | None:
        with self.immediate_transaction() as db:
            claim = claim_next(
                db,
                DISCORD_LIFECYCLE_QUEUE,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
            )
        if claim is None:
            return None
        return DiscordLifecycleClaim(
            job_id=str(claim.key),
            claim_token=claim.claim_token,
            claimed_by=claim.claimed_by,
            attempt_count=claim.attempt_count,
            lease_expires_at=claim.lease_expires_at,
        )

    def mark_discord_lifecycle_stage(
        self,
        job_id: str,
        claim_token: str,
        stage: str,
        *,
        control_message_id: int | None = None,
    ) -> bool:
        if stage not in {"NOTICE_SENT", "DISCORD_APPLIED"}:
            raise ValueError("Unsupported Discord lifecycle stage")
        now = utc_now_iso()
        with self.transaction() as db:
            result = db.execute(
                """
                UPDATE discord_lifecycle_jobs
                SET stage = ?, control_message_id = COALESCE(?, control_message_id),
                    updated_at = ?
                WHERE job_id = ? AND status = 'CLAIMED' AND claim_token = ?
                """,
                (stage, control_message_id, now, job_id, claim_token),
            )
            return result.rowcount == 1

    def complete_discord_lifecycle_job(self, job_id: str, claim_token: str) -> bool:
        now = utc_now_iso()
        with self.transaction() as db:
            return complete_claim(
                db,
                DISCORD_LIFECYCLE_QUEUE,
                key=job_id,
                claim_token=claim_token,
                final_status="COMPLETED",
                values={"stage": "DISCORD_APPLIED", "completed_at": now, "updated_at": now},
            )

    def fail_discord_lifecycle_job(
        self,
        job_id: str,
        claim_token: str,
        *,
        error_code: str,
        retryable: bool,
    ):
        if not SAFE_JOB_ERROR_CODE.fullmatch(error_code):
            raise ValueError("Unsafe lifecycle error code")
        with self.transaction() as db:
            return fail_claim(
                db,
                DISCORD_LIFECYCLE_QUEUE,
                key=job_id,
                claim_token=claim_token,
                error_code=error_code,
                retryable=retryable,
                max_attempts=8,
                base_retry_seconds=15,
                max_retry_seconds=300,
            )

    def safe_runtime_status(self) -> dict[str, Any]:
        health_rows = self._connection.execute(
            "SELECT service_key, status, checked_at FROM service_health ORDER BY service_key"
        ).fetchall()
        queue_depths = {
            "discord": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM discord_lifecycle_jobs "
                    "WHERE status NOT IN ('COMPLETED', 'PERMANENT_FAILURE')"
                ).fetchone()[0]
            ),
            "projection": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM projection_outbox "
                    "WHERE status NOT IN ('COMPLETED', 'PERMANENT_FAILURE')"
                ).fetchone()[0]
            ),
            "private_dump": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM private_dump_jobs "
                    "WHERE status NOT IN ('DELETED', 'FAILED')"
                ).fetchone()[0]
            ),
        }
        failures = {
            "discord": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM discord_lifecycle_jobs WHERE status = 'PERMANENT_FAILURE'"
                ).fetchone()[0]
            ),
            "projection": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM projection_outbox WHERE status = 'PERMANENT_FAILURE'"
                ).fetchone()[0]
            ),
            "private_dump": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM private_dump_jobs WHERE status = 'FAILED'"
                ).fetchone()[0]
            ),
        }
        now = datetime.now(UTC)
        health: list[dict[str, str]] = []
        for row in health_rows:
            checked = datetime.fromisoformat(str(row["checked_at"]))
            if checked.tzinfo is None:
                checked = checked.replace(tzinfo=UTC)
            age_seconds = (now - checked.astimezone(UTC)).total_seconds()
            reported = str(row["status"])
            state = (
                reported
                if reported != "HEALTHY"
                else ("HEALTHY" if age_seconds <= 300 else "STALE")
            )
            health.append({"service": str(row["service_key"]), "state": state})
        return {
            "schema_version": self.schema_version,
            "health": health,
            "queues": queue_depths,
            "failures": failures,
        }

    def _record_public_case_transition(
        self,
        db: sqlite3.Connection,
        *,
        case_id: str,
        case_number: str,
        event_type: str,
        previous_status: str | None,
        new_status: str,
        occurred_at: str,
    ) -> None:
        stream = db.execute(
            "SELECT last_local_projection_version FROM sync_state "
            "WHERE stream_name = 'production-local-sheet-projection'"
        ).fetchone()
        if stream is None:
            raise RuntimeError("PRODUCTION_SYNC_STREAM_MISSING")
        version = int(stream[0]) + 1
        db.execute(
            "UPDATE sync_state SET last_local_projection_version = ?, updated_at = ? "
            "WHERE stream_name = 'production-local-sheet-projection'",
            (version, occurred_at),
        )
        event_id = f"evt-{uuid.uuid4().hex}"
        db.execute(
            """
            INSERT INTO case_lifecycle_events(
                event_id, case_id, case_ref, event_type, previous_status, new_status,
                source_kind, correlation_id, occurred_at, synthetic
            ) VALUES (?, ?, ?, ?, ?, ?, 'DISCORD', ?, ?, 0)
            """,
            (
                event_id,
                case_id,
                case_number,
                event_type,
                previous_status,
                new_status,
                f"discord:{event_id}",
                occurred_at,
            ),
        )
        work = (
            (f"prj-{event_id}-case", "UPSERT_CURRENT_STATE", "CASEBOARD"),
            (f"prj-{event_id}-history", "APPEND_HISTORY", "HISTORY"),
            (f"prj-{event_id}-overview", "UPSERT_CURRENT_STATE", "OVERVIEW"),
            (f"prj-{event_id}-operations", "UPDATE_OPERATIONS", "OPERATIONS"),
        )
        for projection_id, outbox_event, scope in work:
            db.execute(
                """
                INSERT INTO projection_outbox(
                    projection_id, aggregate_type, aggregate_ref, event_type,
                    projection_scope, source_version, status, created_at, updated_at
                ) VALUES (?, 'PUBLIC_CASE', ?, ?, ?, ?, 'PENDING', ?, ?)
                """,
                (
                    projection_id,
                    case_number,
                    outbox_event,
                    scope,
                    version,
                    occurred_at,
                    occurred_at,
                ),
            )

    def update_case_title(self, thread_id: int, title: str) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE cases SET canonical_title = ? WHERE thread_id = ?",
                (title, thread_id),
            )

    def update_service_health(
        self,
        *,
        service_key: str,
        service: str,
        component: str,
        status: str = "HEALTHY",
        mode: str = "PRODUCTION",
        safe_error_code: str | None = None,
    ) -> None:
        now = utc_now_iso()
        with self.immediate_transaction() as db:
            current = db.execute(
                "SELECT status, safe_error_code, checked_at FROM service_health "
                "WHERE service_key = ?",
                (service_key,),
            ).fetchone()
            changed = (
                current is None
                or str(current["status"]) != status
                or (current["safe_error_code"] or None) != safe_error_code
            )
            last_published = None
            if current is not None:
                last_published = datetime.fromisoformat(str(current["checked_at"]))
                if last_published.tzinfo is None:
                    last_published = last_published.replace(tzinfo=UTC)
            publish_due = (
                last_published is None
                or (datetime.now(UTC) - last_published.astimezone(UTC)).total_seconds() >= 300
            )
            db.execute(
                """
                INSERT INTO service_health(
                    service_key, service, component, status, mode, version,
                    last_heartbeat_at, last_success_at, safe_error_code, next_action, checked_at
                ) VALUES (?, ?, ?, ?, ?, 'phase-2c', ?, ?, ?, ?, ?)
                ON CONFLICT(service_key) DO UPDATE SET
                    service=excluded.service, component=excluded.component,
                    status=excluded.status, mode=excluded.mode,
                    last_heartbeat_at=excluded.last_heartbeat_at,
                    last_success_at=excluded.last_success_at,
                    safe_error_code=excluded.safe_error_code,
                    next_action=excluded.next_action,
                    checked_at=excluded.checked_at
                """,
                (
                    service_key,
                    service,
                    component,
                    status,
                    mode,
                    now,
                    now if status == "HEALTHY" else None,
                    safe_error_code,
                    "none" if safe_error_code is None else "inspect service",
                    now,
                ),
            )
            if not changed and not publish_due:
                return
            row = db.execute(
                "SELECT last_local_projection_version FROM sync_state "
                "WHERE stream_name = 'production-local-sheet-projection'"
            ).fetchone()
            if row is None:
                raise RuntimeError("PRODUCTION_SYNC_STREAM_MISSING")
            version = int(row[0]) + 1
            db.execute(
                "UPDATE sync_state SET last_local_projection_version = ?, updated_at = ? "
                "WHERE stream_name = 'production-local-sheet-projection'",
                (version, now),
            )
            db.execute(
                """
                INSERT INTO projection_outbox(
                    projection_id, aggregate_type, aggregate_ref, event_type,
                    projection_scope, source_version, status, created_at, updated_at
                ) VALUES (?, 'OPERATIONS', ?, 'UPDATE_OPERATIONS', 'OPERATIONS',
                          ?, 'PENDING', ?, ?)
                """,
                (f"prj-health-{service_key}-{version}", service_key, version, now, now),
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
