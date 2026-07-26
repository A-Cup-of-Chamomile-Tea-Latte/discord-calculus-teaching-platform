"""Explicit, allowlisted archive fetch and local export handoff service."""

from __future__ import annotations

import re
from collections.abc import Callable

from bots.archive_reader.mapping import ArchiveMessageMapper
from bots.archive_reader.models import (
    ArchiveCaseRecord,
    ExportCommand,
    ExportHandoff,
    ExportMode,
    FollowCheckpoint,
    ManagerContext,
)
from bots.archive_reader.permissions import ManagerAuthorizationPolicy
from bots.archive_reader.repositories import (
    ArchiveCaseIndex,
    ExportHandoffSink,
    FollowCheckpointRepository,
)
from bots.common.config import ArchiveReaderConfig
from bots.common.errors import (
    ConflictError,
    ProviderUnavailableError,
    ResourceNotFoundError,
)
from bots.common.health import build_health
from bots.common.idempotency import IdempotencyStore, OperationState
from bots.common.models import DiscordMessageSnapshot, HealthInfo, HealthStatus
from bots.common.ports import DiscordThreadReader
from tools.case_id import validate_case_number

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class ArchiveReaderService:
    def __init__(
        self,
        *,
        config: ArchiveReaderConfig,
        reader: DiscordThreadReader,
        case_index: ArchiveCaseIndex,
        mapper: ArchiveMessageMapper,
        checkpoints: FollowCheckpointRepository,
        handoff_sink: ExportHandoffSink,
        idempotency: IdempotencyStore,
        manager_policy: ManagerAuthorizationPolicy,
        now: Callable[[], str],
        max_pages_per_request: int = 100,
    ) -> None:
        if config.guild_id is None:
            raise ValueError("Archive Reader service requires an explicit fixture/live guild ID")
        if not config.channel_ids:
            raise ValueError("Archive Reader service requires a non-empty channel allowlist")
        if max_pages_per_request < 1:
            raise ValueError("max_pages_per_request must be positive")
        self._config = config
        self._reader = reader
        self._case_index = case_index
        self._mapper = mapper
        self._checkpoints = checkpoints
        self._handoff_sink = handoff_sink
        self._idempotency = idempotency
        self._manager_policy = manager_policy
        self._now = now
        self._max_pages = max_pages_per_request

    def health(self, status: HealthStatus, checked_at: str) -> HealthInfo:
        return build_health(self._config, status=status, checked_at=checked_at)

    def resolve_thread_id(self, actor: ManagerContext, case_number: str) -> str:
        """Resolve one public case after manager authorization, without fetching content."""
        self._manager_policy.require_manager(actor)
        case = self._resolve_case(case_number)
        if case.mapping is None:
            raise ResourceNotFoundError("The public case has no Discord thread mapping.")
        return case.mapping.thread_id

    async def dump(self, actor: ManagerContext, command: ExportCommand) -> ExportHandoff:
        return await self._export(actor, command, ExportMode.DUMP)

    async def follow(self, actor: ManagerContext, command: ExportCommand) -> ExportHandoff:
        """Fetch once after a stored checkpoint; this method never schedules future work."""
        return await self._export(actor, command, ExportMode.FOLLOW)

    async def _export(
        self,
        actor: ManagerContext,
        command: ExportCommand,
        mode: ExportMode,
    ) -> ExportHandoff:
        self._manager_policy.require_manager(actor)
        self._validate_command(command)
        decision = self._idempotency.begin("archive_reader:export", command.request_id)
        if not decision.acquired:
            if decision.record.state is not OperationState.COMPLETED:
                raise ConflictError("The archive export request is already in progress or failed.")
            existing = self._handoff_sink.get(command.request_id)
            if existing is None or decision.record.result_reference != command.request_id:
                raise ConflictError("Completed archive export is missing its local handoff.")
            return existing.as_duplicate()

        try:
            case = self._resolve_case(command.case_number)
            mapping = case.mapping
            if mapping is None:
                raise ResourceNotFoundError("The public case has no Discord thread mapping.")
            checkpoint = self._checkpoints.get(case.case_id) if mode is ExportMode.FOLLOW else None
            starting_after = checkpoint.last_exported_message_id if checkpoint else None
            snapshots, page_count = await self._fetch_pages(
                thread_id=mapping.thread_id,
                after_message_id=starting_after,
                page_size=command.page_size,
            )
            messages = tuple(self._mapper.map(case.case_id, item) for item in snapshots)
            last_exported = snapshots[-1].message_id if snapshots else starting_after
            handoff = ExportHandoff(
                request_id=command.request_id,
                mode=mode,
                case_id=case.case_id,
                case_number=case.case_number or "",
                thread_id=mapping.thread_id,
                messages=messages,
                starting_after_message_id=starting_after,
                last_exported_message_id=last_exported,
                page_count=page_count,
                created_at=self._now(),
            )
            self._handoff_sink.accept(handoff)
            if mode is ExportMode.FOLLOW and snapshots and last_exported is not None:
                self._checkpoints.upsert(FollowCheckpoint(case.case_id, last_exported, self._now()))
            self._idempotency.complete(
                "archive_reader:export", command.request_id, command.request_id
            )
            return handoff
        except Exception:
            self._fail_if_in_progress(command.request_id)
            raise

    def _resolve_case(self, case_number: str) -> ArchiveCaseRecord:
        normalized = case_number.strip().upper()
        if not validate_case_number(normalized):
            raise ValueError("case_number must match the Cxx-token-MMDD-HHMM[-P] format")
        case = self._case_index.get_by_case_number(normalized)
        if case is None or case.case_type.value != "GENERAL" or case.mapping is None:
            raise ResourceNotFoundError("The exportable public case was not found.")
        mapping = case.mapping
        if mapping.case_id != case.case_id:
            raise ConflictError("The case index and Discord mapping disagree.")
        if mapping.guild_id != self._config.guild_id:
            raise ResourceNotFoundError("The case is outside the configured guild.")
        if mapping.parent_channel_id not in self._config.channel_ids:
            raise ResourceNotFoundError("The case is outside the channel allowlist.")
        return case

    async def _fetch_pages(
        self,
        *,
        thread_id: str,
        after_message_id: str | None,
        page_size: int,
    ) -> tuple[tuple[DiscordMessageSnapshot, ...], int]:
        cursor = after_message_id
        observed_cursors: set[str] = set()
        messages: list[DiscordMessageSnapshot] = []
        observed_messages: set[str] = set()
        for page_count in range(1, self._max_pages + 1):
            page = await self._reader.fetch_thread(
                thread_id=thread_id,
                after_message_id=cursor,
                limit=page_size,
            )
            if page.thread_id != thread_id:
                raise ProviderUnavailableError("Discord reader returned the wrong thread.")
            for message in page.messages:
                if message.thread_id != thread_id or message.message_id in observed_messages:
                    raise ProviderUnavailableError(
                        "Discord reader returned an invalid or duplicate message page."
                    )
                observed_messages.add(message.message_id)
                messages.append(message)
            next_cursor = page.next_cursor
            if next_cursor is None:
                return tuple(messages), page_count
            if not page.messages or next_cursor != page.messages[-1].message_id:
                raise ProviderUnavailableError("Discord reader returned an invalid page cursor.")
            if next_cursor == cursor or next_cursor in observed_cursors:
                raise ProviderUnavailableError("Discord reader repeated a page cursor.")
            observed_cursors.add(next_cursor)
            cursor = next_cursor
        raise ProviderUnavailableError("Archive fetch exceeded the bounded page limit.")

    @staticmethod
    def _validate_command(command: ExportCommand) -> None:
        if not REQUEST_ID_PATTERN.fullmatch(command.request_id):
            raise ValueError("request_id must be a safe 8–128 character identifier")
        if not 1 <= command.page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")

    def _fail_if_in_progress(self, request_id: str) -> None:
        decision = self._idempotency.begin("archive_reader:export", request_id)
        if decision.record.state is OperationState.IN_PROGRESS:
            self._idempotency.fail("archive_reader:export", request_id)
