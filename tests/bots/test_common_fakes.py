from __future__ import annotations

import asyncio

import pytest

from bots.common.errors import ConflictError
from bots.common.idempotency import InMemoryIdempotencyStore, OperationState
from bots.common.models import (
    CaseThreadMapping,
    DiscordMessageSnapshot,
    ThreadSnapshot,
)
from bots.common.testing import FakeDiscordClient, InMemoryCaseThreadMappingRepository

GUILD_ID = "123456789012345678"
CHANNEL_ID = "223456789012345678"
THREAD_ID = "323456789012345678"


def message(identifier: int) -> DiscordMessageSnapshot:
    return DiscordMessageSnapshot(
        message_id=f"{identifier:018d}",
        thread_id=THREAD_ID,
        author_id="423456789012345678",
        author_role_ids=(),
        content=f"fixture message {identifier}",
        created_at=f"2026-07-19T10:0{identifier}:00+00:00",
        edited_at=None,
        parent_message_id=None,
        attachments=(),
    )


def test_mapping_repository_enforces_one_case_per_thread() -> None:
    first = CaseThreadMapping(
        "case_fixture",
        GUILD_ID,
        CHANNEL_ID,
        THREAD_ID,
        "2026-07-19T10:00:00+00:00",
    )
    repository = InMemoryCaseThreadMappingRepository((first,))
    assert repository.get_by_case_id("case_fixture") == first
    assert repository.get_by_thread_id(THREAD_ID) == first
    with pytest.raises(ValueError, match="only one case"):
        repository.upsert(
            CaseThreadMapping(
                "case_other",
                GUILD_ID,
                CHANNEL_ID,
                THREAD_ID,
                "2026-07-19T10:01:00+00:00",
            )
        )


def test_fake_discord_client_supports_read_paging_and_records_writes() -> None:
    async def scenario() -> tuple[int, str | None, tuple[str, ...]]:
        client = FakeDiscordClient(
            (
                ThreadSnapshot(
                    THREAD_ID,
                    (message(1), message(2), message(3)),
                    None,
                    "2026-07-19T10:10:00+00:00",
                ),
            )
        )
        first = await client.fetch_thread(thread_id=THREAD_ID, limit=2)
        second = await client.fetch_thread(
            thread_id=THREAD_ID,
            after_message_id=first.next_cursor,
            limit=2,
        )
        created = await client.create_case_thread(
            operation_id="operation-create",
            parent_channel_id=CHANNEL_ID,
            title="Fixture title",
            body="Fixture body",
        )
        await client.send_message(
            operation_id="operation-reply",
            thread_id=created.thread_id,
            body="Fixture reply",
        )
        return (
            len(first.messages) + len(second.messages),
            first.next_cursor,
            tuple(call.operation for call in client.write_calls),
        )

    count, cursor, operations = asyncio.run(scenario())
    assert count == 3
    assert cursor == "000000000000000002"
    assert operations == ("create_case_thread", "send_message")


def test_fixture_idempotency_namespaces_bot_operations() -> None:
    store = InMemoryIdempotencyStore()
    started = store.begin("course_assistant", "operation-1")
    assert started.acquired is True
    assert started.record.state is OperationState.IN_PROGRESS
    replay = store.begin("course_assistant", "operation-1")
    assert replay.acquired is False and replay.record == started.record
    completed = store.complete("course_assistant", "operation-1", "message-fixture")
    assert completed.state is OperationState.COMPLETED
    assert store.begin("course_assistant", "operation-1").record == completed
    assert store.begin("archive_reader", "operation-1").record.state is OperationState.IN_PROGRESS
    with pytest.raises(ConflictError):
        store.complete("course_assistant", "operation-1", "second-result")
