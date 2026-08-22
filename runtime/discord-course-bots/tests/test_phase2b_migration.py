from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from discord_course_bots import migrations
from discord_course_bots.data_lab.carrier import (
    StagingSafetyError,
    ensure_staging_carrier,
    lab_paths,
    open_staging_repository,
)
from discord_course_bots.migrations import MIGRATIONS, Migration, MigrationError, apply_migrations
from discord_course_bots.repository import Repository

EXPECTED_V4_TABLES = {
    "case_lifecycle_events",
    "inbound_commands",
    "projection_outbox",
    "sync_state",
}


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def test_empty_database_reaches_latest_with_fixed_streams(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "empty.sqlite3")
    assert repo.schema_version == MIGRATIONS[-1].version
    assert table_names(repo._connection) >= EXPECTED_V4_TABLES
    streams = repo._connection.execute("SELECT stream_name FROM sync_state ORDER BY stream_name")
    assert [str(row[0]) for row in streams] == [
        "cloud-command-inbox",
        "local-sheet-projection",
        "production-local-sheet-projection",
    ]


def test_v3_to_latest_preserves_existing_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "upgrade.sqlite3"
    connection = sqlite3.connect(path)
    monkeypatch.setattr(migrations, "MIGRATIONS", MIGRATIONS[:3])
    apply_migrations(connection)
    connection.execute(
        "INSERT INTO runtime_config(key, value, updated_at) VALUES ('sentinel', 'yes', 'now')"
    )
    connection.commit()
    connection.close()
    monkeypatch.setattr(migrations, "MIGRATIONS", MIGRATIONS)

    repo = Repository(path)
    assert repo.schema_version == MIGRATIONS[-1].version
    assert repo.get_config("sentinel") == "yes"
    assert table_names(repo._connection) >= EXPECTED_V4_TABLES


def test_repeated_v4_migration_is_noop(tmp_path: Path) -> None:
    path = tmp_path / "repeat.sqlite3"
    first = Repository(path)
    history = [tuple(row) for row in first.migration_history()]
    first.close()
    second = Repository(path)
    assert [tuple(row) for row in second.migration_history()] == history


def test_v4_transaction_failure_rolls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "rollback.sqlite3"
    connection = sqlite3.connect(path)
    monkeypatch.setattr(migrations, "MIGRATIONS", MIGRATIONS[:3])
    apply_migrations(connection)

    def fail_after_write(db: sqlite3.Connection) -> None:
        db.execute("CREATE TABLE must_rollback(value TEXT)")
        raise RuntimeError("synthetic failure")

    failing = Migration(4, "phase2b-failing-fixture", "fixture", fail_after_write)
    monkeypatch.setattr(migrations, "MIGRATIONS", (*MIGRATIONS[:3], failing))
    with pytest.raises(MigrationError, match="Failed to apply migration 4"):
        apply_migrations(connection)
    assert "must_rollback" not in table_names(connection)
    assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == 3


def test_unknown_newer_database_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "newer.sqlite3"
    repo = Repository(path)
    repo.close()
    connection = sqlite3.connect(path)
    connection.execute("INSERT INTO schema_migrations VALUES (99, 'future', 'future', 'now')")
    connection.commit()
    connection.close()
    with pytest.raises(MigrationError, match="newer than this runtime"):
        Repository(path)


def test_staging_carrier_sets_fail_closed_runtime_markers(tmp_path: Path) -> None:
    paths = ensure_staging_carrier(tmp_path / "phase2b-data-lab")
    repo = open_staging_repository(paths)
    assert repo.config_snapshot() == {
        "environment": "STAGING",
        "live_discord_enabled": "0",
        "synthetic_only": "1",
    }


def test_live_or_wrong_database_paths_are_refused(tmp_path: Path) -> None:
    with pytest.raises(StagingSafetyError, match="STAGING_DIRECTORY_NAME_REQUIRED"):
        ensure_staging_carrier(tmp_path / "discord-course-bots-runtime")
    with pytest.raises(StagingSafetyError, match="STAGING_DIRECTORY_NAME_REQUIRED"):
        ensure_staging_carrier(tmp_path / "live" / "phase2b-lab")
    paths = lab_paths(tmp_path / "phase2b-data-lab")
    paths.root.mkdir()
    paths.config.write_text('{"environment":"PRODUCTION"}', encoding="utf-8")
    with pytest.raises(StagingSafetyError, match="STAGING_ENVIRONMENT_REQUIRED"):
        ensure_staging_carrier(paths.root, create=False)
