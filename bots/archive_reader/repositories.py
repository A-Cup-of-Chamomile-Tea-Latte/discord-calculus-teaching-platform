"""Repository and local handoff ports with deterministic fixture implementations."""

from __future__ import annotations

from typing import Protocol

from bots.archive_reader.models import (
    ArchiveCaseRecord,
    ExportHandoff,
    FollowCheckpoint,
    MessageIdentityPolicy,
)
from bots.common.errors import ConflictError


class ArchiveCaseIndex(Protocol):
    def get_by_case_number(self, case_number: str) -> ArchiveCaseRecord | None: ...


class MessageIdentityPolicyRepository(Protocol):
    def get_by_discord_user_id(self, discord_user_id: str) -> MessageIdentityPolicy | None: ...


class FollowCheckpointRepository(Protocol):
    def get(self, case_id: str) -> FollowCheckpoint | None: ...

    def upsert(self, checkpoint: FollowCheckpoint) -> None: ...


class ExportHandoffSink(Protocol):
    def accept(self, handoff: ExportHandoff) -> None: ...

    def get(self, request_id: str) -> ExportHandoff | None: ...


class InMemoryArchiveCaseIndex:
    def __init__(self, seed: tuple[ArchiveCaseRecord, ...] = ()) -> None:
        self._records: dict[str, ArchiveCaseRecord] = {}
        for record in seed:
            if record.case_number is None:
                continue
            normalized = record.case_number.strip().upper()
            if normalized in self._records:
                raise ValueError("Case numbers must be unique")
            self._records[normalized] = record

    def get_by_case_number(self, case_number: str) -> ArchiveCaseRecord | None:
        return self._records.get(case_number.strip().upper())


class InMemoryMessageIdentityPolicyRepository:
    def __init__(self, seed: dict[str, MessageIdentityPolicy] | None = None) -> None:
        self._policies = dict(seed or {})

    def get_by_discord_user_id(self, discord_user_id: str) -> MessageIdentityPolicy | None:
        return self._policies.get(discord_user_id)


class InMemoryFollowCheckpointRepository:
    def __init__(self, seed: tuple[FollowCheckpoint, ...] = ()) -> None:
        self._checkpoints = {checkpoint.case_id: checkpoint for checkpoint in seed}

    def get(self, case_id: str) -> FollowCheckpoint | None:
        return self._checkpoints.get(case_id)

    def upsert(self, checkpoint: FollowCheckpoint) -> None:
        self._checkpoints[checkpoint.case_id] = checkpoint


class InMemoryExportHandoffSink:
    """Represents a local exporter queue; it does not write files or call a network."""

    def __init__(self) -> None:
        self._handoffs: dict[str, ExportHandoff] = {}

    @property
    def accepted(self) -> tuple[ExportHandoff, ...]:
        return tuple(self._handoffs.values())

    def accept(self, handoff: ExportHandoff) -> None:
        existing = self._handoffs.get(handoff.request_id)
        if existing is not None and existing != handoff:
            raise ConflictError("The export request ID already identifies another handoff.")
        self._handoffs[handoff.request_id] = handoff

    def get(self, request_id: str) -> ExportHandoff | None:
        return self._handoffs.get(request_id)
