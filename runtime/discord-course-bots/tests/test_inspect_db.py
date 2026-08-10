from __future__ import annotations

import hashlib
import sqlite3

from discord_course_bots.inspect_db import _human_summary, inspect_database


def test_inspector_reports_structure_without_mutating_or_printing_values(tmp_path) -> None:
    path = tmp_path / "lesson.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA user_version = 7")
    connection.execute("CREATE TABLE examples(id INTEGER PRIMARY KEY, private_note TEXT NOT NULL)")
    connection.execute("INSERT INTO examples(private_note) VALUES (?)", ("never-print-this",))
    connection.commit()
    connection.close()

    before = hashlib.sha256(path.read_bytes()).hexdigest()
    report = inspect_database(path)
    after = hashlib.sha256(path.read_bytes()).hexdigest()

    assert after == before
    assert report["userVersion"] == 7
    assert report["tables"] == [
        {
            "name": "examples",
            "rowCount": 1,
            "columns": [
                {"name": "id", "type": "INTEGER", "required": False},
                {"name": "private_note", "type": "TEXT", "required": True},
            ],
        }
    ]
    summary = _human_summary(report)
    assert "never-print-this" not in summary
    assert "No application row values were read or printed." in summary
