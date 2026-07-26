from __future__ import annotations

import asyncio
import inspect

import pytest

from bots.archive_reader.admin_app import ArchiveReaderAdminApp
from bots.archive_reader.mapping import ArchiveMessageMapper
from bots.archive_reader.models import (
    AnalysisDecision,
    ArchiveCaseRecord,
    ArchiveCaseType,
    AuthorDisplayMode,
    AuthorRole,
    ExportCommand,
    ExportHandoff,
    ExportMode,
    FollowCheckpoint,
    ManagerContext,
    MessageIdentityPolicy,
)
from bots.archive_reader.permissions import ManagerAuthorizationPolicy
from bots.archive_reader.repositories import (
    InMemoryArchiveCaseIndex,
    InMemoryExportHandoffSink,
    InMemoryFollowCheckpointRepository,
    InMemoryMessageIdentityPolicyRepository,
)
from bots.archive_reader.service import ArchiveReaderService
from bots.common.config import load_archive_reader_config
from bots.common.contracts import ContractRegistry
from bots.common.errors import AuthorizationError, ProviderUnavailableError, ResourceNotFoundError
from bots.common.idempotency import InMemoryIdempotencyStore
from bots.common.models import (
    CaseThreadMapping,
    DiscordAttachmentSnapshot,
    DiscordMessageSnapshot,
    HealthStatus,
    ThreadSnapshot,
)
from bots.common.testing import FakeDiscordClient, FakeReadCall

GUILD_ID = "123456789012345678"
CHANNEL_ID = "223456789012345678"
THREAD_ID = "323456789012345678"
STUDENT_DISCORD_ID = "423456789012345678"
TA_DISCORD_ID = "523456789012345678"
MANAGER_ROLE_ID = "623456789012345678"
ATTACHMENT_ID = "723456789012345678"
CASE_ID = "case_000421"
CASE_NUMBER = "C01-7K4M2Q-0702-1000"
NOW = "2026-07-19T10:30:00+00:00"


def discord_message_id(number: int) -> str:
    return str(823456789012345670 + number)


def snapshots(count: int = 4) -> tuple[DiscordMessageSnapshot, ...]:
    values: list[DiscordMessageSnapshot] = []
    for number in range(1, count + 1):
        is_student = number % 2 == 1
        attachments = (
            (
                DiscordAttachmentSnapshot(
                    ATTACHMENT_ID,
                    "fictional-limit-sketch.png",
                    "image/png",
                    2048,
                    "https://cdn.invalid/fixture-must-not-be-exported",
                ),
            )
            if number == 3
            else ()
        )
        values.append(
            DiscordMessageSnapshot(
                message_id=discord_message_id(number),
                thread_id=THREAD_ID,
                author_id=STUDENT_DISCORD_ID if is_student else TA_DISCORD_ID,
                author_role_ids=(),
                content=f"Fictional archive message {number}.",
                created_at=f"2026-07-19T10:0{number}:00+00:00",
                edited_at="2026-07-19T10:09:00+00:00" if number == 3 else None,
                parent_message_id=discord_message_id(number - 1) if number > 1 else None,
                attachments=attachments,
            )
        )
    return tuple(values)


def case_record(
    *,
    case_number: str = CASE_NUMBER,
    case_type: ArchiveCaseType = ArchiveCaseType.GENERAL,
    mapping: CaseThreadMapping | None = None,
) -> ArchiveCaseRecord:
    return ArchiveCaseRecord(
        CASE_ID,
        case_number,
        case_type,
        mapping or CaseThreadMapping(CASE_ID, GUILD_ID, CHANNEL_ID, THREAD_ID, NOW),
    )


def identity_repository() -> InMemoryMessageIdentityPolicyRepository:
    return InMemoryMessageIdentityPolicyRepository(
        {
            STUDENT_DISCORD_ID: MessageIdentityPolicy(
                "usr_amber",
                AuthorRole.STUDENT,
                AuthorDisplayMode.COURSE_ALIAS,
                AnalysisDecision.INHERIT,
            ),
            TA_DISCORD_ID: MessageIdentityPolicy(
                "usr_staff_example",
                AuthorRole.TA,
                AuthorDisplayMode.REAL_NAME,
                AnalysisDecision.INCLUDED,
            ),
        }
    )


def harness(
    *,
    messages: tuple[DiscordMessageSnapshot, ...] | None = None,
    checkpoints: InMemoryFollowCheckpointRepository | None = None,
    sink: InMemoryExportHandoffSink | None = None,
    record: ArchiveCaseRecord | None = None,
) -> tuple[
    ArchiveReaderService,
    FakeDiscordClient,
    InMemoryFollowCheckpointRepository,
    InMemoryExportHandoffSink,
]:
    config = load_archive_reader_config(
        {
            "ARCHIVE_READER_GUILD_ID": GUILD_ID,
            "ARCHIVE_READER_CHANNEL_IDS": CHANNEL_ID,
        }
    )
    client = FakeDiscordClient((ThreadSnapshot(THREAD_ID, messages or snapshots(), None, NOW),))
    checkpoint_repository = checkpoints or InMemoryFollowCheckpointRepository()
    handoff_sink = sink or InMemoryExportHandoffSink()
    service = ArchiveReaderService(
        config=config,
        reader=client,
        case_index=InMemoryArchiveCaseIndex((record or case_record(),)),
        mapper=ArchiveMessageMapper(identity_repository(), ContractRegistry.project_default()),
        checkpoints=checkpoint_repository,
        handoff_sink=handoff_sink,
        idempotency=InMemoryIdempotencyStore(),
        manager_policy=ManagerAuthorizationPolicy(frozenset(), frozenset({MANAGER_ROLE_ID})),
        now=lambda: NOW,
    )
    return service, client, checkpoint_repository, handoff_sink


def manager() -> ManagerContext:
    return ManagerContext("usr_archive_manager", (MANAGER_ROLE_ID,))


def test_dump_resolves_one_case_and_reads_multiple_pages_without_writes() -> None:
    async def scenario() -> tuple[ExportHandoff, ExportHandoff, FakeDiscordClient]:
        service, client, _, _ = harness()
        assert service.resolve_thread_id(manager(), f" {CASE_NUMBER.lower()} ") == THREAD_ID
        assert client.read_calls == []
        handoff = await service.dump(
            manager(), ExportCommand("archive-dump-0001", CASE_NUMBER, page_size=2)
        )
        replay = await service.dump(
            manager(), ExportCommand("archive-dump-0001", CASE_NUMBER, page_size=2)
        )
        return handoff, replay, client

    handoff, replay, client = asyncio.run(scenario())
    assert handoff.mode is ExportMode.DUMP
    assert len(handoff.messages) == 4
    assert handoff.page_count == 2
    assert handoff.last_exported_message_id == discord_message_id(4)
    assert replay.duplicate is True
    assert len(client.read_calls) == 2
    assert client.read_calls[1].after_message_id == discord_message_id(2)
    assert client.write_calls == []


def test_attachment_handoff_contains_metadata_but_never_url_or_download_hash() -> None:
    async def scenario() -> dict[str, object]:
        service, _, _, _ = harness()
        handoff = await service.dump(
            manager(), ExportCommand("archive-dump-0002", CASE_NUMBER, page_size=100)
        )
        return handoff.messages[2].to_contract()

    contract = asyncio.run(scenario())
    attachment = contract["attachments"]
    assert isinstance(attachment, list)
    assert attachment == [
        {
            "attachmentId": f"attachment_discord_{ATTACHMENT_ID}",
            "filename": "fictional-limit-sketch.png",
            "mediaType": "image/png",
            "sizeBytes": 2048,
        }
    ]
    assert "cdn.invalid" not in str(contract)


def test_follow_advances_only_after_handoff_and_then_exports_incrementally() -> None:
    async def scenario() -> tuple[
        ExportHandoff,
        FollowCheckpoint | None,
        ExportHandoff,
        ExportHandoff,
        FakeDiscordClient,
        FollowCheckpoint | None,
    ]:
        first_service, _, checkpoints, sink = harness()
        first = await first_service.follow(
            manager(), ExportCommand("archive-follow-001", CASE_NUMBER, page_size=2)
        )
        first_checkpoint = checkpoints.get(CASE_ID)

        second_service, second_client, _, _ = harness(
            messages=snapshots(5), checkpoints=checkpoints, sink=sink
        )
        second = await second_service.follow(
            manager(), ExportCommand("archive-follow-002", CASE_NUMBER, page_size=2)
        )

        third_service, _, _, _ = harness(messages=snapshots(5), checkpoints=checkpoints, sink=sink)
        third = await third_service.follow(
            manager(), ExportCommand("archive-follow-003", CASE_NUMBER, page_size=2)
        )
        return first, first_checkpoint, second, third, second_client, checkpoints.get(CASE_ID)

    first, first_checkpoint, second, third, second_client, final_checkpoint = asyncio.run(
        scenario()
    )
    assert len(first.messages) == 4
    assert first_checkpoint is not None
    assert first_checkpoint.last_exported_message_id == discord_message_id(4)
    assert second.starting_after_message_id == discord_message_id(4)
    assert [item.discord_message_id for item in second.messages] == [discord_message_id(5)]
    assert second_client.read_calls[0].after_message_id == discord_message_id(4)
    assert third.messages == ()
    assert third.last_exported_message_id == discord_message_id(5)
    assert final_checkpoint is not None
    assert final_checkpoint.last_exported_message_id == discord_message_id(5)


def test_unauthorized_or_private_case_fails_before_any_content_read() -> None:
    async def scenario() -> tuple[list[FakeReadCall], list[FakeReadCall]]:
        service, client, _, _ = harness()
        with pytest.raises(AuthorizationError):
            await service.dump(
                ManagerContext("usr_student_fixture", ()),
                ExportCommand("archive-denied-01", CASE_NUMBER),
            )
        private_service, private_client, _, _ = harness(
            record=case_record(
                case_number="C99-B4W9K6-0702-1500-P", case_type=ArchiveCaseType.PRIVATE_SUPPORT
            )
        )
        with pytest.raises(ResourceNotFoundError):
            await private_service.dump(
                manager(), ExportCommand("archive-private-1", "C99-B4W9K6-0702-1500-P")
            )
        return client.read_calls, private_client.read_calls

    denied_reads, private_reads = asyncio.run(scenario())
    assert denied_reads == []
    assert private_reads == []


def test_admin_app_is_fixture_safe_and_has_no_discord_command_tree() -> None:
    async def scenario() -> tuple[HealthStatus, tuple[str, ...], bool, int]:
        service, _, _, _ = harness()
        config = load_archive_reader_config(
            {
                "ARCHIVE_READER_GUILD_ID": GUILD_ID,
                "ARCHIVE_READER_CHANNEL_IDS": CHANNEL_ID,
            }
        )
        app = ArchiveReaderAdminApp(config, service, now=lambda: NOW)
        await app.start()
        handoff = await app.dump(
            manager(), ExportCommand("archive-admin-001", CASE_NUMBER, page_size=3)
        )
        result = (
            app.health().status,
            app.command_names,
            hasattr(app, "bot"),
            len(handoff.messages),
        )
        await app.stop()
        return result

    status, names, has_bot, count = asyncio.run(scenario())
    assert status is HealthStatus.READY
    assert names == ("/dump", "/follow")
    assert has_bot is False
    assert count == 4


def test_reader_source_contains_no_background_scheduler_or_sleep() -> None:
    import bots.archive_reader.admin_app as admin_app_module
    import bots.archive_reader.service as service_module

    source = inspect.getsource(admin_app_module) + inspect.getsource(service_module)
    assert "create_task(" not in source
    assert "asyncio.sleep" not in source
    assert "tasks.loop" not in source


def test_invalid_repeated_page_is_bounded_and_fails_closed() -> None:
    class RepeatingReader:
        async def fetch_thread(
            self,
            *,
            thread_id: str,
            after_message_id: str | None = None,
            limit: int = 100,
        ) -> ThreadSnapshot:
            message = snapshots(1)[0]
            return ThreadSnapshot(thread_id, (message,), message.message_id, NOW)

    async def scenario() -> None:
        service, _, checkpoints, sink = harness()
        service = ArchiveReaderService(
            config=load_archive_reader_config(
                {
                    "ARCHIVE_READER_GUILD_ID": GUILD_ID,
                    "ARCHIVE_READER_CHANNEL_IDS": CHANNEL_ID,
                }
            ),
            reader=RepeatingReader(),
            case_index=InMemoryArchiveCaseIndex((case_record(),)),
            mapper=ArchiveMessageMapper(identity_repository(), ContractRegistry.project_default()),
            checkpoints=checkpoints,
            handoff_sink=sink,
            idempotency=InMemoryIdempotencyStore(),
            manager_policy=ManagerAuthorizationPolicy(
                frozenset({"usr_archive_manager"}), frozenset()
            ),
            now=lambda: NOW,
            max_pages_per_request=3,
        )
        with pytest.raises(ProviderUnavailableError):
            await service.dump(
                manager(), ExportCommand("archive-loop-0001", CASE_NUMBER, page_size=1)
            )

    asyncio.run(scenario())
