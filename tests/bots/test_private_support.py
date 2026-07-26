from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import discord
import pytest

from bots.common.errors import AuthorizationError
from bots.common.idempotency import InMemoryIdempotencyStore
from bots.course_assistant.anonymous_reply import InMemoryInteractionIdentityResolver
from bots.course_assistant.models import ActorContext, CaseStatus
from bots.course_assistant.permissions import StaffPermissionPolicy
from bots.course_assistant.private_support import (
    ClosePrivateSupportCommand,
    CreatePrivateSupportCommand,
    EscalatePrivateSupportCommand,
    EscalationReason,
    InMemoryPrivateSupportAuditSink,
    InMemoryPrivateSupportLifecycleHooks,
    InMemoryPrivateSupportRepository,
    InMemoryRestrictedPrivateSupportProvider,
    PrivateSupportCaseRecord,
    PrivateSupportDataPolicy,
    PrivateSupportResult,
    PrivateSupportService,
    PrivateSupportSource,
    RestrictedRepresentationKind,
)
from bots.course_assistant.private_support_interaction import (
    PrivateSupportDiscordAdapter,
    PrivateSupportModal,
    PrivateSupportView,
)

ROOT = Path(__file__).resolve().parents[2]
OWNER_DISCORD_ID = "723456789012345678"
CASE_ID = "case_private_fixture"
NOW = "2026-07-19T12:00:00+00:00"
TA_USER_ID = "usr_ta_fixture"


def owner() -> ActorContext:
    return ActorContext("usr_amber", ())


def staff() -> ActorContext:
    return ActorContext(TA_USER_ID, ())


def harness(
    kind: RestrictedRepresentationKind = RestrictedRepresentationKind.BACKEND_ONLY,
) -> tuple[
    PrivateSupportService,
    InMemoryPrivateSupportRepository,
    InMemoryRestrictedPrivateSupportProvider,
    InMemoryPrivateSupportAuditSink,
    InMemoryPrivateSupportLifecycleHooks,
]:
    repository = InMemoryPrivateSupportRepository()
    provider = InMemoryRestrictedPrivateSupportProvider(kind)
    audit = InMemoryPrivateSupportAuditSink()
    lifecycle = InMemoryPrivateSupportLifecycleHooks()
    service = PrivateSupportService(
        repository=repository,
        provider=provider,
        audit=audit,
        idempotency=InMemoryIdempotencyStore(),
        staff_policy=StaffPermissionPolicy(frozenset({TA_USER_ID}), frozenset()),
        teaching_team_user_ids=frozenset({TA_USER_ID}),
        retention_days=30,
        retention_hook=lifecycle,
        closure_hook=lifecycle,
        now=lambda: NOW,
    )
    return service, repository, provider, audit, lifecycle


def create_command(
    source: PrivateSupportSource = PrivateSupportSource.PORTAL,
) -> CreatePrivateSupportCommand:
    return CreatePrivateSupportCommand(
        "private-create-0001",
        CASE_ID,
        source,
        "Fictional private support request",
        "This content is fictional and remains inside the restricted fixture provider.",
    )


def test_portal_creation_is_backend_only_private_excluded_and_idempotent() -> None:
    async def scenario() -> tuple[
        PrivateSupportResult,
        PrivateSupportResult,
        PrivateSupportCaseRecord,
        InMemoryRestrictedPrivateSupportProvider,
        InMemoryPrivateSupportAuditSink,
        InMemoryPrivateSupportLifecycleHooks,
    ]:
        service, repository, provider, audit, lifecycle = harness()
        created = await service.create(owner(), create_command())
        replay = await service.create(owner(), create_command())
        record = repository.get(CASE_ID)
        assert record is not None
        return created, replay, record, provider, audit, lifecycle

    created, replay, record, provider, audit, lifecycle = asyncio.run(scenario())
    assert created.representation_kind is RestrictedRepresentationKind.BACKEND_ONLY
    assert replay.duplicate is True
    assert record.source is PrivateSupportSource.PORTAL
    assert record.status is CaseStatus.OPEN
    assert record.analysis_permission == "EXCLUDED"
    assert record.visibility == "TEACHING_STAFF"
    assert record.retention_review_at == "2026-08-18T12:00:00+00:00"
    assert {item.user_id for item in record.participants} == {"usr_amber", TA_USER_ID}
    assert not hasattr(record, "case_number")
    assert len(provider.calls) == 1
    assert len(audit.records) == 1
    assert audit.records[0].actor_user_id == "usr_amber"
    assert not hasattr(audit.records[0], "body")
    assert len(lifecycle.retention_scheduled) == 1
    assert PrivateSupportDataPolicy.public_case_number(record) is None
    assert PrivateSupportDataPolicy.include_in_analysis(record) is False
    assert PrivateSupportDataPolicy.allow_content_export(record) is False


def test_only_explicit_participants_can_read_private_record() -> None:
    async def scenario() -> None:
        service, _, _, _, _ = harness()
        await service.create(owner(), create_command())
        assert service.get_for_participant(owner(), CASE_ID).owner_user_id == "usr_amber"
        assert service.get_for_participant(staff(), CASE_ID).case_id == CASE_ID
        with pytest.raises(AuthorizationError):
            service.get_for_participant(ActorContext("usr_coral", ()), CASE_ID)

    asyncio.run(scenario())


def test_owner_can_escalate_to_allowlisted_teaching_team_member() -> None:
    async def scenario() -> tuple[
        PrivateSupportResult,
        PrivateSupportCaseRecord,
        InMemoryRestrictedPrivateSupportProvider,
        InMemoryPrivateSupportAuditSink,
    ]:
        service, repository, provider, audit, _ = harness()
        await service.create(owner(), create_command())
        result = await service.escalate(
            owner(),
            EscalatePrivateSupportCommand(
                "private-escalate-1",
                CASE_ID,
                TA_USER_ID,
                EscalationReason.WELLBEING,
            ),
        )
        record = repository.get(CASE_ID)
        assert record is not None
        return result, record, provider, audit

    result, record, provider, audit = asyncio.run(scenario())
    assert result.status is CaseStatus.ESCALATED
    assert record.assigned_staff_user_id == TA_USER_ID
    assert [item.operation for item in provider.calls] == ["create", "grant_participant"]
    assert audit.records[-1].reason is EscalationReason.WELLBEING


def test_escalation_rejects_unallowlisted_target_without_provider_write() -> None:
    async def scenario() -> int:
        service, _, provider, _, _ = harness()
        await service.create(owner(), create_command())
        with pytest.raises(AuthorizationError, match="allowlist"):
            await service.escalate(
                owner(),
                EscalatePrivateSupportCommand(
                    "private-escalate-2",
                    CASE_ID,
                    "usr_unapproved_staff",
                    EscalationReason.OTHER,
                ),
            )
        return len(provider.calls)

    assert asyncio.run(scenario()) == 1


def test_owner_close_invokes_restricted_provider_and_closure_hook() -> None:
    async def scenario() -> tuple[
        PrivateSupportResult,
        PrivateSupportCaseRecord,
        InMemoryRestrictedPrivateSupportProvider,
        InMemoryPrivateSupportLifecycleHooks,
    ]:
        service, repository, provider, _, lifecycle = harness()
        await service.create(owner(), create_command())
        result = await service.close(
            owner(), ClosePrivateSupportCommand("private-close-0001", CASE_ID)
        )
        record = repository.get(CASE_ID)
        assert record is not None
        return result, record, provider, lifecycle

    result, record, provider, lifecycle = asyncio.run(scenario())
    assert result.status is CaseStatus.CLOSED
    assert record.closed_at == NOW
    assert provider.calls[-1].operation == "close"
    assert lifecycle.closure_completed == [record]


@dataclass
class FakeInteractionUser:
    id: int


class FakeInteractionResponse:
    def __init__(self) -> None:
        self.modal: discord.ui.Modal | None = None
        self.messages: list[tuple[str, bool]] = []

    async def send_modal(self, modal: discord.ui.Modal) -> None:
        self.modal = modal

    async def send_message(self, content: str, *, ephemeral: bool = False) -> None:
        self.messages.append((content, ephemeral))


class FakeInteraction:
    def __init__(self, interaction_id: int, user_id: int) -> None:
        self.id = interaction_id
        self.user = FakeInteractionUser(user_id)
        self.response = FakeInteractionResponse()


def test_bot_interaction_creates_private_case_with_ephemeral_confirmation() -> None:
    async def scenario() -> tuple[
        FakeInteraction,
        FakeInteraction,
        PrivateSupportCaseRecord,
        InMemoryRestrictedPrivateSupportProvider,
    ]:
        service, repository, provider, _, _ = harness()
        adapter = PrivateSupportDiscordAdapter(
            service,
            InMemoryInteractionIdentityResolver({OWNER_DISCORD_ID: owner()}),
        )
        opening = FakeInteraction(823456789012345678, int(OWNER_DISCORD_ID))
        assert await adapter.open_modal(cast(discord.Interaction, opening)) is True
        assert isinstance(opening.response.modal, PrivateSupportModal)
        modal = opening.response.modal
        modal.title_input._value = "Fixture bot private request"
        modal.body_input._value = "Fictional private content submitted only in the modal."
        submission = FakeInteraction(823456789012345679, int(OWNER_DISCORD_ID))
        await modal.on_submit(cast(discord.Interaction, submission))
        record = repository.get("case_private_823456789012345679")
        assert record is not None
        return opening, submission, record, provider

    opening, submission, record, provider = asyncio.run(scenario())
    assert opening.response.messages == []
    assert submission.response.messages == [
        (
            "Private Support 已建立；它不會出現在公開案件查詢或教學分析。",
            True,
        )
    ]
    assert record.source is PrivateSupportSource.BOT
    assert provider.calls[0].case_id == record.case_id


def test_private_view_is_stable_and_no_public_writer_or_reader_is_imported() -> None:
    async def scenario() -> tuple[int, str | None]:
        service, _, _, _, _ = harness()
        adapter = PrivateSupportDiscordAdapter(
            service,
            InMemoryInteractionIdentityResolver({OWNER_DISCORD_ID: owner()}),
        )
        view = PrivateSupportView(adapter)
        return len(view.children), getattr(view.children[0], "custom_id", None)

    count, custom_id = asyncio.run(scenario())
    assert count == 1
    assert custom_id == "private_support_open"

    import bots.course_assistant.private_support as service_module
    import bots.course_assistant.private_support_interaction as interaction_module

    source = inspect.getsource(service_module) + inspect.getsource(interaction_module)
    assert "DiscordCourseWriter" not in source
    assert "DiscordThreadReader" not in source
    assert "create_case_thread" not in source
    assert "send_message(" in source  # Only generic ephemeral interaction responses.


def test_public_lookup_fixtures_never_contain_private_case_identifiers() -> None:
    responses = json.loads(
        (ROOT / "fixtures" / "adapters" / "case-lookup-responses.json").read_text(encoding="utf-8")
    )
    serialized = json.dumps(responses)
    assert "case_private_001" not in serialized
    assert "PRIVATE_SUPPORT" not in serialized
