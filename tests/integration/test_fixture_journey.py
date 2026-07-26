from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from bots.archive_reader.mapping import ArchiveMessageMapper
from bots.archive_reader.models import (
    AnalysisDecision,
    ArchiveCaseRecord,
    ArchiveCaseType,
    AuthorDisplayMode,
    AuthorRole,
    ExportCommand,
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
from bots.common.config import load_archive_reader_config, load_course_assistant_config
from bots.common.contracts import ContractRegistry
from bots.common.errors import ResourceNotFoundError
from bots.common.idempotency import InMemoryIdempotencyStore
from bots.common.models import (
    CaseThreadMapping,
    CreatedThread,
    DiscordAttachmentSnapshot,
    DiscordMessageSnapshot,
    ThreadSnapshot,
)
from bots.common.testing import FakeDiscordClient, InMemoryCaseThreadMappingRepository
from bots.course_assistant.anonymous_reply import (
    AnonymousReplyDiscordAdapter,
    AnonymousReplyModal,
    InMemoryInteractionIdentityResolver,
    modal_text_input,
)
from bots.course_assistant.hooks import InteractionHookRegistry
from bots.course_assistant.models import (
    ActorContext,
    AnonymousReplyCasePolicy,
    AnonymousReplyCommand,
    AnonymousReplyDisplayMode,
    CreateCasePostCommand,
)
from bots.course_assistant.permissions import MembershipRolePolicy, StaffPermissionPolicy
from bots.course_assistant.repositories import (
    InMemoryAnonymousReplyAuditSink,
    InMemoryAnonymousReplyCaseRepository,
    InMemoryCourseCaseRepository,
    InMemoryJoiningOrderRepository,
)
from bots.course_assistant.service import CourseAssistantService
from tools.anonymizer.pipeline import AnonymizerPipeline
from tools.discord_export.adapters import FixtureExportAdapter
from tools.discord_export.pipeline import DiscordExportPipeline
from tools.sheets_importer.adapters import DryRunAdapter
from tools.sheets_importer.importer import BatchImporter

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
NOW = "2026-07-19T19:00:00+08:00"
GUILD_ID = "923456789012345678"
CHANNEL_ID = "323456789012345678"
THREAD_ID = "223456789012345678"
MEMBER_ROLE_ID = "723456789012345678"
CLASS_ROLE_ID = "723456789012345679"


class FixedThreadWriter(FakeDiscordClient):
    async def create_case_thread(
        self,
        *,
        operation_id: str,
        parent_channel_id: str,
        title: str,
        body: str,
    ) -> CreatedThread:
        await super().create_case_thread(
            operation_id=operation_id,
            parent_channel_id=parent_channel_id,
            title=title,
            body=body,
        )
        return CreatedThread(THREAD_ID, "423456789012345678")


def load_array(path: Path) -> list[dict[str, Any]]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, list)
    assert all(isinstance(item, dict) for item in value)
    return value


def course_assistant() -> tuple[
    CourseAssistantService, FixedThreadWriter, InMemoryAnonymousReplyAuditSink
]:
    config = load_course_assistant_config(
        {
            "COURSE_ASSISTANT_GUILD_ID": GUILD_ID,
            "COURSE_ASSISTANT_CHANNEL_IDS": CHANNEL_ID,
            "COURSE_ASSISTANT_ROLE_IDS": f"{MEMBER_ROLE_ID},{CLASS_ROLE_ID}",
        }
    )
    mappings = InMemoryCaseThreadMappingRepository()
    writer = FixedThreadWriter()
    anonymous_audit = InMemoryAnonymousReplyAuditSink()
    service = CourseAssistantService(
        config=config,
        writer=writer,
        mappings=mappings,
        cases=InMemoryCourseCaseRepository(),
        joining_orders=InMemoryJoiningOrderRepository(),
        idempotency=InMemoryIdempotencyStore(),
        staff_policy=StaffPermissionPolicy(frozenset({"usr_staff_example"}), frozenset()),
        role_policy=MembershipRolePolicy(MEMBER_ROLE_ID, {"01": CLASS_ROLE_ID}),
        hooks=InteractionHookRegistry(),
        case_parent_channel_id=CHANNEL_ID,
        now=lambda: NOW,
        anonymous_reply_cases=InMemoryAnonymousReplyCaseRepository(
            (
                AnonymousReplyCasePolicy(
                    "case_000421",
                    "usr_amber",
                    AnonymousReplyDisplayMode.COURSE_ALIAS,
                    "01007",
                ),
            )
        ),
        anonymous_reply_audit=anonymous_audit,
    )
    assert config.network_enabled is False
    return service, writer, anonymous_audit


def archive_reader() -> tuple[ArchiveReaderService, FakeDiscordClient]:
    records = load_array(FIXTURES / "messages/case-000421-thread.json")
    accounts = {
        str(item["userId"]): str(item["discordUserId"])
        for item in load_array(FIXTURES / "users/discord-accounts.json")
    }
    discord_by_internal = {
        str(item["messageId"]): str(item["discordMessageId"]) for item in records
    }
    snapshots: list[DiscordMessageSnapshot] = []
    for item in records:
        attachments = tuple(
            DiscordAttachmentSnapshot(
                str(attachment["attachmentId"]),
                str(attachment["filename"]),
                str(attachment["mediaType"]),
                int(attachment["sizeBytes"]),
                "https://cdn.invalid/not-exported",
            )
            for attachment in item["attachments"]
        )
        parent = item["parentMessageId"]
        snapshots.append(
            DiscordMessageSnapshot(
                str(item["discordMessageId"]),
                THREAD_ID,
                accounts[str(item["authorUserId"])],
                (),
                str(item["body"]),
                str(item["createdAt"]),
                str(item["editedAt"]) if item["editedAt"] else None,
                discord_by_internal[str(parent)] if parent else None,
                attachments,
            )
        )
    client = FakeDiscordClient((ThreadSnapshot(THREAD_ID, tuple(snapshots), None, NOW),))
    config = load_archive_reader_config(
        {
            "ARCHIVE_READER_GUILD_ID": GUILD_ID,
            "ARCHIVE_READER_CHANNEL_IDS": CHANNEL_ID,
        }
    )
    identities = InMemoryMessageIdentityPolicyRepository(
        {
            accounts["usr_amber"]: MessageIdentityPolicy(
                "usr_amber",
                AuthorRole.STUDENT,
                AuthorDisplayMode.COURSE_ALIAS,
                AnalysisDecision.INHERIT,
            ),
            accounts["usr_staff_example"]: MessageIdentityPolicy(
                "usr_staff_example",
                AuthorRole.TA,
                AuthorDisplayMode.REAL_NAME,
                AnalysisDecision.INCLUDED,
            ),
        }
    )
    service = ArchiveReaderService(
        config=config,
        reader=client,
        case_index=InMemoryArchiveCaseIndex(
            (
                ArchiveCaseRecord(
                    "case_000421",
                    "C01-7K4M2Q-0702-1000",
                    ArchiveCaseType.GENERAL,
                    CaseThreadMapping("case_000421", GUILD_ID, CHANNEL_ID, THREAD_ID, NOW),
                ),
            )
        ),
        mapper=ArchiveMessageMapper(identities, ContractRegistry.project_default()),
        checkpoints=InMemoryFollowCheckpointRepository(),
        handoff_sink=InMemoryExportHandoffSink(),
        idempotency=InMemoryIdempotencyStore(),
        manager_policy=ManagerAuthorizationPolicy(frozenset({"usr_staff_example"}), frozenset()),
        now=lambda: NOW,
    )
    assert config.network_enabled is False
    return service, client


def test_complete_fixture_journey_uses_explicit_adapters_and_no_network(tmp_path: Path) -> None:
    contracts = ContractRegistry.project_default()
    cases = load_array(FIXTURES / "cases/cases.json")
    general_case = next(item for item in cases if item["caseId"] == "case_000421")
    first_message = load_array(FIXTURES / "messages/case-000421-thread.json")[0]

    service, writer, audit = course_assistant()
    created = asyncio.run(
        service.create_case_post(
            ActorContext("usr_amber", ()),
            CreateCasePostCommand(
                "integration-create-0001",
                str(general_case["caseId"]),
                str(general_case["title"]),
                str(first_message["body"]),
            ),
        )
    )
    assert created.thread_id == THREAD_ID
    assert [call.operation for call in writer.write_calls] == ["create_case_thread"]

    lookup_records = load_array(FIXTURES / "adapters/case-lookup-responses.json")
    for record in lookup_records:
        contracts.validate("case-lookup-response.schema.json", record)
    found = next(item for item in lookup_records if item["outcome"] == "FOUND")
    assert found["requestedCaseNumber"] == general_case["caseNumber"]
    assert all(
        item["case"]["caseType"] != "PRIVATE_SUPPORT" for item in lookup_records if item["case"]
    )
    private_case_number = next(item for item in cases if item["caseType"] == "PRIVATE_SUPPORT")[
        "caseNumber"
    ]
    assert private_case_number.endswith("-P")

    modal_adapter = AnonymousReplyDiscordAdapter(
        service,
        InMemoryInteractionIdentityResolver({"123456789012345678": ActorContext("usr_amber", ())}),
    )
    modal = AnonymousReplyModal(modal_adapter, "case_000421")
    assert modal.custom_id == "anonymous_reply:case_000421"
    assert modal_text_input(modal).max_length == 1800
    published = asyncio.run(
        service.post_anonymous_reply(
            ActorContext("usr_amber", ()),
            AnonymousReplyCommand(
                "integration-anonymous-0001",
                "case_000421",
                "A fictional follow-up sent through the modal service path.",
            ),
        )
    )
    assert published.display_mode is AnonymousReplyDisplayMode.COURSE_ALIAS
    assert len(audit.records) == 1
    assert audit.records[0].actor_user_id == "usr_amber"
    assert audit.records[0].__dict__.get("body") is None

    reader, read_client = archive_reader()
    assert read_client.read_calls == []
    handoff = asyncio.run(
        reader.dump(
            ManagerContext("usr_staff_example", ()),
            ExportCommand("integration-archive-0001", "C01-7K4M2Q-0702-1000", page_size=2),
        )
    )
    assert len(handoff.messages) == 4
    assert handoff.page_count == 2
    assert len(read_client.read_calls) == 2
    assert read_client.write_calls == []

    fixture_adapter = FixtureExportAdapter(FIXTURES, contracts)
    raw = DiscordExportPipeline(fixture_adapter, contracts, now=lambda: NOW).export(
        "C01-7K4M2Q-0702-1000",
        tmp_path / "raw",
        initiated_by_user_id="usr_staff_example",
        page_size=2,
    )
    assert raw.total_messages == 4
    with pytest.raises(ResourceNotFoundError):
        fixture_adapter.resolve_case("C99-B4W9K6-0702-1500-P")

    sanitized = AnonymizerPipeline(FIXTURES, contracts, now=NOW).sanitize(
        raw.output_directory, tmp_path / "sanitized"
    )
    assert sanitized.included_messages == 3
    assert sanitized.placeholder_messages == 1

    dry_run = DryRunAdapter()
    imported = BatchImporter(dry_run, contracts, batch_size=2).import_package(
        raw.output_directory / "metadata.json",
        sanitized.output_directory / "sanitized-thread.json",
    )
    assert imported.planned == imported.succeeded == 5
    assert imported.failed == ()
    assert {row.sheet for row in dry_run.rows} == {"Exports", "AnalysisMessages"}
    assert not any("token" in key.lower() for row in dry_run.rows for key in row.values)
