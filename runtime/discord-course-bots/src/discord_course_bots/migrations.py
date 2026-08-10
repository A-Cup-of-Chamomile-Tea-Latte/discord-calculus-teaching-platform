from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from discord_course_bots.repository_time import utc_now_iso


class MigrationError(RuntimeError):
    """The database schema cannot be safely brought to the expected version."""


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    fingerprint: str
    apply: Callable[[sqlite3.Connection], None]

    @property
    def checksum(self) -> str:
        source = f"{self.version}\n{self.name}\n{self.fingerprint}"
        return hashlib.sha256(source.encode()).hexdigest()


BASELINE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS runtime_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS drafts (
        thread_id INTEGER PRIMARY KEY,
        forum_channel_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        original_title TEXT NOT NULL,
        starter_message_id INTEGER,
        setup_message_id INTEGER,
        created_at TEXT NOT NULL,
        reminded_at TEXT,
        deleted_at TEXT,
        delete_reason TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cases (
        case_id TEXT PRIMARY KEY,
        case_number TEXT NOT NULL UNIQUE,
        thread_id INTEGER NOT NULL UNIQUE,
        author_id INTEGER NOT NULL,
        module_code TEXT NOT NULL,
        keyword TEXT NOT NULL,
        ai_content_permission INTEGER NOT NULL CHECK(ai_content_permission IN (0, 1)),
        canonical_title TEXT NOT NULL,
        base_title TEXT NOT NULL,
        status TEXT NOT NULL,
        reopen_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        closed_at TEXT,
        last_staff_response_at TEXT,
        initial_snapshot_json TEXT NOT NULL,
        dump_version INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS private_support (
        channel_id INTEGER PRIMARY KEY,
        case_number TEXT UNIQUE,
        requester_id INTEGER NOT NULL,
        ai_content_permission INTEGER NOT NULL CHECK(ai_content_permission IN (0, 1)),
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        closed_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS private_dump_jobs (
        channel_id INTEGER PRIMARY KEY,
        status TEXT NOT NULL,
        requested_by INTEGER NOT NULL,
        requested_at TEXT NOT NULL,
        completed_at TEXT,
        manifest_path TEXT,
        delete_completed_at TEXT,
        error TEXT
    )
    """,
)


def _apply_baseline(connection: sqlite3.Connection) -> None:
    for statement in BASELINE_STATEMENTS:
        connection.execute(statement)


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _apply_legacy_compatibility(connection: sqlite3.Connection) -> None:
    if "base_title" not in _column_names(connection, "cases"):
        connection.execute("ALTER TABLE cases ADD COLUMN base_title TEXT NOT NULL DEFAULT ''")
        rows = connection.execute(
            "SELECT case_id, canonical_title, initial_snapshot_json FROM cases"
        ).fetchall()
        for row in rows:
            base_title = str(row[1])
            try:
                snapshot = json.loads(str(row[2]))
                snapshot_title = snapshot.get("title")
                if isinstance(snapshot_title, str) and snapshot_title.strip():
                    base_title = snapshot_title
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
            connection.execute(
                "UPDATE cases SET base_title = ? WHERE case_id = ?",
                (base_title, str(row[0])),
            )

    if "case_number" not in _column_names(connection, "private_support"):
        connection.execute("ALTER TABLE private_support ADD COLUMN case_number TEXT")
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS private_support_case_number_unique
        ON private_support(case_number)
        """
    )


def _apply_private_dump_job_leases(connection: sqlite3.Connection) -> None:
    columns = _column_names(connection, "private_dump_jobs")
    additions = (
        ("claim_token", "TEXT"),
        ("claimed_by", "TEXT"),
        ("lease_expires_at", "TEXT"),
        ("attempt_count", "INTEGER NOT NULL DEFAULT 0"),
        ("retry_at", "TEXT"),
        ("failure_kind", "TEXT"),
        ("updated_at", "TEXT"),
    )
    for name, declaration in additions:
        if name not in columns:
            connection.execute(f"ALTER TABLE private_dump_jobs ADD COLUMN {name} {declaration}")
    connection.execute(
        """
        UPDATE private_dump_jobs
        SET updated_at = COALESCE(updated_at, completed_at, requested_at),
            attempt_count = CASE
                WHEN status IN ('VERIFIED', 'DELETED') AND attempt_count = 0 THEN 1
                ELSE attempt_count
            END
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS private_dump_jobs_claimable
        ON private_dump_jobs(status, retry_at, lease_expires_at, requested_at)
        """
    )


MIGRATIONS = (
    Migration(
        1,
        "baseline-five-runtime-tables",
        "\n".join(statement.strip() for statement in BASELINE_STATEMENTS),
        _apply_baseline,
    ),
    Migration(
        2,
        "legacy-base-title-and-private-case-number",
        "cases.base_title from initial snapshot; private_support.case_number; unique index; v1",
        _apply_legacy_compatibility,
    ),
    Migration(
        3,
        "private-dump-job-claim-lease-retry",
        (
            "private_dump_jobs claim_token claimed_by lease_expires_at attempt_count retry_at "
            "failure_kind updated_at; claimable index; legacy backfill; v1"
        ),
        _apply_private_dump_job_leases,
    ),
)


def _create_ledger(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def _verify_recorded_migrations(connection: sqlite3.Connection) -> set[int]:
    known = {migration.version: migration for migration in MIGRATIONS}
    rows = connection.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    applied: set[int] = set()
    for row in rows:
        version = int(row[0])
        migration = known.get(version)
        if migration is None:
            raise MigrationError(
                f"Database migration {version} is newer than this runtime; refusing downgrade"
            )
        if str(row[1]) != migration.name or str(row[2]) != migration.checksum:
            raise MigrationError(f"Database migration {version} checksum or name does not match")
        applied.add(version)
    return applied


def apply_migrations(connection: sqlite3.Connection) -> None:
    _create_ledger(connection)
    applied = _verify_recorded_migrations(connection)
    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        try:
            connection.execute("BEGIN IMMEDIATE")
            migration.apply(connection)
            connection.execute(
                """
                INSERT INTO schema_migrations(version, name, checksum, applied_at)
                VALUES (?, ?, ?, ?)
                """,
                (migration.version, migration.name, migration.checksum, utc_now_iso()),
            )
            connection.execute(f"PRAGMA user_version = {migration.version}")
            connection.commit()
        except Exception as error:
            connection.rollback()
            if isinstance(error, MigrationError):
                raise
            raise MigrationError(
                f"Failed to apply migration {migration.version} ({migration.name})"
            ) from error

    expected_version = MIGRATIONS[-1].version
    actual_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if actual_version != expected_version:
        connection.execute(f"PRAGMA user_version = {expected_version}")
        connection.commit()
