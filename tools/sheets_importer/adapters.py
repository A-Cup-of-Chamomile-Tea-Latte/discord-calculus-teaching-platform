from __future__ import annotations

import csv
import os
import re
from collections.abc import Mapping
from pathlib import Path

from bots.common.errors import NotConfiguredError
from tools.sheets_importer.models import ImportRow, RowOutcome

SAFE_SHEET_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,63}$")


class DryRunAdapter:
    def __init__(self) -> None:
        self.rows: list[ImportRow] = []
        self._seen: set[str] = set()

    def write_batch(self, sheet: str, rows: tuple[ImportRow, ...]) -> tuple[RowOutcome, ...]:
        del sheet
        outcomes: list[RowOutcome] = []
        for row in rows:
            if row.idempotency_key in self._seen:
                outcomes.append(RowOutcome(row.idempotency_key, "SKIPPED"))
            else:
                self._seen.add(row.idempotency_key)
                self.rows.append(row)
                outcomes.append(RowOutcome(row.idempotency_key, "SUCCEEDED"))
        return tuple(outcomes)


class CsvDirectoryAdapter:
    """Local CSV destination with durable importKey-based deduplication."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory.resolve()
        self._directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._directory, 0o700)

    def write_batch(self, sheet: str, rows: tuple[ImportRow, ...]) -> tuple[RowOutcome, ...]:
        if not SAFE_SHEET_PATTERN.fullmatch(sheet):
            raise ValueError("Destination sheet name is unsafe.")
        path = self._directory / f"{sheet}.csv"
        existing = self._existing_keys(path)
        outcomes: list[RowOutcome] = []
        new_rows = [row for row in rows if row.idempotency_key not in existing]
        fieldnames = self._fieldnames(path, new_rows)
        if new_rows:
            with path.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                if path.stat().st_size == 0:
                    writer.writeheader()
                for row in new_rows:
                    writer.writerow({"importKey": row.idempotency_key, **row.values})
            os.chmod(path, 0o600)
        inserted = {row.idempotency_key for row in new_rows}
        for row in rows:
            status = "SUCCEEDED" if row.idempotency_key in inserted else "SKIPPED"
            outcomes.append(RowOutcome(row.idempotency_key, status))
        return tuple(outcomes)

    @staticmethod
    def _existing_keys(path: Path) -> set[str]:
        if not path.exists() or path.stat().st_size == 0:
            return set()
        with path.open(encoding="utf-8", newline="") as handle:
            return {str(row.get("importKey", "")) for row in csv.DictReader(handle)}

    @staticmethod
    def _fieldnames(path: Path, rows: list[ImportRow]) -> list[str]:
        if path.exists() and path.stat().st_size:
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                return next(reader)
        names = sorted({key for row in rows for key in row.values})
        return ["importKey", *names]


class MockAppsScriptEndpointAdapter:
    """In-memory endpoint simulator; failure plans are statuses, never HTTP calls."""

    def __init__(self, failure_plan: Mapping[str, tuple[str, ...]] | None = None) -> None:
        self._failure_plan = dict(failure_plan or {})
        self._attempts: dict[str, int] = {}
        self._seen: set[str] = set()
        self.accepted: list[ImportRow] = []
        self.calls = 0

    def write_batch(self, sheet: str, rows: tuple[ImportRow, ...]) -> tuple[RowOutcome, ...]:
        del sheet
        self.calls += 1
        outcomes: list[RowOutcome] = []
        for row in rows:
            key = row.idempotency_key
            if key in self._seen:
                outcomes.append(RowOutcome(key, "SKIPPED"))
                continue
            attempt = self._attempts.get(key, 0)
            self._attempts[key] = attempt + 1
            plan = self._failure_plan.get(key, ())
            planned = plan[attempt] if attempt < len(plan) else "SUCCEEDED"
            if planned == "RETRY":
                outcomes.append(RowOutcome(key, "FAILED", True, "fixture retryable failure"))
            elif planned == "FAIL":
                outcomes.append(RowOutcome(key, "FAILED", False, "fixture permanent failure"))
            else:
                self._seen.add(key)
                self.accepted.append(row)
                outcomes.append(RowOutcome(key, "SUCCEEDED"))
        return tuple(outcomes)


class FutureGoogleSheetsApiAdapter:
    def __init__(self, configuration: Mapping[str, str] | None = None) -> None:
        del configuration

    def write_batch(self, sheet: str, rows: tuple[ImportRow, ...]) -> tuple[RowOutcome, ...]:
        del sheet, rows
        raise NotConfiguredError(
            "Google Sheets API adapter is not configured; no external request was made."
        )
