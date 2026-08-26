#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


def candidate_schema_version() -> int:
    repository_source = (
        Path(__file__).resolve().parents[2] / "runtime" / "discord-course-bots" / "src"
    )
    sys.path.insert(0, str(repository_source))
    from discord_course_bots.migrations import MIGRATIONS  # noqa: PLC0415

    return MIGRATIONS[-1].version


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_only_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def integrity(connection: sqlite3.Connection) -> bool:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    return row is not None and str(row[0]) == "ok"


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def snapshot(connection: sqlite3.Connection) -> dict[str, Any]:
    tables = sorted(
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    )
    counts = {
        table: int(
            connection.execute(f"SELECT COUNT(*) FROM {quote_identifier(table)}").fetchone()[0]
        )
        for table in tables
    }
    return {
        "schemaVersion": int(connection.execute("PRAGMA user_version").fetchone()[0]),
        "tables": tables,
        "rowCounts": counts,
    }


def migration_versions(connection: sqlite3.Connection) -> list[int]:
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
        ).fetchall()
    }
    if "schema_migrations" not in tables:
        return []
    return [
        int(row[0])
        for row in connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rehearse consistent SQLite backup, restore and migration on copies."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("work_directory", type=Path)
    parser.add_argument(
        "--expected-source-schema",
        type=int,
        help="Require the supplied source copy to have this schema version (production gate: 6).",
    )
    parser.add_argument(
        "--expected-target-schema",
        type=int,
        default=candidate_schema_version(),
        help="Require the candidate migration to reach this schema version (default: code head).",
    )
    parser.add_argument("--keep", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    work_directory = args.work_directory.resolve()
    if not source.is_file():
        raise SystemExit("source database is missing")
    if not work_directory.is_dir():
        raise SystemExit("work directory is missing")

    run_directory = Path(tempfile.mkdtemp(prefix="sqlite-rehearsal-", dir=work_directory))
    backup = run_directory / "consistent-backup.sqlite3"
    restored = run_directory / "restored.sqlite3"
    migrated = run_directory / "migrated.sqlite3"
    rollback = run_directory / "rollback.sqlite3"
    result: dict[str, Any] = {}
    try:
        source_before = sha256(source)
        with read_only_connection(source) as source_connection:
            source_integrity = integrity(source_connection)
            source_snapshot = snapshot(source_connection)
            source_ledger_versions = migration_versions(source_connection)
            backup_connection = sqlite3.connect(backup)
            try:
                source_connection.backup(backup_connection)
            finally:
                backup_connection.close()
        backup.chmod(stat.S_IRUSR | stat.S_IWUSR)

        with read_only_connection(backup) as backup_connection:
            backup_snapshot = snapshot(backup_connection)
            backup_ledger_versions = migration_versions(backup_connection)
            backup_integrity = integrity(backup_connection)
        shutil.copyfile(backup, restored)
        restored.chmod(stat.S_IRUSR | stat.S_IWUSR)
        with read_only_connection(restored) as restored_connection:
            restored_snapshot = snapshot(restored_connection)
            restored_ledger_versions = migration_versions(restored_connection)
            restored_integrity = integrity(restored_connection)

        shutil.copyfile(backup, rollback)
        rollback.chmod(stat.S_IRUSR | stat.S_IWUSR)
        with read_only_connection(rollback) as rollback_connection:
            rollback_snapshot = snapshot(rollback_connection)
            rollback_ledger_versions = migration_versions(rollback_connection)
            rollback_integrity = integrity(rollback_connection)

        restored_before_migration = sha256(restored)
        shutil.copyfile(restored, migrated)
        migrated.chmod(stat.S_IRUSR | stat.S_IWUSR)
        repository_source = (
            Path(__file__).resolve().parents[2] / "runtime" / "discord-course-bots" / "src"
        )
        sys.path.insert(0, str(repository_source))
        from discord_course_bots.repository import Repository  # noqa: PLC0415

        repository = Repository(migrated)
        migrated_version = repository.schema_version
        migration_entries = len(repository.migration_history())
        repository.close()
        with read_only_connection(migrated) as migrated_connection:
            migrated_snapshot = snapshot(migrated_connection)
            migrated_ledger_versions = migration_versions(migrated_connection)
            migrated_integrity = integrity(migrated_connection)

        original_tables_preserved = all(
            migrated_snapshot["rowCounts"].get(table) == count
            for table, count in source_snapshot["rowCounts"].items()
            if table != "schema_migrations"
        )
        source_after = sha256(source)
        source_mode = stat.S_IMODE(source.stat().st_mode)
        source_owner_matches_process = source.stat().st_uid == os.geteuid()
        workspace_mode = stat.S_IMODE(work_directory.stat().st_mode)
        workspace_owner_matches_process = work_directory.stat().st_uid == os.geteuid()
        restored_mode = stat.S_IMODE(restored.stat().st_mode)
        expected_source_schema = args.expected_source_schema
        source_schema_matches = expected_source_schema is None or (
            source_snapshot["schemaVersion"] == expected_source_schema
        )
        source_mode_gate = expected_source_schema is None or source_mode == 0o600
        source_owner_gate = expected_source_schema is None or source_owner_matches_process
        workspace_mode_gate = expected_source_schema is None or workspace_mode == 0o700
        workspace_owner_gate = expected_source_schema is None or workspace_owner_matches_process
        expected_source_ledger = list(range(1, source_snapshot["schemaVersion"] + 1))
        expected_target_ledger = list(range(1, args.expected_target_schema + 1))
        source_ledger_complete = source_ledger_versions == expected_source_ledger
        backup_ledger_complete = backup_ledger_versions == expected_source_ledger
        restored_ledger_complete = restored_ledger_versions == expected_source_ledger
        migrated_ledger_complete = migrated_ledger_versions == expected_target_ledger
        rollback_ledger_complete = rollback_ledger_versions == expected_source_ledger
        rollback_copy_equivalent = (
            rollback_integrity
            and rollback_snapshot == backup_snapshot
            and sha256(rollback) == sha256(backup)
        )
        pass_result = all(
            (
                source_before == source_after,
                source_integrity,
                source_mode_gate,
                source_owner_gate,
                workspace_mode_gate,
                workspace_owner_gate,
                source_schema_matches,
                source_ledger_complete,
                backup_integrity,
                backup_ledger_complete,
                restored_integrity,
                restored_ledger_complete,
                migrated_integrity,
                migrated_ledger_complete,
                rollback_copy_equivalent,
                rollback_ledger_complete,
                source_snapshot == backup_snapshot,
                backup_snapshot == restored_snapshot,
                original_tables_preserved,
                restored_before_migration == sha256(restored),
                os.access(work_directory, os.W_OK),
                workspace_mode & stat.S_IWUSR != 0,
                restored_mode == 0o600,
                migrated_version == args.expected_target_schema,
                migration_entries == args.expected_target_schema,
            )
        )
        result = {
            "status": "PASS" if pass_result else "FAIL",
            "sourceOpenedReadOnly": True,
            "sourceFileStableDuringRun": source_before == source_after,
            "sourceIntegrity": source_integrity,
            "sourceModeOwnerOnly": source_mode == 0o600,
            "sourceOwnerMatchesProcess": source_owner_matches_process,
            "workspaceWritable": os.access(work_directory, os.W_OK),
            "workspaceOwnerWritable": workspace_mode & stat.S_IWUSR != 0,
            "workspaceModeOwnerOnly": workspace_mode == 0o700,
            "workspaceOwnerMatchesProcess": workspace_owner_matches_process,
            "sourceSchemaMatchesExpected": source_schema_matches,
            "sourceLedgerComplete": source_ledger_complete,
            "backupIntegrity": backup_integrity,
            "backupLedgerComplete": backup_ledger_complete,
            "restoreIntegrity": restored_integrity,
            "restoreLedgerComplete": restored_ledger_complete,
            "migrationIntegrity": migrated_integrity,
            "migrationLedgerComplete": migrated_ledger_complete,
            "rollbackIntegrity": rollback_integrity,
            "rollbackCopyEquivalent": rollback_copy_equivalent,
            "rollbackLedgerComplete": rollback_ledger_complete,
            "backupRestoreEquivalent": backup_snapshot == restored_snapshot,
            "sourceBackupEquivalent": source_snapshot == backup_snapshot,
            "restoredCopyIndependent": restored_before_migration == sha256(restored),
            "originalTableRowCountsPreserved": original_tables_preserved,
            "sourceSchemaVersion": source_snapshot["schemaVersion"],
            "migratedSchemaVersion": migrated_version,
            "expectedSourceSchemaVersion": expected_source_schema,
            "expectedTargetSchemaVersion": args.expected_target_schema,
            "migrationLedgerEntries": migration_entries,
            "sourceTableCount": len(source_snapshot["tables"]),
            "migratedTableCount": len(migrated_snapshot["tables"]),
            "backupSha256": sha256(backup),
            "artifactsRetained": bool(args.keep),
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if pass_result else 1
    finally:
        if not args.keep:
            shutil.rmtree(run_directory, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
