from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def inspect_database(path: Path) -> dict[str, Any]:
    """Return structural metadata without reading application row contents."""
    resolved = path.expanduser().resolve(strict=True)
    connection = sqlite3.connect(f"{resolved.as_uri()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        table_names = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_schema
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        tables: list[dict[str, Any]] = []
        for table_name in table_names:
            quoted = _quote_identifier(table_name)
            columns = [
                {"name": str(row[1]), "type": str(row[2]), "required": bool(row[3])}
                for row in connection.execute(f"PRAGMA table_info({quoted})")
            ]
            row_count = int(connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])
            tables.append(
                {
                    "name": table_name,
                    "rowCount": row_count,
                    "columns": columns,
                }
            )
        return {
            "database": resolved.name,
            "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
            "userVersion": user_version,
            "tableCount": len(tables),
            "tables": tables,
        }
    finally:
        connection.close()


def _human_summary(report: dict[str, Any]) -> str:
    lines = [
        f"Database: {report['database']}",
        f"SHA-256: {report['sha256']}",
        f"Schema version: {report['userVersion']}",
        f"Tables: {report['tableCount']}",
    ]
    for table in report["tables"]:
        columns = ", ".join(column["name"] for column in table["columns"])
        lines.append(f"- {table['name']}: {table['rowCount']} row(s); columns: {columns}")
    lines.append("No application row values were read or printed.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect SQLite structure and row counts without modifying or printing records",
    )
    parser.add_argument("database", type=Path)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    report = inspect_database(args.database)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else _human_summary(report))


if __name__ == "__main__":
    main()
