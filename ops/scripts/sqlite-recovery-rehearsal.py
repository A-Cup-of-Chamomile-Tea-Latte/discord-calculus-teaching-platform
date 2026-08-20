#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rehearse consistent SQLite backup, restore and migration on copies."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("work_directory", type=Path)
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
    result: dict[str, Any] = {}
    try:
        source_before = sha256(source)
        with read_only_connection(source) as source_connection:
            source_snapshot = snapshot(source_connection)
            backup_connection = sqlite3.connect(backup)
            try:
                source_connection.backup(backup_connection)
            finally:
                backup_connection.close()
        backup.chmod(stat.S_IRUSR | stat.S_IWUSR)

        with read_only_connection(backup) as backup_connection:
            backup_snapshot = snapshot(backup_connection)
            backup_integrity = integrity(backup_connection)
        shutil.copyfile(backup, restored)
        restored.chmod(stat.S_IRUSR | stat.S_IWUSR)
        with read_only_connection(restored) as restored_connection:
            restored_snapshot = snapshot(restored_connection)
            restored_integrity = integrity(restored_connection)

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
            migrated_integrity = integrity(migrated_connection)

        original_tables_preserved = all(
            migrated_snapshot["rowCounts"].get(table) == count
            for table, count in source_snapshot["rowCounts"].items()
        )
        source_after = sha256(source)
        source_mode = stat.S_IMODE(source.stat().st_mode)
        restored_mode = stat.S_IMODE(restored.stat().st_mode)
        pass_result = all(
            (
                backup_integrity,
                restored_integrity,
                migrated_integrity,
                source_snapshot == backup_snapshot,
                backup_snapshot == restored_snapshot,
                original_tables_preserved,
                restored_before_migration == sha256(restored),
                restored_mode == 0o600,
                migration_entries > 0,
            )
        )
        result = {
            "status": "PASS" if pass_result else "FAIL",
            "sourceOpenedReadOnly": True,
            "sourceFileStableDuringRun": source_before == source_after,
            "sourceModeOwnerOnly": source_mode == 0o600,
            "backupIntegrity": backup_integrity,
            "restoreIntegrity": restored_integrity,
            "migrationIntegrity": migrated_integrity,
            "backupRestoreEquivalent": backup_snapshot == restored_snapshot,
            "sourceBackupEquivalent": source_snapshot == backup_snapshot,
            "restoredCopyIndependent": restored_before_migration == sha256(restored),
            "originalTableRowCountsPreserved": original_tables_preserved,
            "sourceSchemaVersion": source_snapshot["schemaVersion"],
            "migratedSchemaVersion": migrated_version,
            "migrationLedgerEntries": migration_entries,
            "sourceTableCount": len(source_snapshot["tables"]),
            "migratedTableCount": len(migrated_snapshot["tables"]),
            "checksumPrefix": sha256(backup)[:12],
            "artifactsRetained": bool(args.keep),
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if pass_result else 1
    finally:
        if not args.keep:
            shutil.rmtree(run_directory, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
