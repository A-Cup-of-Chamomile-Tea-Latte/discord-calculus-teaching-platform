from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class DestinationMap:
    exports: str = "Exports"
    messages: str = "AnalysisMessages"
    summaries: str = "AnalysisSummaries"


@dataclass(frozen=True)
class ImportRow:
    sheet: str
    idempotency_key: str
    values: dict[str, Any]


@dataclass(frozen=True)
class RowOutcome:
    idempotency_key: str
    status: str
    retryable: bool = False
    reason: str | None = None


class BatchDestination(Protocol):
    def write_batch(self, sheet: str, rows: tuple[ImportRow, ...]) -> tuple[RowOutcome, ...]: ...


@dataclass(frozen=True)
class ImportFailure:
    idempotency_key: str
    sheet: str
    reason: str
    attempts: int


@dataclass(frozen=True)
class ImportReport:
    planned: int
    succeeded: int
    skipped: int
    failed: tuple[ImportFailure, ...]
    batches: int
    retries: int
    rows: tuple[ImportRow, ...]
