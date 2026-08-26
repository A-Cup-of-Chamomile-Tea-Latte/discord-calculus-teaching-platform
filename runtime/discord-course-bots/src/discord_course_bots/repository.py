from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from discord_course_bots.domain.applicants import (
    applicant_identity_key,
    normalize_class_code,
    normalize_discord_username,
    normalize_email,
    normalize_ntu_email,
    normalize_optional_gmail,
)
from discord_course_bots.domain.case_numbers import generate_case_number
from discord_course_bots.domain.titles import canonical_title, closed_title, cycle_title
from discord_course_bots.jobs import (
    CourseRoleClaim,
    DiscordLifecycleClaim,
    DmClaim,
    EmailDeliveryClaim,
    PrivateDumpClaim,
    PrivateDumpFailureResult,
    PrivateOpenClaim,
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
PRIVATE_OPEN_QUEUE = ReliableQueueSpec(
    table="private_open_requests",
    key_column="interaction_id",
    retry_column="next_attempt_at",
    error_column="last_error_code",
    order_column="created_at",
    retry_status="RETRYABLE_FAILURE",
    terminal_failure_status="PERMANENT_FAILURE",
    reset_columns_on_claim=("last_error_code",),
)
DM_OUTBOX_QUEUE = ReliableQueueSpec(
    table="discord_dm_outbox",
    key_column="message_key",
    retry_column="next_attempt_at",
    error_column="last_error_code",
    order_column="created_at",
    retry_status="RETRYABLE_FAILURE",
    terminal_failure_status="PERMANENT_FAILURE",
    reset_columns_on_claim=("last_error_code",),
)
COURSE_ROLE_QUEUE = ReliableQueueSpec(
    table="course_role_jobs",
    key_column="job_id",
    retry_column="next_attempt_at",
    error_column="last_error_code",
    order_column="created_at",
    retry_status="RETRYABLE_FAILURE",
    terminal_failure_status="PERMANENT_FAILURE",
    reset_columns_on_claim=("last_error_code",),
)
EMAIL_DELIVERY_QUEUE = ReliableQueueSpec(
    table="email_delivery_outbox",
    key_column="delivery_id",
    retry_column="next_attempt_at",
    error_column="last_error_code",
    order_column="created_at",
    retry_status="RETRYABLE_FAILURE",
    terminal_failure_status="PERMANENT_FAILURE",
    reset_columns_on_claim=("last_error_code",),
)
ACTIVE_CASE_STATUSES = frozenset({"OPEN", "TRACKED", "IDLE"})
CLOSED_CASE_STATUSES = frozenset({"CLOSED", "AUTO_CLOSED"})
LEGACY_STATUS_MAP = {
    "WAITING_FOR_STUDENT": "IDLE",
    "ANSWERED": "TRACKED",
    "ESCALATED": "TRACKED",
    "TEMPORARILY_CLOSED": "IDLE",
    "REOPENED": "TRACKED",
}


def canonical_case_status(value: str) -> str:
    return LEGACY_STATUS_MAP.get(value, value)


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
        ai_content_permission: bool,
        module_code: str = "M1",
        keyword: str = "隱密支援",
        canonical_title: str,
        initial_snapshot: dict[str, Any],
        class_code: str | None = None,
        guest: bool = False,
        private_support: bool = False,
    ) -> str:
        for _ in range(CASE_NUMBER_MAX_ATTEMPTS):
            case_number = (
                generate_case_number(private_support=True)
                if private_support
                else (
                    generate_case_number(guest=True)
                    if guest
                    else generate_case_number(class_code=class_code)
                )
            )
            try:
                with self.transaction() as db:
                    now = utc_now_iso()
                    db.execute(
                        """
                        INSERT INTO cases(
                            case_id, case_number, thread_id, author_id, module_code, keyword,
                            ai_content_permission, canonical_title, base_title, status, created_at,
                            initial_snapshot_json, visibility, last_student_activity_at,
                            updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?)
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
                            "PRIVATE" if private_support else "PUBLIC",
                            now,
                            now,
                        ),
                    )
                    self._record_public_case_transition(
                        db,
                        case_id=case_id,
                        case_number=case_number,
                        event_type="OPEN",
                        previous_status=None,
                        new_status="OPEN",
                        occurred_at=now,
                        project_public=not private_support,
                    )
            except sqlite3.IntegrityError as exc:
                if "cases.case_number" not in str(exc):
                    raise
            else:
                return case_number
        case_kind = "隱密" if private_support else "公開"
        raise RuntimeError(f"無法產生不重複的{case_kind}案件編號，請稍後再試。")

    def get_case_by_thread(self, thread_id: int) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM cases WHERE thread_id = ?", (thread_id,)
        ).fetchone()

    def safe_case_projection(
        self, case_number: str, *, allow_private: bool
    ) -> dict[str, Any] | None:
        normalized = case_number.strip().upper()
        if normalized.startswith("GUEST-"):
            normalized = "Guest-" + normalized[6:]
        row = self._connection.execute(
            "SELECT * FROM cases WHERE case_number = ?", (normalized,)
        ).fetchone()
        if row is None or (str(row["visibility"]) == "PRIVATE" and not allow_private):
            return None
        return {
            "caseNumber": str(row["case_number"]),
            "caseType": "PRIVATE_SUPPORT" if str(row["visibility"]) == "PRIVATE" else "GENERAL",
            "status": canonical_case_status(str(row["status"])),
            "updatedAt": str(row["updated_at"] or row["created_at"]),
            "teachingTeamReplied": bool(row["teaching_team_replied"]),
            "discordUrl": str(row["jump_url"] or ""),
        }

    def set_case_jump_url(self, thread_id: int, jump_url: str) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE cases SET jump_url = ?, updated_at = ? WHERE thread_id = ?",
                (jump_url, utc_now_iso(), thread_id),
            )

    def tracked_cases(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                "SELECT * FROM cases WHERE status IN ('OPEN', 'TRACKED', 'IDLE') "
                "ORDER BY created_at"
            ).fetchall()
        )

    def claim_case(self, thread_id: int, staff_id: int) -> sqlite3.Row | None:
        with self.transaction() as db:
            now = utc_now_iso()
            row = db.execute("SELECT * FROM cases WHERE thread_id = ?", (thread_id,)).fetchone()
            if row is None:
                return None
            current = canonical_case_status(str(row["status"]))
            if current == "TRACKED" and int(row["assigned_staff_id"] or 0) == staff_id:
                return row
            if current != "OPEN":
                return None
            result = db.execute(
                """
                UPDATE cases SET status = 'TRACKED', assigned_staff_id = ?, updated_at = ?
                WHERE thread_id = ? AND status = ?
                """,
                (staff_id, now, thread_id, str(row["status"])),
            )
            if result.rowcount != 1:
                return None
            self._record_public_case_transition(
                db,
                case_id=str(row["case_id"]),
                case_number=str(row["case_number"]),
                event_type="TRACK",
                previous_status=current,
                new_status="TRACKED",
                occurred_at=now,
                project_public=str(row["visibility"]) == "PUBLIC",
            )
            return db.execute("SELECT * FROM cases WHERE thread_id = ?", (thread_id,)).fetchone()

    def record_case_activity(
        self,
        thread_id: int,
        *,
        actor_id: int,
        is_staff: bool,
        occurred_at: datetime | None = None,
    ) -> sqlite3.Row | None:
        at = (occurred_at or datetime.now(UTC)).astimezone(UTC).isoformat()
        with self.transaction() as db:
            row = db.execute("SELECT * FROM cases WHERE thread_id = ?", (thread_id,)).fetchone()
            if row is None:
                return None
            raw_status = str(row["status"])
            status = canonical_case_status(raw_status)
            new_status = status
            event_type = "ACTIVITY"
            assigned_staff_id = row["assigned_staff_id"]
            if is_staff:
                if status == "OPEN":
                    new_status = "TRACKED"
                    event_type = "TRACK"
                    assigned_staff_id = actor_id
                db.execute(
                    """
                    UPDATE cases SET status = ?, assigned_staff_id = ?,
                        last_staff_response_at = ?, teaching_team_replied = 1,
                        idle_at = NULL, idle_reminded_at = NULL, updated_at = ?
                    WHERE thread_id = ?
                    """,
                    (new_status, assigned_staff_id, at, at, thread_id),
                )
            else:
                if status in CLOSED_CASE_STATUSES | {"IDLE"}:
                    new_status = "TRACKED"
                    event_type = "REOPEN"
                db.execute(
                    """
                    UPDATE cases SET status = ?, last_student_activity_at = ?,
                        idle_at = NULL, idle_reminded_at = NULL,
                        closed_at = CASE WHEN ? = 'TRACKED' THEN NULL ELSE closed_at END,
                        reopen_count = reopen_count + CASE
                            WHEN ? IN ('CLOSED', 'AUTO_CLOSED') THEN 1 ELSE 0 END,
                        updated_at = ? WHERE thread_id = ?
                    """,
                    (new_status, at, new_status, status, at, thread_id),
                )
            if new_status != status:
                self._record_public_case_transition(
                    db,
                    case_id=str(row["case_id"]),
                    case_number=str(row["case_number"]),
                    event_type=event_type,
                    previous_status=status,
                    new_status=new_status,
                    occurred_at=at,
                    project_public=str(row["visibility"]) == "PUBLIC",
                )
            updated = db.execute("SELECT * FROM cases WHERE thread_id = ?", (thread_id,)).fetchone()
            if not is_staff and status in CLOSED_CASE_STATUSES:
                self._enqueue_discord_lifecycle_job(
                    db,
                    case_id=str(updated["case_id"]),
                    thread_id=thread_id,
                    transition="REOPEN",
                    cycle_number=int(updated["reopen_count"]) + 1,
                    desired_title=cycle_title(
                        str(updated["base_title"]), int(updated["reopen_count"])
                    ),
                    created_at=at,
                )
            return updated

    def mark_due_cases_idle(
        self, idle_seconds: int, *, now: datetime | None = None
    ) -> list[sqlite3.Row]:
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        cutoff = (moment - timedelta(seconds=idle_seconds)).isoformat()
        at = moment.isoformat()
        changed: list[sqlite3.Row] = []
        with self.transaction() as db:
            rows = db.execute(
                """
                SELECT * FROM cases WHERE status = 'TRACKED'
                  AND last_staff_response_at IS NOT NULL
                  AND last_staff_response_at <= ?
                  AND COALESCE(last_student_activity_at, created_at) <= last_staff_response_at
                """,
                (cutoff,),
            ).fetchall()
            for row in rows:
                result = db.execute(
                    """UPDATE cases SET status = 'IDLE', idle_at = ?,
                       idle_reminded_at = ?, updated_at = ?
                       WHERE case_id = ? AND status = 'TRACKED'""",
                    (at, at, at, str(row["case_id"])),
                )
                if result.rowcount != 1:
                    continue
                self._record_public_case_transition(
                    db,
                    case_id=str(row["case_id"]),
                    case_number=str(row["case_number"]),
                    event_type="IDLE",
                    previous_status="TRACKED",
                    new_status="IDLE",
                    occurred_at=at,
                    source_kind="SCHEDULER",
                    project_public=str(row["visibility"]) == "PUBLIC",
                )
                self._enqueue_discord_lifecycle_job(
                    db,
                    case_id=str(row["case_id"]),
                    thread_id=int(row["thread_id"]),
                    transition="IDLE",
                    cycle_number=int(row["reopen_count"]) + 1,
                    desired_title=cycle_title(str(row["base_title"]), int(row["reopen_count"])),
                    created_at=at,
                )
                changed.append(row)
        return changed

    def auto_close_due_cases(
        self, auto_close_seconds: int, *, now: datetime | None = None
    ) -> list[sqlite3.Row]:
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        cutoff = (moment - timedelta(seconds=auto_close_seconds)).isoformat()
        at = moment.isoformat()
        changed: list[sqlite3.Row] = []
        with self.transaction() as db:
            rows = db.execute(
                """
                SELECT * FROM cases
                WHERE (status = 'IDLE' AND idle_at <= ?)
                   OR (visibility = 'PRIVATE' AND status = 'CLOSED' AND closed_at <= ?)
                """,
                (cutoff, cutoff),
            ).fetchall()
            for row in rows:
                previous_status = canonical_case_status(str(row["status"]))
                result = db.execute(
                    """UPDATE cases SET status = 'AUTO_CLOSED', closed_at = ?, updated_at = ?
                       WHERE case_id = ? AND status = ?""",
                    (at, at, str(row["case_id"]), str(row["status"])),
                )
                if result.rowcount != 1:
                    continue
                self._record_public_case_transition(
                    db,
                    case_id=str(row["case_id"]),
                    case_number=str(row["case_number"]),
                    event_type="AUTO_CLOSE",
                    previous_status=previous_status,
                    new_status="AUTO_CLOSED",
                    occurred_at=at,
                    source_kind="SCHEDULER",
                    project_public=str(row["visibility"]) == "PUBLIC",
                )
                self._enqueue_discord_lifecycle_job(
                    db,
                    case_id=str(row["case_id"]),
                    thread_id=int(row["thread_id"]),
                    transition="AUTO_CLOSE",
                    cycle_number=int(row["reopen_count"]) + 1,
                    desired_title=closed_title(
                        cycle_title(str(row["base_title"]), int(row["reopen_count"])),
                        automatic=True,
                    ),
                    created_at=at,
                )
                if str(row["visibility"]) == "PRIVATE":
                    db.execute(
                        "UPDATE private_support SET status = 'CLOSED', closed_at = ?, "
                        "updated_at = ? WHERE channel_id = ? AND status != 'DELETED'",
                        (at, at, int(row["thread_id"])),
                    )
                changed.append(row)
        return changed

    def close_case(self, thread_id: int, *, now: datetime | None = None) -> sqlite3.Row | None:
        changed = False
        with self.transaction() as db:
            at = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
            before = db.execute("SELECT * FROM cases WHERE thread_id = ?", (thread_id,)).fetchone()
            if before is None or canonical_case_status(str(before["status"])) not in {
                "TRACKED",
                "IDLE",
            }:
                return None
            previous_status = canonical_case_status(str(before["status"]))
            result = db.execute(
                """
                UPDATE cases
                SET status = 'CLOSED', closed_at = ?, updated_at = ?
                WHERE thread_id = ? AND status IN ('TRACKED', 'IDLE')
                """,
                (at, at, thread_id),
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
                    previous_status=previous_status,
                    new_status="CLOSED",
                    occurred_at=at,
                    project_public=str(before["visibility"]) == "PUBLIC",
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
                    created_at=at,
                )
                if str(before["visibility"]) == "PRIVATE":
                    db.execute(
                        "UPDATE private_support SET status = 'CLOSED', closed_at = ?, "
                        "updated_at = ? WHERE channel_id = ? AND status != 'DELETED'",
                        (at, at, thread_id),
                    )
        return self.get_case_by_thread(thread_id) if changed else None

    def reopen_case(self, thread_id: int) -> sqlite3.Row | None:
        with self.transaction() as db:
            now = utc_now_iso()
            before = db.execute("SELECT * FROM cases WHERE thread_id = ?", (thread_id,)).fetchone()
            if before is None or canonical_case_status(str(before["status"])) not in {
                "CLOSED",
                "AUTO_CLOSED",
            }:
                return None
            previous_status = canonical_case_status(str(before["status"]))
            result = db.execute(
                """
                UPDATE cases SET status = 'TRACKED', closed_at = NULL,
                    reopen_count = reopen_count + 1, updated_at = ?
                WHERE thread_id = ? AND status IN ('CLOSED', 'AUTO_CLOSED')
                """,
                (now, thread_id),
            )
            if result.rowcount != 1:
                return None
            row = db.execute("SELECT * FROM cases WHERE thread_id = ?", (thread_id,)).fetchone()
            self._record_public_case_transition(
                db,
                case_id=str(row["case_id"]),
                case_number=str(row["case_number"]),
                event_type="REOPEN",
                previous_status=previous_status,
                new_status="TRACKED",
                occurred_at=now,
                project_public=str(row["visibility"]) == "PUBLIC",
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
            if str(row["visibility"]) == "PRIVATE":
                dump = db.execute(
                    "SELECT status FROM private_dump_jobs WHERE channel_id = ?", (thread_id,)
                ).fetchone()
                if dump is not None:
                    raise RuntimeError("PRIVATE_CASE_ALREADY_ARCHIVED")
                db.execute(
                    "UPDATE private_support SET status = 'OPEN', closed_at = NULL, "
                    "updated_at = ? WHERE channel_id = ? AND status != 'DELETED'",
                    (now, thread_id),
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

    def defer_discord_lifecycle_job(
        self, job_id: str, claim_token: str, *, delay_seconds: int = 10
    ) -> bool:
        """Release a claim while a prerequisite queue is still making progress."""
        if delay_seconds < 1 or delay_seconds > 300:
            raise ValueError("Unsafe lifecycle defer interval")
        now = datetime.now(UTC)
        retry_at = (now + timedelta(seconds=delay_seconds)).isoformat()
        with self.transaction() as db:
            result = db.execute(
                """
                UPDATE discord_lifecycle_jobs
                SET status = 'RETRYABLE_FAILURE', next_attempt_at = ?, claimed_by = NULL,
                    claim_token = NULL, lease_expires_at = NULL,
                    attempt_count = CASE WHEN attempt_count > 0 THEN attempt_count - 1 ELSE 0 END,
                    last_error_code = 'WAITING_FOR_PRIVATE_DUMP', updated_at = ?
                WHERE job_id = ? AND status = 'CLAIMED' AND claim_token = ?
                """,
                (retry_at, now.isoformat(), job_id, claim_token),
            )
            return result.rowcount == 1

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
            "dm": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM discord_dm_outbox "
                    "WHERE status NOT IN ('COMPLETED', 'PERMANENT_FAILURE')"
                ).fetchone()[0]
            ),
            "private_open": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM private_open_requests "
                    "WHERE status NOT IN ('COMPLETED', 'REJECTED', 'PERMANENT_FAILURE')"
                ).fetchone()[0]
            ),
            "course_role": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM course_role_jobs "
                    "WHERE status NOT IN ('COMPLETED', 'PERMANENT_FAILURE')"
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
            "dm": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM discord_dm_outbox WHERE status = 'PERMANENT_FAILURE'"
                ).fetchone()[0]
            ),
            "private_open": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM private_open_requests WHERE status = 'PERMANENT_FAILURE'"
                ).fetchone()[0]
            ),
            "course_role": int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM course_role_jobs WHERE status = 'PERMANENT_FAILURE'"
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

    @staticmethod
    def _manual_attention_source(queue_kind: str) -> tuple[str, str, str, str]:
        sources = {
            "LIFECYCLE": (
                "discord_lifecycle_jobs",
                "job_id",
                "PERMANENT_FAILURE",
                "last_error_code",
            ),
            "PRIVATE_OPEN": (
                "private_open_requests",
                "interaction_id",
                "PERMANENT_FAILURE",
                "last_error_code",
            ),
            "DM": (
                "discord_dm_outbox",
                "message_key",
                "PERMANENT_FAILURE",
                "last_error_code",
            ),
            "COURSE_ROLE": (
                "course_role_jobs",
                "job_id",
                "PERMANENT_FAILURE",
                "last_error_code",
            ),
            "EMAIL": (
                "email_delivery_outbox",
                "delivery_id",
                "PERMANENT_FAILURE",
                "last_error_code",
            ),
            "PRIVATE_DUMP": ("private_dump_jobs", "channel_id", "FAILED", "error"),
        }
        normalized = queue_kind.strip().upper()
        if normalized not in sources:
            raise ValueError("不支援的人工接管 queue kind。")
        return sources[normalized]

    def list_manual_attention(self, *, limit: int = 10) -> list[dict[str, Any]]:
        if limit < 1 or limit > 25:
            raise ValueError("人工接管清單上限必須介於 1 與 25。")
        items: list[dict[str, Any]] = []
        for kind in ("LIFECYCLE", "PRIVATE_OPEN", "DM", "COURSE_ROLE", "EMAIL", "PRIVATE_DUMP"):
            table, key_column, terminal_status, error_column = self._manual_attention_source(kind)
            rows = self._connection.execute(
                f"SELECT {key_column} AS item_key, attempt_count, {error_column} AS error_code, "
                f"updated_at FROM {table} WHERE status = ? ORDER BY updated_at LIMIT ?",
                (terminal_status, limit),
            ).fetchall()
            for row in rows:
                latest = self._connection.execute(
                    """SELECT action FROM manual_attention_actions
                       WHERE queue_kind = ? AND item_key = ?
                       ORDER BY created_at DESC, action_id DESC LIMIT 1""",
                    (kind, str(row["item_key"])),
                ).fetchone()
                if latest is not None and str(latest["action"]) == "RESOLVE":
                    continue
                items.append(
                    {
                        "kind": kind,
                        "itemKey": str(row["item_key"]),
                        "attempts": int(row["attempt_count"]),
                        "errorCode": str(row["error_code"] or "UNKNOWN"),
                        "updatedAt": str(row["updated_at"] or ""),
                    }
                )
        return sorted(items, key=lambda item: item["updatedAt"])[:limit]

    def inspect_manual_attention(self, queue_kind: str, item_key: str) -> dict[str, Any] | None:
        kind = queue_kind.strip().upper()
        table, key_column, terminal_status, error_column = self._manual_attention_source(kind)
        if not item_key or len(item_key) > 128:
            raise ValueError("人工接管 item key 無效。")
        row = self._connection.execute(
            f"SELECT {key_column} AS item_key, status, attempt_count, "
            f"{error_column} AS error_code, updated_at FROM {table} WHERE {key_column} = ?",
            (int(item_key) if kind == "PRIVATE_DUMP" else item_key,),
        ).fetchone()
        if row is None:
            return None
        latest = self._connection.execute(
            """SELECT action, reason_code, created_at FROM manual_attention_actions
               WHERE queue_kind = ? AND item_key = ?
               ORDER BY created_at DESC, action_id DESC LIMIT 1""",
            (kind, item_key),
        ).fetchone()
        return {
            "kind": kind,
            "itemKey": str(row["item_key"]),
            "status": str(row["status"]),
            "terminal": str(row["status"]) == terminal_status,
            "attempts": int(row["attempt_count"]),
            "errorCode": str(row["error_code"] or "NONE"),
            "updatedAt": str(row["updated_at"] or ""),
            "lastOwnerAction": None if latest is None else str(latest["action"]),
            "lastReasonCode": None if latest is None else str(latest["reason_code"]),
        }

    def _record_manual_attention_action(
        self,
        db: sqlite3.Connection,
        *,
        queue_kind: str,
        item_key: str,
        action: str,
        actor_id: int,
        reason_code: str,
    ) -> None:
        if actor_id <= 0 or not SAFE_JOB_ERROR_CODE.fullmatch(reason_code):
            raise ValueError("人工接管 actor 或 reason code 無效。")
        db.execute(
            """INSERT INTO manual_attention_actions(
                   action_id, queue_kind, item_key, action, actor_id, reason_code, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                f"attention-{uuid.uuid4().hex}",
                queue_kind,
                item_key,
                action,
                actor_id,
                reason_code,
                utc_now_iso(),
            ),
        )

    def retry_manual_attention(
        self, queue_kind: str, item_key: str, *, actor_id: int, reason_code: str
    ) -> bool:
        kind = queue_kind.strip().upper()
        table, key_column, terminal_status, _ = self._manual_attention_source(kind)
        key: str | int = int(item_key) if kind == "PRIVATE_DUMP" else item_key
        now = utc_now_iso()
        with self.transaction() as db:
            if kind == "EMAIL":
                payload = db.execute(
                    "SELECT destination, verification_code FROM email_delivery_outbox "
                    "WHERE delivery_id = ? AND status = 'PERMANENT_FAILURE'",
                    (key,),
                ).fetchone()
                if (
                    payload is None
                    or payload["destination"] is None
                    or payload["verification_code"] is None
                ):
                    return False
            if kind == "PRIVATE_DUMP":
                result = db.execute(
                    """UPDATE private_dump_jobs SET status = 'PENDING', retry_at = NULL,
                       claimed_by = NULL, claim_token = NULL, lease_expires_at = NULL,
                       failure_kind = NULL, error = NULL, updated_at = ?
                       WHERE channel_id = ? AND status = ?""",
                    (now, key, terminal_status),
                )
            else:
                result = db.execute(
                    f"""UPDATE {table} SET status = 'RETRYABLE_FAILURE', next_attempt_at = NULL,
                       claimed_by = NULL, claim_token = NULL, lease_expires_at = NULL,
                       last_error_code = NULL, updated_at = ?
                       WHERE {key_column} = ? AND status = ?""",
                    (now, key, terminal_status),
                )
            if result.rowcount != 1:
                return False
            self._record_manual_attention_action(
                db,
                queue_kind=kind,
                item_key=item_key,
                action="RETRY",
                actor_id=actor_id,
                reason_code=reason_code,
            )
            return True

    def resolve_manual_attention(
        self, queue_kind: str, item_key: str, *, actor_id: int, reason_code: str
    ) -> bool:
        kind = queue_kind.strip().upper()
        table, key_column, terminal_status, _ = self._manual_attention_source(kind)
        key: str | int = int(item_key) if kind == "PRIVATE_DUMP" else item_key
        row = self._connection.execute(
            f"SELECT 1 FROM {table} WHERE {key_column} = ? AND status = ?",
            (key, terminal_status),
        ).fetchone()
        if row is None:
            return False
        with self.transaction() as db:
            self._record_manual_attention_action(
                db,
                queue_kind=kind,
                item_key=item_key,
                action="RESOLVE",
                actor_id=actor_id,
                reason_code=reason_code,
            )
            return True

    def create_replacement_private_request(
        self,
        *,
        previous_case_number: str,
        requester_id: int,
        actor_id: int,
        reason_code: str,
        guild_id: int,
        module_code: str,
    ) -> sqlite3.Row:
        previous = self._connection.execute(
            "SELECT * FROM cases WHERE case_number = ? AND visibility = 'PRIVATE'",
            (previous_case_number.strip().upper(),),
        ).fetchone()
        if previous is None or canonical_case_status(str(previous["status"])) != "AUTO_CLOSED":
            raise RuntimeError("REPLACEMENT_SOURCE_NOT_ELIGIBLE")
        interaction_id = f"manual-replacement-{uuid.uuid4().hex}"
        request = self.begin_private_open_request(
            interaction_id=interaction_id,
            guild_id=guild_id,
            requester_id=requester_id,
            module_code=module_code,
            keyword="人工接管",
            ai_content_permission=False,
        )
        if str(request["status"]) == "REJECTED":
            raise RuntimeError("REPLACEMENT_REQUEST_REJECTED")
        with self.transaction() as db:
            db.execute(
                "UPDATE private_open_requests SET replacement_for_case_id = ? "
                "WHERE interaction_id = ?",
                (str(previous["case_id"]), interaction_id),
            )
            self._record_manual_attention_action(
                db,
                queue_kind="PRIVATE_CASE",
                item_key=str(previous["case_number"]),
                action="REPLACEMENT_CASE",
                actor_id=actor_id,
                reason_code=reason_code,
            )
        return self.get_private_open_request(interaction_id)

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
        source_kind: str = "DISCORD",
        project_public: bool = True,
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                event_id,
                case_id,
                case_number,
                event_type,
                previous_status,
                new_status,
                source_kind,
                f"discord:{event_id}",
                occurred_at,
            ),
        )
        if not project_public:
            return
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

    def begin_private_open_request(
        self,
        *,
        interaction_id: str,
        guild_id: int,
        requester_id: int,
        ai_content_permission: bool,
        module_code: str = "M1",
        keyword: str = "隱密支援",
        now: datetime | None = None,
        capacity: int = 50,
    ) -> sqlite3.Row:
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        at = moment.isoformat()
        with self.immediate_transaction() as db:
            existing = db.execute(
                "SELECT * FROM private_open_requests WHERE interaction_id = ?",
                (interaction_id,),
            ).fetchone()
            if existing is not None:
                return existing
            windows = (
                (120, 1, "RATE_2_MINUTES"),
                (3600, 5, "RATE_1_HOUR"),
                (86400, 20, "RATE_24_HOURS"),
            )
            rejection: str | None = None
            for seconds, limit, code in windows:
                cutoff = (moment - timedelta(seconds=seconds)).isoformat()
                count = int(
                    db.execute(
                        """
                        SELECT COUNT(*) FROM private_open_requests
                        WHERE requester_id = ? AND created_at > ?
                          AND status != 'REJECTED'
                        """,
                        (requester_id, cutoff),
                    ).fetchone()[0]
                )
                if count >= limit:
                    rejection = code
                    break
            pending = int(
                db.execute(
                    """SELECT COUNT(*) FROM private_open_requests
                       WHERE status IN ('PENDING', 'CLAIMED', 'RETRYABLE_FAILURE')"""
                ).fetchone()[0]
            )
            status = "REJECTED" if rejection else "PENDING"
            if rejection is None and pending >= capacity:
                rejection = "CAPACITY_WAIT"
            db.execute(
                """
                INSERT INTO private_open_requests(
                    interaction_id, idempotency_key, guild_id, requester_id,
                    module_code, keyword, ai_content_permission, status, rejection_code,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction_id,
                    f"private-open:{guild_id}:{requester_id}:{interaction_id}",
                    guild_id,
                    requester_id,
                    module_code,
                    keyword,
                    int(ai_content_permission),
                    status,
                    rejection,
                    at,
                    at,
                ),
            )
            return db.execute(
                "SELECT * FROM private_open_requests WHERE interaction_id = ?",
                (interaction_id,),
            ).fetchone()

    def get_private_open_request(self, interaction_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM private_open_requests WHERE interaction_id = ?", (interaction_id,)
        ).fetchone()

    def claim_private_open_request(self, worker_id: str) -> PrivateOpenClaim | None:
        with self.immediate_transaction() as db:
            claim = claim_next(db, PRIVATE_OPEN_QUEUE, worker_id=worker_id, lease_seconds=300)
        if claim is None:
            return None
        return PrivateOpenClaim(
            interaction_id=str(claim.key),
            claim_token=claim.claim_token,
            claimed_by=claim.claimed_by,
            attempt_count=claim.attempt_count,
            lease_expires_at=claim.lease_expires_at,
        )

    def release_private_open_claim(self, interaction_id: str, claim_token: str) -> bool:
        now = utc_now_iso()
        with self.transaction() as db:
            result = db.execute(
                """UPDATE private_open_requests SET status = 'PENDING', claim_token = NULL,
                   claimed_by = NULL, lease_expires_at = NULL, next_attempt_at = NULL,
                   updated_at = ? WHERE interaction_id = ? AND status = 'CLAIMED'
                   AND claim_token = ?""",
                (now, interaction_id, claim_token),
            )
            return result.rowcount == 1

    def mark_private_channel_created(
        self, interaction_id: str, claim_token: str, *, channel_id: int, jump_url: str
    ) -> bool:
        now = utc_now_iso()
        with self.transaction() as db:
            result = db.execute(
                """UPDATE private_open_requests SET channel_id = ?, jump_url = ?, updated_at = ?
                   WHERE interaction_id = ? AND status = 'CLAIMED' AND claim_token = ?""",
                (channel_id, jump_url, now, interaction_id, claim_token),
            )
            return result.rowcount == 1

    def fail_private_open_request(
        self, interaction_id: str, claim_token: str, *, error_code: str, retryable: bool
    ) -> bool:
        if not SAFE_JOB_ERROR_CODE.fullmatch(error_code):
            raise ValueError("Unsafe private request error code")
        with self.transaction() as db:
            result = fail_claim(
                db,
                PRIVATE_OPEN_QUEUE,
                key=interaction_id,
                claim_token=claim_token,
                error_code=error_code,
                retryable=retryable,
                max_attempts=8,
                base_retry_seconds=15,
                max_retry_seconds=300,
            )
            return result is not None

    def complete_private_open_request(
        self,
        *,
        interaction_id: str,
        channel_id: int,
        jump_url: str,
        requester_id: int,
        ai_content_permission: bool,
    ) -> sqlite3.Row:
        request = self._connection.execute(
            "SELECT * FROM private_open_requests WHERE interaction_id = ?", (interaction_id,)
        ).fetchone()
        if request is None:
            raise RuntimeError("PRIVATE_REQUEST_MISSING")
        if str(request["status"]) == "COMPLETED":
            return request
        existing_case = self.get_case_by_thread(channel_id)
        if existing_case is None:
            case_id = str(uuid.uuid4())
            module_code = str(request["module_code"])
            keyword = str(request["keyword"])
            title = canonical_title(module_code, "99", keyword, "隱密支援")
            case_number = self.create_case(
                case_id=case_id,
                thread_id=channel_id,
                author_id=requester_id,
                module_code=module_code,
                keyword=keyword,
                ai_content_permission=ai_content_permission,
                canonical_title=title,
                initial_snapshot={"title": title, "visibility": "PRIVATE"},
                private_support=True,
            )
            existing_case = self.get_case_by_thread(channel_id)
        else:
            case_number = str(existing_case["case_number"])
            case_id = str(existing_case["case_id"])
        now = utc_now_iso()
        with self.transaction() as db:
            db.execute(
                "UPDATE cases SET jump_url = ?, updated_at = ? WHERE thread_id = ?",
                (jump_url, now, channel_id),
            )
            db.execute(
                """
                INSERT INTO private_support(
                    channel_id, case_number, requester_id, ai_content_permission,
                    status, created_at, case_id, interaction_id, updated_at
                ) VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    case_number=excluded.case_number, case_id=excluded.case_id,
                    interaction_id=excluded.interaction_id, updated_at=excluded.updated_at
                """,
                (
                    channel_id,
                    case_number,
                    requester_id,
                    int(ai_content_permission),
                    now,
                    case_id,
                    interaction_id,
                    now,
                ),
            )
            db.execute(
                """
                UPDATE private_open_requests
                SET status = 'COMPLETED', channel_id = ?, case_id = ?, case_number = ?,
                    jump_url = ?, completed_at = ?, updated_at = ?
                WHERE interaction_id = ? AND status IN (
                    'PENDING', 'CLAIMED', 'RETRYABLE_FAILURE'
                )
                """,
                (channel_id, case_id, case_number, jump_url, now, now, interaction_id),
            )
            self._enqueue_dm(
                db,
                message_key=f"case-open:{case_id}",
                recipient_id=requester_id,
                message_kind="CASE_OPENED",
                aggregate_ref=case_number,
                body=f"您的隱密支援案件已成立。\n案號：`{case_number}`\n前往案件：{jump_url}",
                created_at=now,
            )
            return db.execute(
                "SELECT * FROM private_open_requests WHERE interaction_id = ?",
                (interaction_id,),
            ).fetchone()

    def _enqueue_dm(
        self,
        db: sqlite3.Connection,
        *,
        message_key: str,
        recipient_id: int,
        message_kind: str,
        aggregate_ref: str,
        body: str,
        created_at: str,
    ) -> None:
        db.execute(
            """
            INSERT INTO discord_dm_outbox(
                message_key, recipient_id, message_kind, aggregate_ref, body,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?)
            ON CONFLICT(message_key) DO NOTHING
            """,
            (
                message_key,
                recipient_id,
                message_kind,
                aggregate_ref,
                body,
                created_at,
                created_at,
            ),
        )

    def enqueue_case_dm(
        self, *, case_id: str, recipient_id: int, case_number: str, jump_url: str
    ) -> None:
        now = utc_now_iso()
        with self.transaction() as db:
            db.execute(
                "UPDATE cases SET jump_url = ?, updated_at = ? WHERE case_id = ?",
                (jump_url, now, case_id),
            )
            self._enqueue_dm(
                db,
                message_key=f"case-open:{case_id}",
                recipient_id=recipient_id,
                message_kind="CASE_OPENED",
                aggregate_ref=case_number,
                body=f"您的案件已成立。\n案號：`{case_number}`\n前往案件：{jump_url}",
                created_at=now,
            )

    def enqueue_case_reopen_dm(self, *, case_id: str, cycle_number: int) -> None:
        if cycle_number < 2:
            raise ValueError("Reopen cycle must be at least 2")
        row = self._connection.execute(
            "SELECT author_id, case_number, jump_url FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
        if row is None or int(row["author_id"]) <= 0 or not row["jump_url"]:
            return
        now = utc_now_iso()
        case_number = str(row["case_number"])
        with self.transaction() as db:
            self._enqueue_dm(
                db,
                message_key=f"case-reopen:{case_id}:{cycle_number}",
                recipient_id=int(row["author_id"]),
                message_kind="CASE_REOPENED",
                aggregate_ref=f"{case_number}:cycle:{cycle_number}",
                body=(
                    f"您的案件已重新開啟（第 {cycle_number} 次提問）。\n"
                    f"案號：`{case_number}`\n前往案件：{row['jump_url']}"
                ),
                created_at=now,
            )

    def get_dm_message(self, message_key: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM discord_dm_outbox WHERE message_key = ?", (message_key,)
        ).fetchone()

    def claim_dm_message(self, worker_id: str) -> DmClaim | None:
        with self.immediate_transaction() as db:
            claim = claim_next(db, DM_OUTBOX_QUEUE, worker_id=worker_id, lease_seconds=120)
        if claim is None:
            return None
        return DmClaim(
            message_key=str(claim.key),
            claim_token=claim.claim_token,
            claimed_by=claim.claimed_by,
            attempt_count=claim.attempt_count,
            lease_expires_at=claim.lease_expires_at,
        )

    def complete_dm_message(self, message_key: str, claim_token: str) -> bool:
        now = utc_now_iso()
        with self.transaction() as db:
            return complete_claim(
                db,
                DM_OUTBOX_QUEUE,
                key=message_key,
                claim_token=claim_token,
                final_status="COMPLETED",
                values={"completed_at": now, "updated_at": now},
            )

    def fail_dm_message(
        self,
        message_key: str,
        claim_token: str,
        *,
        error_code: str,
        retryable: bool,
    ) -> bool:
        if not SAFE_JOB_ERROR_CODE.fullmatch(error_code):
            raise ValueError("Unsafe DM error code")
        with self.transaction() as db:
            result = fail_claim(
                db,
                DM_OUTBOX_QUEUE,
                key=message_key,
                claim_token=claim_token,
                error_code=error_code,
                retryable=retryable,
                max_attempts=8,
                base_retry_seconds=30,
                max_retry_seconds=900,
            )
            return result is not None

    def enqueue_verification_email(
        self,
        *,
        challenge_id: str,
        destination: str,
        verification_code: str,
        email_kind: str,
        expires_at: str,
        delivery_id: str | None = None,
    ) -> str:
        if not re.fullmatch(r"email_verification_[a-z0-9]{8,64}", challenge_id):
            raise ValueError("Invalid email verification challenge ID")
        normalized_destination = normalize_email(destination)
        if not re.fullmatch(r"[0-9]{6}", verification_code):
            raise ValueError("Verification code must contain six digits")
        normalized_kind = email_kind.strip().upper()
        if normalized_kind not in {"INSTITUTIONAL", "CONTACT"}:
            raise ValueError("Invalid verification email kind")
        try:
            expiry = datetime.fromisoformat(expires_at)
        except ValueError as error:
            raise ValueError("Invalid verification email expiry") from error
        if expiry.tzinfo is None:
            raise ValueError("Verification email expiry must be timezone-aware")
        identifier = delivery_id or f"email_delivery_{uuid.uuid4().hex}"
        if not re.fullmatch(r"email_delivery_[a-z0-9]{8,64}", identifier):
            raise ValueError("Invalid email delivery ID")
        now = utc_now_iso()
        if expiry.astimezone(UTC) <= datetime.fromisoformat(now).astimezone(UTC):
            raise ValueError("Verification email expiry must be in the future")
        destination_hash = hashlib.sha256(normalized_destination.encode("utf-8")).hexdigest()
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO email_delivery_outbox(
                    delivery_id, challenge_id, destination, destination_hash,
                    verification_code, email_kind, expires_at, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
                ON CONFLICT(delivery_id) DO NOTHING
                """,
                (
                    identifier,
                    challenge_id,
                    normalized_destination,
                    destination_hash,
                    verification_code,
                    normalized_kind,
                    expiry.astimezone(UTC).isoformat(),
                    now,
                    now,
                ),
            )
            row = db.execute(
                "SELECT challenge_id, destination_hash, email_kind, expires_at "
                "FROM email_delivery_outbox WHERE delivery_id = ?",
                (identifier,),
            ).fetchone()
            if row is None or (
                str(row["challenge_id"]) != challenge_id
                or str(row["destination_hash"]) != destination_hash
                or str(row["email_kind"]) != normalized_kind
                or str(row["expires_at"]) != expiry.astimezone(UTC).isoformat()
            ):
                raise ValueError("Email delivery idempotency conflict")
        return identifier

    @staticmethod
    def _email_session_fingerprint(session_subject: str) -> str:
        if not session_subject or len(session_subject) > 256:
            raise ValueError("Invalid verification session")
        return hashlib.sha256(session_subject.encode("utf-8")).hexdigest()

    @staticmethod
    def _email_code_hash(code: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", code.encode("ascii"), bytes.fromhex(salt), 200_000
        ).hex()

    def start_email_verification(
        self,
        *,
        session_subject: str,
        destination: str,
        email_kind: str,
        now: datetime | None = None,
        ttl_seconds: int = 600,
    ) -> str:
        kind = email_kind.strip().upper()
        if kind == "INSTITUTIONAL":
            normalized_destination = normalize_ntu_email(destination)
        elif kind == "CONTACT":
            normalized_destination = normalize_email(destination)
        else:
            raise ValueError("Invalid verification email kind")
        if ttl_seconds < 60 or ttl_seconds > 1_800:
            raise ValueError("Unsafe verification expiry")
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        expires_at = (moment + timedelta(seconds=ttl_seconds)).isoformat()
        challenge_id = f"email_verification_{uuid.uuid4().hex}"
        verification_code = f"{secrets.randbelow(1_000_000):06d}"
        salt = secrets.token_hex(16)
        session_fingerprint = self._email_session_fingerprint(session_subject)
        destination_hash = hashlib.sha256(normalized_destination.encode("utf-8")).hexdigest()
        at = moment.isoformat()
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO email_verification_challenges(
                    challenge_id, session_fingerprint, destination_hash, email_kind,
                    code_salt, code_hash, expires_at, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
                """,
                (
                    challenge_id,
                    session_fingerprint,
                    destination_hash,
                    kind,
                    salt,
                    self._email_code_hash(verification_code, salt),
                    expires_at,
                    at,
                    at,
                ),
            )
        self.enqueue_verification_email(
            challenge_id=challenge_id,
            destination=normalized_destination,
            verification_code=verification_code,
            email_kind=kind,
            expires_at=expires_at,
        )
        return challenge_id

    def verify_email_challenge(
        self,
        *,
        challenge_id: str,
        session_subject: str,
        verification_code: str,
        now: datetime | None = None,
    ) -> bool:
        if not re.fullmatch(r"email_verification_[a-f0-9]{32}", challenge_id):
            return False
        if not re.fullmatch(r"[0-9]{6}", verification_code):
            return False
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        at = moment.isoformat()
        fingerprint = self._email_session_fingerprint(session_subject)
        with self.immediate_transaction() as db:
            row = db.execute(
                "SELECT * FROM email_verification_challenges WHERE challenge_id = ?",
                (challenge_id,),
            ).fetchone()
            if row is None or str(row["session_fingerprint"]) != fingerprint:
                return False
            status = str(row["status"])
            if status == "VERIFIED":
                return True
            if status != "PENDING":
                return False
            if datetime.fromisoformat(str(row["expires_at"])).astimezone(UTC) <= moment:
                db.execute(
                    "UPDATE email_verification_challenges SET status = 'EXPIRED', "
                    "updated_at = ? WHERE challenge_id = ?",
                    (at, challenge_id),
                )
                return False
            attempt_count = int(row["attempt_count"]) + 1
            expected = str(row["code_hash"])
            supplied = self._email_code_hash(verification_code, str(row["code_salt"]))
            if not secrets.compare_digest(expected, supplied):
                status = "LOCKED" if attempt_count >= 5 else "PENDING"
                db.execute(
                    "UPDATE email_verification_challenges SET attempt_count = ?, status = ?, "
                    "updated_at = ? WHERE challenge_id = ?",
                    (attempt_count, status, at, challenge_id),
                )
                return False
            db.execute(
                """UPDATE email_verification_challenges
                   SET attempt_count = ?, status = 'VERIFIED', verified_at = ?, updated_at = ?
                   WHERE challenge_id = ?""",
                (attempt_count, at, at, challenge_id),
            )
            return True

    def email_verification_matches(
        self,
        *,
        challenge_id: str,
        session_subject: str,
        destination: str,
        now: datetime | None = None,
    ) -> bool:
        normalized_destination = normalize_email(destination)
        row = self._connection.execute(
            "SELECT * FROM email_verification_challenges WHERE challenge_id = ?",
            (challenge_id,),
        ).fetchone()
        if row is None or str(row["status"]) not in {"VERIFIED", "CONSUMED"}:
            return False
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        return (
            str(row["session_fingerprint"]) == self._email_session_fingerprint(session_subject)
            and str(row["destination_hash"])
            == hashlib.sha256(normalized_destination.encode("utf-8")).hexdigest()
            and datetime.fromisoformat(str(row["expires_at"])).astimezone(UTC) > moment
        )

    def consume_email_verification(
        self, *, challenge_id: str, session_subject: str, destination: str
    ) -> bool:
        if not self.email_verification_matches(
            challenge_id=challenge_id,
            session_subject=session_subject,
            destination=destination,
        ):
            return False
        now = utc_now_iso()
        with self.transaction() as db:
            result = db.execute(
                """UPDATE email_verification_challenges
                   SET status = 'CONSUMED', consumed_at = COALESCE(consumed_at, ?), updated_at = ?
                   WHERE challenge_id = ? AND status IN ('VERIFIED', 'CONSUMED')""",
                (now, now, challenge_id),
            )
            return result.rowcount == 1

    def claim_verification_email(self, worker_id: str) -> EmailDeliveryClaim | None:
        now = datetime.now(UTC)
        now_iso = now.isoformat()
        with self.immediate_transaction() as db:
            db.execute(
                """
                UPDATE email_delivery_outbox
                SET status = 'PERMANENT_FAILURE', destination = NULL,
                    verification_code = NULL, claim_token = NULL, claimed_by = NULL,
                    lease_expires_at = NULL, next_attempt_at = NULL,
                    last_error_code = 'EMAIL_CODE_EXPIRED', updated_at = ?
                WHERE status IN ('PENDING', 'CLAIMED', 'RETRYABLE_FAILURE')
                  AND expires_at <= ?
                """,
                (now_iso, now_iso),
            )
            claim = claim_next(
                db,
                EMAIL_DELIVERY_QUEUE,
                worker_id=worker_id,
                now=now,
                lease_seconds=120,
            )
            if claim is None:
                return None
            row = db.execute(
                "SELECT challenge_id, destination, verification_code, email_kind, expires_at "
                "FROM email_delivery_outbox WHERE delivery_id = ?",
                (claim.key,),
            ).fetchone()
            if row is None or row["destination"] is None or row["verification_code"] is None:
                raise RuntimeError("Claimed verification email has no delivery payload")
        return EmailDeliveryClaim(
            delivery_id=str(claim.key),
            challenge_id=str(row["challenge_id"]),
            destination=str(row["destination"]),
            verification_code=str(row["verification_code"]),
            email_kind=str(row["email_kind"]),
            expires_at=str(row["expires_at"]),
            claim_token=claim.claim_token,
            attempt_count=claim.attempt_count,
            lease_expires_at=claim.lease_expires_at,
        )

    def complete_verification_email(
        self, delivery_id: str, claim_token: str, provider_receipt: str
    ) -> bool:
        if provider_receipt not in {
            "EMAIL_PROVIDER_ACCEPTED",
            "EMAIL_DELIVERY_ALREADY_ACCEPTED",
        }:
            raise ValueError("Unsafe email provider receipt")
        now = utc_now_iso()
        with self.transaction() as db:
            return complete_claim(
                db,
                EMAIL_DELIVERY_QUEUE,
                key=delivery_id,
                claim_token=claim_token,
                final_status="COMPLETED",
                values={
                    "destination": None,
                    "verification_code": None,
                    "provider_receipt": provider_receipt,
                    "updated_at": now,
                },
            )

    def fail_verification_email(
        self,
        delivery_id: str,
        claim_token: str,
        *,
        error_code: str,
        retryable: bool,
    ) -> bool:
        if not SAFE_JOB_ERROR_CODE.fullmatch(error_code):
            raise ValueError("Unsafe email delivery error code")
        with self.transaction() as db:
            result = fail_claim(
                db,
                EMAIL_DELIVERY_QUEUE,
                key=delivery_id,
                claim_token=claim_token,
                error_code=error_code,
                retryable=retryable,
                max_attempts=8,
                base_retry_seconds=900,
                max_retry_seconds=21_600,
            )
            if result is not None and result.exhausted:
                db.execute(
                    """
                    UPDATE email_delivery_outbox
                    SET destination = NULL, verification_code = NULL, updated_at = ?
                    WHERE delivery_id = ? AND status = 'PERMANENT_FAILURE'
                    """,
                    (utc_now_iso(), delivery_id),
                )
            return result is not None

    def safe_verification_email_status(self, delivery_id: str) -> dict[str, object] | None:
        row = self._connection.execute(
            """
            SELECT delivery_id, challenge_id, email_kind, expires_at, status,
                   attempt_count, next_attempt_at, last_error_code, provider_receipt,
                   created_at, updated_at
            FROM email_delivery_outbox WHERE delivery_id = ?
            """,
            (delivery_id,),
        ).fetchone()
        return None if row is None else dict(row)

    def submit_join_application(
        self,
        *,
        applicant_type: str,
        discord_username: str,
        identity_email: str,
        ntu_mail: str | None = None,
        contact_email: str | None = None,
        class_code: str | None = None,
        visit_reason: str | None = None,
    ) -> tuple[sqlite3.Row, bool]:
        kind = applicant_type.strip().upper()
        if kind not in {"STUDENT", "VISITOR"}:
            raise ValueError("身分類型必須是臺大學生或訪客。")
        username = normalize_discord_username(discord_username)
        if kind == "STUDENT":
            email = normalize_ntu_email(identity_email)
            ntu = normalize_ntu_email(ntu_mail or identity_email)
            klass = normalize_class_code(class_code or "")
            contact = normalize_optional_gmail(contact_email)
            reason = None
        else:
            email = normalize_email(identity_email)
            ntu = None
            klass = None
            contact = normalize_email(contact_email or identity_email)
            reason = (visit_reason or "").strip()
            if not reason:
                raise ValueError("訪客請填寫來訪原因。")
        key = applicant_identity_key(kind, email, username)
        now = utc_now_iso()
        with self.transaction() as db:
            existing = db.execute(
                "SELECT * FROM join_applications WHERE identity_key = ?", (key,)
            ).fetchone()
            if existing is None:
                existing = db.execute(
                    """SELECT * FROM join_applications
                       WHERE applicant_type = ? AND normalized_email = ?
                       ORDER BY created_at LIMIT 1""",
                    (kind, email),
                ).fetchone()
            if existing is not None:
                if existing["discord_user_id"] is not None:
                    summary = str(existing["role_summary"] or "尚未設定班級／權限")
                    self._enqueue_dm(
                        db,
                        message_key=f"join-duplicate:{existing['application_id']}",
                        recipient_id=int(existing["discord_user_id"]),
                        message_kind="JOIN_DUPLICATE",
                        aggregate_ref=str(existing["application_id"]),
                        body=f"你已經註冊過了呦！\n目前班級／權限：{summary}",
                        created_at=now,
                    )
                return existing, True
            application_id = f"join-{uuid.uuid4().hex}"
            db.execute(
                """
                INSERT INTO join_applications(
                    application_id, identity_key, applicant_type, discord_username,
                    normalized_username, identity_email, normalized_email, ntu_mail,
                    contact_email, class_code, visit_reason, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_REVIEW', ?, ?)
                """,
                (
                    application_id,
                    key,
                    kind,
                    discord_username.strip(),
                    username,
                    identity_email.strip(),
                    email,
                    ntu,
                    contact,
                    klass,
                    reason,
                    now,
                    now,
                ),
            )
            self._record_join_event(
                db,
                application_id=application_id,
                previous_status=None,
                new_status="PENDING_REVIEW",
                actor_id=None,
                reason_code="SUBMITTED",
                occurred_at=now,
            )
            row = db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            return row, False

    def bind_join_discord_member(self, application_id: str, discord_user_id: int) -> sqlite3.Row:
        now = utc_now_iso()
        with self.transaction() as db:
            try:
                result = db.execute(
                    """UPDATE join_applications SET discord_user_id = ?, updated_at = ?
                       WHERE application_id = ? AND status != 'ARCHIVED'""",
                    (discord_user_id, now, application_id),
                )
            except sqlite3.IntegrityError as exc:
                raise RuntimeError("DISCORD_MEMBER_ALREADY_BOUND") from exc
            if result.rowcount != 1:
                raise RuntimeError("JOIN_APPLICATION_NOT_FOUND")
            return db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()

    def get_join_application(self, application_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
        ).fetchone()

    def pending_join_applications(self, limit: int = 25) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                """SELECT * FROM join_applications
                   WHERE status IN ('PENDING_REVIEW', 'WAITING_FOR_DISCORD_MEMBER')
                   ORDER BY created_at LIMIT ?""",
                (limit,),
            ).fetchall()
        )

    def transition_join_application(
        self,
        application_id: str,
        *,
        action: str,
        actor_id: int,
        reason_code: str,
        desired_role_ids: tuple[int, ...] = (),
        desired_nickname: str | None = None,
    ) -> sqlite3.Row:
        normalized_action = action.strip().upper()
        now = utc_now_iso()
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            if row is None:
                raise RuntimeError("JOIN_APPLICATION_NOT_FOUND")
            previous = str(row["status"])
            if previous not in {"PENDING_REVIEW", "WAITING_FOR_DISCORD_MEMBER"}:
                raise RuntimeError("JOIN_APPLICATION_NOT_REVIEWABLE")
            if normalized_action == "WAITING":
                target = "WAITING_FOR_DISCORD_MEMBER"
            elif normalized_action == "REJECT":
                target = "REJECTED"
            elif normalized_action == "APPROVE":
                if row["discord_user_id"] is None:
                    target = "WAITING_FOR_DISCORD_MEMBER"
                else:
                    target = previous
                    db.execute(
                        """
                        INSERT INTO course_role_jobs(
                            job_id, application_id, discord_user_id, desired_roles_json,
                            desired_nickname, status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?)
                        ON CONFLICT(application_id) DO UPDATE SET
                            discord_user_id=excluded.discord_user_id,
                            desired_roles_json=excluded.desired_roles_json,
                            desired_nickname=excluded.desired_nickname,
                            status='PENDING', attempt_count=0, next_attempt_at=NULL,
                            claimed_by=NULL, claim_token=NULL, lease_expires_at=NULL,
                            last_error_code=NULL, updated_at=excluded.updated_at,
                            completed_at=NULL
                        WHERE course_role_jobs.status = 'PERMANENT_FAILURE'
                        """,
                        (
                            f"roles-{uuid.uuid4().hex}",
                            application_id,
                            int(row["discord_user_id"]),
                            json.dumps(sorted(set(desired_role_ids))),
                            desired_nickname,
                            now,
                            now,
                        ),
                    )
            else:
                raise ValueError("不支援的審核動作。")
            if target != previous:
                db.execute(
                    """UPDATE join_applications SET status = ?, updated_at = ?
                       WHERE application_id = ?""",
                    (target, now, application_id),
                )
            self._record_join_event(
                db,
                application_id=application_id,
                previous_status=previous,
                new_status=target,
                actor_id=actor_id,
                reason_code=reason_code,
                occurred_at=now,
            )
            if target in {"WAITING_FOR_DISCORD_MEMBER", "REJECTED"} and row["discord_user_id"]:
                copy = (
                    "我們還找不到你的 Discord 成員資料。請先加入伺服器等候區；申請會保留。"
                    if target == "WAITING_FOR_DISCORD_MEMBER"
                    else "你的加入申請目前未通過。若資料需要更正，請聯絡教學團隊。"
                )
                self._enqueue_dm(
                    db,
                    message_key=f"join-{target.lower()}:{application_id}",
                    recipient_id=int(row["discord_user_id"]),
                    message_kind=f"JOIN_{target}",
                    aggregate_ref=application_id,
                    body=copy,
                    created_at=now,
                )
            return db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()

    def reserve_course_alias(self, application_id: str, *, observed_max: int = 0) -> str:
        if observed_max < 0:
            raise ValueError("observed_max cannot be negative")
        now = utc_now_iso()
        with self.immediate_transaction() as db:
            existing = db.execute(
                "SELECT nickname FROM course_alias_allocations WHERE application_id = ?",
                (application_id,),
            ).fetchone()
            if existing is not None:
                return str(existing["nickname"])
            application = db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            if application is None:
                raise RuntimeError("JOIN_APPLICATION_NOT_FOUND")
            if str(application["status"]) not in {
                "PENDING_REVIEW",
                "WAITING_FOR_DISCORD_MEMBER",
            }:
                raise RuntimeError("JOIN_APPLICATION_NOT_REVIEWABLE")
            if str(application["applicant_type"]) == "STUDENT":
                class_code = normalize_class_code(str(application["class_code"] or ""))
                scope_key = f"STUDENT:{class_code}"
                prefix = f"Student_{class_code}"
            else:
                scope_key = "VISITOR:GENERAL"
                prefix = "Guest_Visitor"
            row = db.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS maximum FROM course_alias_allocations "
                "WHERE scope_key = ?",
                (scope_key,),
            ).fetchone()
            sequence = max(int(row["maximum"]), observed_max) + 1
            if sequence > 999:
                raise RuntimeError("COURSE_ALIAS_SEQUENCE_EXHAUSTED")
            nickname = f"{prefix}{sequence:03d}"
            db.execute(
                """INSERT INTO course_alias_allocations(
                       application_id, scope_key, sequence, nickname, created_at
                   ) VALUES (?, ?, ?, ?, ?)""",
                (application_id, scope_key, sequence, nickname, now),
            )
            return nickname

    def complete_course_role_job(self, job_id: str, claim_token: str, role_summary: str) -> bool:
        now = utc_now_iso()
        with self.transaction() as db:
            job = db.execute(
                "SELECT * FROM course_role_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if job is None:
                return False
            application_id = str(job["application_id"])
            row = db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            if row is None or row["discord_user_id"] is None or str(row["status"]) == "ARCHIVED":
                return False
            completed = complete_claim(
                db,
                COURSE_ROLE_QUEUE,
                key=job_id,
                claim_token=claim_token,
                final_status="COMPLETED",
                values={"completed_at": now, "updated_at": now},
            )
            if not completed:
                return False
            previous = str(row["status"])
            db.execute(
                """UPDATE join_applications
                   SET status = 'APPROVED', role_summary = ?, updated_at = ?
                   WHERE application_id = ?""",
                (role_summary, now, application_id),
            )
            self._record_join_event(
                db,
                application_id=application_id,
                previous_status=previous,
                new_status="APPROVED",
                actor_id=None,
                reason_code="ROLES_APPLIED",
                occurred_at=now,
            )
            self._enqueue_dm(
                db,
                message_key=f"join-approved:{application_id}",
                recipient_id=int(row["discord_user_id"]),
                message_kind="JOIN_APPROVED",
                aggregate_ref=application_id,
                body=f"你的加入申請已核准。\n目前班級／權限：{role_summary}",
                created_at=now,
            )
            return True

    def get_course_role_job(self, job_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM course_role_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()

    def claim_course_role_job(self, worker_id: str) -> CourseRoleClaim | None:
        with self.immediate_transaction() as db:
            claim = claim_next(db, COURSE_ROLE_QUEUE, worker_id=worker_id, lease_seconds=300)
        if claim is None:
            return None
        return CourseRoleClaim(
            job_id=str(claim.key),
            claim_token=claim.claim_token,
            claimed_by=claim.claimed_by,
            attempt_count=claim.attempt_count,
            lease_expires_at=claim.lease_expires_at,
        )

    def fail_course_role_job(
        self, job_id: str, claim_token: str, *, error_code: str, retryable: bool
    ) -> bool:
        if not SAFE_JOB_ERROR_CODE.fullmatch(error_code):
            raise ValueError("Unsafe role job error code")
        with self.transaction() as db:
            result = fail_claim(
                db,
                COURSE_ROLE_QUEUE,
                key=job_id,
                claim_token=claim_token,
                error_code=error_code,
                retryable=retryable,
                max_attempts=8,
                base_retry_seconds=15,
                max_retry_seconds=300,
            )
            return result is not None

    def archive_join_application(
        self, application_id: str, *, actor_id: int, reason: str
    ) -> sqlite3.Row:
        now = utc_now_iso()
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            if row is None:
                raise RuntimeError("JOIN_APPLICATION_NOT_FOUND")
            if str(row["status"]) == "ARCHIVED":
                return row
            active_job = db.execute(
                """SELECT 1 FROM course_role_jobs
                   WHERE application_id = ?
                     AND status IN ('PENDING', 'CLAIMED', 'RETRYABLE_FAILURE')""",
                (application_id,),
            ).fetchone()
            if active_job is not None:
                raise RuntimeError("JOIN_APPLICATION_HAS_ACTIVE_ROLE_JOB")
            db.execute(
                """UPDATE join_applications SET previous_status = status, status = 'ARCHIVED',
                   archive_reason = ?, archived_by = ?, archived_at = ?, updated_at = ?
                   WHERE application_id = ?""",
                (reason.strip(), actor_id, now, now, application_id),
            )
            self._record_join_event(
                db,
                application_id=application_id,
                previous_status=str(row["status"]),
                new_status="ARCHIVED",
                actor_id=actor_id,
                reason_code="ARCHIVED",
                occurred_at=now,
            )
            return db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()

    def restore_join_application(self, application_id: str, *, actor_id: int) -> sqlite3.Row:
        now = utc_now_iso()
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            if row is None or str(row["status"]) != "ARCHIVED" or not row["previous_status"]:
                raise RuntimeError("JOIN_APPLICATION_NOT_ARCHIVED")
            target = str(row["previous_status"])
            db.execute(
                """UPDATE join_applications SET status = ?, previous_status = NULL,
                   archive_reason = NULL, archived_by = NULL, archived_at = NULL, updated_at = ?
                   WHERE application_id = ?""",
                (target, now, application_id),
            )
            self._record_join_event(
                db,
                application_id=application_id,
                previous_status="ARCHIVED",
                new_status=target,
                actor_id=actor_id,
                reason_code="RESTORED",
                occurred_at=now,
            )
            return db.execute(
                "SELECT * FROM join_applications WHERE application_id = ?", (application_id,)
            ).fetchone()

    def set_reviewer_grant(
        self, discord_user_id: int, *, level: str, actor_id: int, active: bool
    ) -> None:
        reviewer_level = level.strip().upper()
        if reviewer_level not in {"REVIEWER", "SYSTEM_ADMIN"}:
            raise ValueError("Unsupported reviewer level")
        now = utc_now_iso()
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO reviewer_grants(
                    discord_user_id, reviewer_level, active, granted_by, granted_at,
                    revoked_by, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    reviewer_level=excluded.reviewer_level, active=excluded.active,
                    granted_by=excluded.granted_by, granted_at=excluded.granted_at,
                    revoked_by=excluded.revoked_by, revoked_at=excluded.revoked_at
                """,
                (
                    discord_user_id,
                    reviewer_level,
                    int(active),
                    actor_id,
                    now,
                    None if active else actor_id,
                    None if active else now,
                ),
            )

    def reviewer_level(self, discord_user_id: int) -> str | None:
        row = self._connection.execute(
            """SELECT reviewer_level FROM reviewer_grants
               WHERE discord_user_id = ? AND active = 1""",
            (discord_user_id,),
        ).fetchone()
        return None if row is None else str(row["reviewer_level"])

    def active_system_admin_ids(self) -> tuple[int, ...]:
        rows = self._connection.execute(
            """SELECT discord_user_id FROM reviewer_grants
               WHERE reviewer_level = 'SYSTEM_ADMIN' AND active = 1
               ORDER BY discord_user_id"""
        ).fetchall()
        return tuple(int(row["discord_user_id"]) for row in rows)

    def _record_join_event(
        self,
        db: sqlite3.Connection,
        *,
        application_id: str,
        previous_status: str | None,
        new_status: str,
        actor_id: int | None,
        reason_code: str,
        occurred_at: str,
    ) -> None:
        db.execute(
            """INSERT INTO join_application_events(
                   event_id, application_id, previous_status, new_status,
                   actor_id, reason_code, occurred_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                f"join-evt-{uuid.uuid4().hex}",
                application_id,
                previous_status,
                new_status,
                actor_id,
                reason_code,
                occurred_at,
            ),
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

    def mark_private_deleted(self, channel_id: int) -> bool:
        deleted_at = utc_now_iso()
        with self.transaction() as db:
            dump = db.execute(
                "SELECT status FROM private_dump_jobs WHERE channel_id = ?", (channel_id,)
            ).fetchone()
            if dump is None or str(dump["status"]) not in {"VERIFIED", "DELETED"}:
                return False
            support = db.execute(
                "SELECT case_number FROM private_support WHERE channel_id = ?", (channel_id,)
            ).fetchone()
            if support is None:
                return False
            case_number = str(support["case_number"])
            db.execute(
                """UPDATE private_support SET status = 'DELETED', requester_id = 0,
                   ai_content_permission = 0, updated_at = ? WHERE channel_id = ?""",
                (deleted_at, channel_id),
            )
            db.execute(
                """UPDATE private_dump_jobs
                SET status = 'DELETED', delete_completed_at = ?, updated_at = ?
                WHERE channel_id = ? AND status IN ('VERIFIED', 'DELETED')""",
                (deleted_at, deleted_at, channel_id),
            )
            db.execute(
                """UPDATE cases SET author_id = 0, keyword = '已刪除',
                   ai_content_permission = 0, canonical_title = '[Private][已刪除]',
                   base_title = '[Private][已刪除]', initial_snapshot_json = '{}',
                   jump_url = NULL, updated_at = ? WHERE thread_id = ?""",
                (deleted_at, channel_id),
            )
            db.execute(
                """UPDATE private_open_requests SET requester_id = 0, keyword = '已刪除',
                   jump_url = NULL, updated_at = ? WHERE channel_id = ?""",
                (deleted_at, channel_id),
            )
            db.execute(
                """UPDATE discord_dm_outbox SET recipient_id = 0, body = '', updated_at = ?
                   WHERE aggregate_ref = ? AND status IN ('COMPLETED', 'PERMANENT_FAILURE')""",
                (deleted_at, case_number),
            )
            return True
