from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import cast

import discord
import pytest

from bots.common.config import load_course_assistant_config
from bots.common.errors import AuthorizationError
from bots.common.idempotency import InMemoryIdempotencyStore
from bots.common.models import CaseThreadMapping
from bots.common.testing import FakeDiscordClient, InMemoryCaseThreadMappingRepository
from bots.course_assistant.anonymous_reply import (
    AnonymousReplyDiscordAdapter,
    AnonymousReplyModal,
    AnonymousReplyView,
    InMemoryInteractionIdentityResolver,
    modal_text_input,
)
from bots.course_assistant.hooks import InteractionHookRegistry
from bots.course_assistant.models import (
    ActorContext,
    AnonymousReplyAuditRecord,
    AnonymousReplyCasePolicy,
    AnonymousReplyCommand,
    AnonymousReplyDisplayMode,
    PublishedAnonymousReply,
)
from bots.course_assistant.permissions import MembershipRolePolicy, StaffPermissionPolicy
from bots.course_assistant.repositories import (
    InMemoryAnonymousReplyAuditSink,
    InMemoryAnonymousReplyCaseRepository,
    InMemoryCourseCaseRepository,
    InMemoryJoiningOrderRepository,
)
from bots.course_assistant.service import CourseAssistantService

GUILD_ID = "123456789012345678"
CHANNEL_ID = "223456789012345678"
THREAD_ID = "323456789012345678"
MEMBER_ROLE_ID = "423456789012345678"
CLASS_ROLE_ID = "523456789012345678"
STAFF_ROLE_ID = "623456789012345678"
OWNER_DISCORD_ID = "723456789012345678"
CASE_ID = "case_anonymous_fixture"
NOW = "2026-07-19T11:00:00+00:00"


def harness(
    display_mode: AnonymousReplyDisplayMode = AnonymousReplyDisplayMode.ANONYMOUS,
) -> tuple[CourseAssistantService, FakeDiscordClient, InMemoryAnonymousReplyAuditSink]:
    config = load_course_assistant_config(
        {
            "COURSE_ASSISTANT_GUILD_ID": GUILD_ID,
            "COURSE_ASSISTANT_CHANNEL_IDS": CHANNEL_ID,
            "COURSE_ASSISTANT_ROLE_IDS": f"{MEMBER_ROLE_ID},{CLASS_ROLE_ID}",
        }
    )
    writer = FakeDiscordClient()
    audit = InMemoryAnonymousReplyAuditSink()
    service = CourseAssistantService(
        config=config,
        writer=writer,
        mappings=InMemoryCaseThreadMappingRepository(
            (CaseThreadMapping(CASE_ID, GUILD_ID, CHANNEL_ID, THREAD_ID, NOW),)
        ),
        cases=InMemoryCourseCaseRepository(),
        joining_orders=InMemoryJoiningOrderRepository(),
        idempotency=InMemoryIdempotencyStore(),
        staff_policy=StaffPermissionPolicy(frozenset(), frozenset({STAFF_ROLE_ID})),
        role_policy=MembershipRolePolicy(MEMBER_ROLE_ID, {"01": CLASS_ROLE_ID}),
        hooks=InteractionHookRegistry(),
        case_parent_channel_id=CHANNEL_ID,
        now=lambda: NOW,
        anonymous_reply_cases=InMemoryAnonymousReplyCaseRepository(
            (
                AnonymousReplyCasePolicy(
                    CASE_ID,
                    "usr_amber",
                    display_mode,
                    "01001" if display_mode is AnonymousReplyDisplayMode.COURSE_ALIAS else None,
                ),
            )
        ),
        anonymous_reply_audit=audit,
    )
    return service, writer, audit


def owner() -> ActorContext:
    return ActorContext("usr_amber", ())


def test_fully_anonymous_reply_has_one_bot_write_and_private_actor_audit() -> None:
    async def scenario() -> tuple[
        PublishedAnonymousReply,
        PublishedAnonymousReply,
        FakeDiscordClient,
        AnonymousReplyAuditRecord,
    ]:
        service, writer, audit = harness()
        command = AnonymousReplyCommand(
            "anonymous-operation-001",
            CASE_ID,
            "This fictional reply came only from a private modal.",
        )
        published = await service.post_anonymous_reply(owner(), command)
        replay = await service.post_anonymous_reply(owner(), command)
        return published, replay, writer, audit.records[0]

    published, replay, writer, audit = asyncio.run(scenario())
    assert published.display_mode is AnonymousReplyDisplayMode.ANONYMOUS
    assert replay.duplicate is True
    assert len(writer.write_calls) == 1
    assert writer.write_calls[0].mentions_suppressed is True
    public_body = writer.write_calls[0].body or ""
    assert public_body.startswith("**匿名同學**\n")
    assert "usr_amber" not in public_body
    assert OWNER_DISCORD_ID not in public_body
    assert audit.actor_user_id == "usr_amber"
    assert audit.case_id == CASE_ID
    assert not hasattr(audit, "body")


def test_course_alias_and_fully_anonymous_modes_are_visibly_distinct() -> None:
    async def scenario() -> tuple[str, AnonymousReplyDisplayMode]:
        service, writer, audit = harness(AnonymousReplyDisplayMode.COURSE_ALIAS)
        await service.post_anonymous_reply(
            owner(),
            AnonymousReplyCommand(
                "anonymous-operation-002",
                CASE_ID,
                "A fictional course-alias reply.",
            ),
        )
        return writer.write_calls[0].body or "", audit.records[0].display_mode

    public_body, display_mode = asyncio.run(scenario())
    assert public_body.startswith("**01001**\n")
    assert "匿名同學" not in public_body
    assert display_mode is AnonymousReplyDisplayMode.COURSE_ALIAS


def test_non_owner_cannot_append_to_someone_elses_anonymous_case() -> None:
    async def scenario() -> tuple[int, int]:
        service, writer, audit = harness()
        with pytest.raises(AuthorizationError):
            await service.post_anonymous_reply(
                ActorContext("usr_coral", ()),
                AnonymousReplyCommand(
                    "anonymous-operation-003",
                    CASE_ID,
                    "This fixture must never be posted.",
                ),
            )
        return len(writer.write_calls), len(audit.records)

    writes, audits = asyncio.run(scenario())
    assert writes == 0
    assert audits == 0


@pytest.mark.parametrize("body", ["", "   ", "x" * 1801])
def test_empty_whitespace_and_overlong_modal_content_is_rejected(body: str) -> None:
    async def scenario() -> int:
        service, writer, _ = harness()
        with pytest.raises(ValueError, match="1–1800"):
            await service.post_anonymous_reply(
                owner(), AnonymousReplyCommand("anonymous-operation-004", CASE_ID, body)
            )
        return len(writer.write_calls)

    assert asyncio.run(scenario()) == 0


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


def test_fixture_interaction_opens_modal_and_submit_ack_is_ephemeral() -> None:
    async def scenario() -> tuple[
        FakeInteraction,
        FakeInteraction,
        FakeDiscordClient,
        AnonymousReplyAuditRecord,
    ]:
        service, writer, audit = harness()
        adapter = AnonymousReplyDiscordAdapter(
            service,
            InMemoryInteractionIdentityResolver({OWNER_DISCORD_ID: owner()}),
        )
        opening = FakeInteraction(823456789012345678, int(OWNER_DISCORD_ID))
        opened = await adapter.open_modal(
            cast(discord.Interaction, opening),
            case_id=CASE_ID,
        )
        assert opened is True
        assert isinstance(opening.response.modal, AnonymousReplyModal)
        modal = opening.response.modal
        input_control = modal_text_input(modal)
        assert input_control.required is True
        assert input_control.min_length == 1
        assert input_control.max_length == 1800
        input_control._value = "A fixture reply submitted privately through the modal."

        submission = FakeInteraction(823456789012345679, int(OWNER_DISCORD_ID))
        await modal.on_submit(cast(discord.Interaction, submission))
        return opening, submission, writer, audit.records[0]

    opening, submission, writer, audit = asyncio.run(scenario())
    assert opening.response.messages == []
    assert submission.response.messages == [
        ("已以完全匿名方式代為發布；只有你看得到此確認。", True)
    ]
    assert len(writer.write_calls) == 1
    assert writer.write_calls[0].operation == "send_message"
    assert audit.actor_user_id == "usr_amber"


def test_view_has_bound_button_and_source_never_deletes_normal_messages() -> None:
    async def scenario() -> tuple[int, str | None]:
        service, _, _ = harness()
        adapter = AnonymousReplyDiscordAdapter(
            service,
            InMemoryInteractionIdentityResolver({OWNER_DISCORD_ID: owner()}),
        )
        view = AnonymousReplyView(adapter, CASE_ID)
        custom_ids = [getattr(item, "custom_id", None) for item in view.children]
        return len(view.children), custom_ids[0]

    child_count, custom_id = asyncio.run(scenario())
    assert child_count == 1
    assert custom_id == f"anonymous_reply_open:{CASE_ID}"

    import bots.course_assistant.anonymous_reply as module

    source = inspect.getsource(module)
    assert "delete_message" not in source
    assert "on_message" not in source
