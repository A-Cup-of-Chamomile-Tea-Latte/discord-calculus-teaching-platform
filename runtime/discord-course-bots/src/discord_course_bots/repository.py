from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from discord_course_bots.domain.case_numbers import generate_case_number
from discord_course_bots.migrations import apply_migrations
from discord_course_bots.repository_time import utc_now_iso

CASE_NUMBER_MAX_ATTEMPTS = 5


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
        with self.transaction() as db:
            result = db.execute(
                """INSERT INTO private_dump_jobs(channel_id, status, requested_by, requested_at)
                SELECT channel_id, 'PENDING', ?, ? FROM private_support
                WHERE channel_id = ? AND status = 'CLOSED'
                ON CONFLICT(channel_id) DO NOTHING""",
                (requested_by, utc_now_iso(), channel_id),
            )
            return result.rowcount == 1

    def pending_private_dump_jobs(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                """SELECT job.*, support.case_number FROM private_dump_jobs AS job
            JOIN private_support AS support USING(channel_id)
            WHERE job.status = 'PENDING' ORDER BY job.requested_at"""
            ).fetchall()
        )

    def complete_private_dump(self, channel_id: int, manifest_path: str) -> None:
        with self.transaction() as db:
            db.execute(
                """UPDATE private_dump_jobs
                SET status = 'VERIFIED', completed_at = ?, manifest_path = ?
                WHERE channel_id = ? AND status = 'PENDING'""",
                (utc_now_iso(), manifest_path, channel_id),
            )

    def pending_private_deletions(self) -> list[sqlite3.Row]:
        return list(
            self._connection.execute(
                "SELECT * FROM private_dump_jobs WHERE status = 'VERIFIED' ORDER BY completed_at"
            ).fetchall()
        )

    def mark_private_deleted(self, channel_id: int) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE private_support SET status = 'DELETED' WHERE channel_id = ?", (channel_id,)
            )
            db.execute(
                """UPDATE private_dump_jobs SET status = 'DELETED', delete_completed_at = ?
                WHERE channel_id = ? AND status = 'VERIFIED'""",
                (utc_now_iso(), channel_id),
            )
