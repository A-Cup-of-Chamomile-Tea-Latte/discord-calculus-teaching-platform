"""Typed values shared by export adapters and the local pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class ExportCase:
    record: dict[str, Any]
    thread_id: str

    @property
    def case_id(self) -> str:
        return str(self.record["caseId"])

    @property
    def case_number(self) -> str:
        return str(self.record["caseNumber"])


@dataclass(frozen=True)
class MessagePage:
    messages: tuple[dict[str, Any], ...]
    next_cursor: str | None


class ThreadExportAdapter(Protocol):
    def resolve_case(self, case_number_or_thread_id: str) -> ExportCase: ...

    def fetch_page(
        self,
        case: ExportCase,
        *,
        after_message_id: str | None,
        limit: int,
    ) -> MessagePage: ...

    def user_record(self, user_id: str) -> dict[str, Any]: ...

    def course_alias(self, user_id: str) -> str | None: ...


@dataclass(frozen=True)
class ExportResult:
    output_directory: Path
    total_messages: int
    added_messages: int
    page_count: int
    checkpoint: str | None
    unchanged: bool
