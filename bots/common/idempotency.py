"""Idempotency protocol and deterministic in-memory fixture implementation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from bots.common.errors import ConflictError


class OperationState(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class OperationRecord:
    namespace: str
    operation_id: str
    state: OperationState
    result_reference: str | None


@dataclass(frozen=True)
class BeginOperationResult:
    record: OperationRecord
    acquired: bool


class IdempotencyStore(Protocol):
    def begin(self, namespace: str, operation_id: str) -> BeginOperationResult: ...

    def complete(
        self, namespace: str, operation_id: str, result_reference: str
    ) -> OperationRecord: ...

    def fail(self, namespace: str, operation_id: str) -> OperationRecord: ...


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], OperationRecord] = {}

    def begin(self, namespace: str, operation_id: str) -> BeginOperationResult:
        self._validate(namespace, operation_id)
        key = (namespace, operation_id)
        existing = self._records.get(key)
        if existing:
            return BeginOperationResult(existing, acquired=False)
        record = OperationRecord(namespace, operation_id, OperationState.IN_PROGRESS, None)
        self._records[key] = record
        return BeginOperationResult(record, acquired=True)

    def complete(self, namespace: str, operation_id: str, result_reference: str) -> OperationRecord:
        key = (namespace, operation_id)
        existing = self._records.get(key)
        if existing is None or existing.state is not OperationState.IN_PROGRESS:
            raise ConflictError("Only an in-progress operation may be completed.")
        record = OperationRecord(
            namespace, operation_id, OperationState.COMPLETED, result_reference
        )
        self._records[key] = record
        return record

    def fail(self, namespace: str, operation_id: str) -> OperationRecord:
        key = (namespace, operation_id)
        existing = self._records.get(key)
        if existing is None or existing.state is not OperationState.IN_PROGRESS:
            raise ConflictError("Only an in-progress operation may be failed.")
        record = OperationRecord(namespace, operation_id, OperationState.FAILED, None)
        self._records[key] = record
        return record

    @staticmethod
    def _validate(namespace: str, operation_id: str) -> None:
        if not namespace or not operation_id:
            raise ValueError("namespace and operation_id are required")
