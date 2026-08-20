from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from discord_course_bots.repository import Repository

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    assert receipt["sourceOpenedReadOnly"] is True
    assert receipt["backupRestoreEquivalent"] is True
    assert receipt["restoredCopyIndependent"] is True
    assert receipt["originalTableRowCountsPreserved"] is True
    assert receipt["artifactsRetained"] is False
    assert file_sha256(source) == source_before
