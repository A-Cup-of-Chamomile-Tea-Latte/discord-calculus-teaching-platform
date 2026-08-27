from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from discord_course_bots.migrations import MIGRATIONS, _create_ledger, utc_now_iso
from discord_course_bots.repository import Repository

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_schema_v6(path: Path) -> None:
    connection = sqlite3.connect(path)
    _create_ledger(connection)
    for migration in MIGRATIONS[:6]:
        connection.execute("BEGIN IMMEDIATE")
        migration.apply(connection)
        connection.execute(
            "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
            "VALUES (?, ?, ?, ?)",
            (migration.version, migration.name, migration.checksum, utc_now_iso()),
        )
        connection.execute(f"PRAGMA user_version = {migration.version}")
        connection.commit()
    connection.close()
    path.chmod(0o600)


def seed_schema_v6(path: Path) -> None:
    now = "2026-08-27T00:00:00+00:00"
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "case-v6",
            "C01-ABC234-0827-0800",
            101,
            201,
            "M1",
            "limit",
            0,
            "[M1 | C01][limit] fixture",
            "[M1 | C01][limit] fixture",
            "OPEN",
            0,
            now,
            None,
            None,
            '{"fixture":true}',
            0,
        ),
    )
    connection.execute(
        "INSERT INTO drafts(thread_id, forum_channel_id, author_id, original_title, created_at) "
        "VALUES (102, 301, 202, 'fixture draft', ?)",
        (now,),
    )
    connection.execute(
        "INSERT INTO private_support VALUES "
        "(401, 'C99-ABC234-0827-0800-P', 203, 0, 'OPEN', ?, NULL)",
        (now,),
    )
    connection.execute(
        "INSERT INTO private_dump_jobs(channel_id, status, requested_by, requested_at, "
        "attempt_count, updated_at) VALUES (401, 'PENDING', 301, ?, 0, ?)",
        (now, now),
    )
    connection.execute(
        "INSERT INTO runtime_config VALUES ('fixture_key', 'fixture_value', ?)", (now,)
    )
    connection.execute(
        "INSERT INTO case_lifecycle_events VALUES "
        "('event-v6', 'case-v6', 'C01-ABC234-0827-0800', 'OPEN', NULL, 'OPEN', "
        "'DISCORD', 'correlation-v6', ?, 0)",
        (now,),
    )
    connection.execute(
        "INSERT INTO discord_lifecycle_jobs(job_id, case_id, thread_id, transition, "
        "cycle_number, desired_title, status, stage, created_at, updated_at) VALUES "
        "('job-v6', 'case-v6', 101, 'CLOSE', 1, 'fixture', 'PENDING', 'PENDING', ?, ?)",
        (now, now),
    )
    connection.execute(
        "INSERT INTO projection_outbox(projection_id, aggregate_type, aggregate_ref, "
        "event_type, projection_scope, source_version, payload_sha256, status, created_at, "
        "updated_at) VALUES ('projection-v6', 'PUBLIC_CASE', 'C01-ABC234-0827-0800', "
        "'UPSERT_CURRENT_STATE', 'CASEBOARD', 1, ?, 'PENDING', ?, ?)",
        ("a" * 64, now, now),
    )
    connection.execute(
        "INSERT INTO service_health(service_key, service, component, status, mode, checked_at) "
        "VALUES ('course-assistant', 'course-assistant', 'gateway', 'HEALTHY', 'PRODUCTION', ?)",
        (now,),
    )
    connection.execute(
        "INSERT INTO sync_state(stream_name, updated_at) VALUES ('fixture-stream', ?)", (now,)
    )
    connection.execute(
        "INSERT INTO inbound_commands(command_id, idempotency_key, command_type, payload_ref, "
        "source_version, envelope_sha256, source_fingerprint, status, fetched_at, updated_at) "
        "VALUES ('CMD-TST-V6', 'fixture-idempotency', 'CREATE_SYNTHETIC_CASE', "
        "'fixture://public/basic-v1', 1, ?, 'fixture-fingerprint', 'FETCHED', ?, ?)",
        ("b" * 64, now, now),
    )
    connection.commit()
    connection.close()


def test_backup_and_restore_scripts_require_and_preserve_checksum(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE probe(value TEXT NOT NULL)")
    connection.execute("INSERT INTO probe VALUES ('synthetic')")
    connection.commit()
    connection.close()
    backup = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"

    subprocess.run(
        [PROJECT_ROOT / "ops/scripts/sqlite-backup.sh", source, backup],
        check=True,
        capture_output=True,
        text=True,
    )
    expected = file_sha256(backup)
    subprocess.run(
        [
            PROJECT_ROOT / "ops/scripts/sqlite-restore.sh",
            backup,
            restored,
            expected,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert file_sha256(restored) == expected
    restored_connection = sqlite3.connect(restored)
    assert restored_connection.execute("SELECT value FROM probe").fetchone() == ("synthetic",)
    restored_connection.close()


def test_recovery_rehearsal_migrates_only_an_independent_copy(tmp_path: Path) -> None:
    source = tmp_path / "runtime.sqlite3"
    repository = Repository(source)
    repository.set_config("synthetic.rehearsal", "preserved")
    repository.close()
    source_before = file_sha256(source)

    completed = subprocess.run(
        [
            sys.executable,
            PROJECT_ROOT / "ops/scripts/sqlite-recovery-rehearsal.py",
            source,
            tmp_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(completed.stdout)
    assert receipt["status"] == "PASS"
    assert receipt["sourceIntegrity"] is True
    assert receipt["sourceForeignKeysValid"] is True
    assert receipt["sourceOwnerMatchesProcess"] is True
    assert receipt["workspaceModeOwnerOnly"] is True
    assert receipt["workspaceOwnerMatchesProcess"] is True
    assert receipt["sourceOpenedReadOnly"] is True
    assert receipt["backupRestoreEquivalent"] is True
    assert receipt["backupForeignKeysValid"] is True
    assert receipt["restoreForeignKeysValid"] is True
    assert receipt["migrationForeignKeysValid"] is True
    assert receipt["rollbackForeignKeysValid"] is True
    assert receipt["restoredCopyIndependent"] is True
    assert receipt["originalTableRowCountsPreserved"] is True
    assert receipt["artifactsRetained"] is False
    assert file_sha256(source) == source_before


def test_recovery_rehearsal_preserves_v6_application_rows_while_ledger_advances(
    tmp_path: Path,
) -> None:
    source = tmp_path / "production-shaped-v6.sqlite3"
    create_schema_v6(source)
    seed_schema_v6(source)
    source_before = file_sha256(source)

    completed = subprocess.run(
        [
            sys.executable,
            PROJECT_ROOT / "ops/scripts/sqlite-recovery-rehearsal.py",
            "--expected-source-schema",
            "6",
            "--expected-target-schema",
            "13",
            source,
            tmp_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(completed.stdout)
    assert receipt["status"] == "PASS"
    assert receipt["sourceIntegrity"] is True
    assert receipt["sourceForeignKeysValid"] is True
    assert receipt["workspaceModeOwnerOnly"] is True
    assert receipt["sourceLedgerComplete"] is True
    assert receipt["migrationLedgerComplete"] is True
    assert receipt["migrationLedgerEntries"] == 13
    assert receipt["originalTableRowCountsPreserved"] is True
    assert file_sha256(source) == source_before


def test_recovery_rehearsal_accepts_schema_13_noop_maintenance(tmp_path: Path) -> None:
    source = tmp_path / "production-shaped-v13.sqlite3"
    repository = Repository(source)
    repository.set_config("synthetic.maintenance", "preserved")
    repository.close()
    source.chmod(0o600)
    source_before = file_sha256(source)

    completed = subprocess.run(
        [
            sys.executable,
            PROJECT_ROOT / "ops/scripts/sqlite-recovery-rehearsal.py",
            "--expected-source-schema",
            "13",
            "--expected-target-schema",
            "13",
            source,
            tmp_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(completed.stdout)
    assert receipt["status"] == "PASS"
    assert receipt["sourceSchemaVersion"] == 13
    assert receipt["migratedSchemaVersion"] == 13
    assert receipt["expectedSourceSchemaVersion"] == 13
    assert receipt["expectedTargetSchemaVersion"] == 13
    assert receipt["sourceLedgerComplete"] is True
    assert receipt["migrationLedgerComplete"] is True
    assert receipt["migrationLedgerEntries"] == 13
    assert receipt["originalTableRowCountsPreserved"] is True
    assert file_sha256(source) == source_before
