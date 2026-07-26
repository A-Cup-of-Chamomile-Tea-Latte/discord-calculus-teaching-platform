from __future__ import annotations

import asyncio

import pytest

from bots.common.config import load_course_assistant_config
from bots.common.errors import (
    AuthorizationError,
    ConflictError,
    NotConfiguredError,
)
from bots.common.idempotency import InMemoryIdempotencyStore
from bots.common.models import HealthStatus
from bots.common.testing import (
    FakeDiscordClient,
    InMemoryCaseThreadMappingRepository,
)
from bots.course_assistant.discord_app import CourseAssistantDiscordApp
from bots.course_assistant.hooks import InteractionHookRegistry
from bots.course_assistant.models import (
    ActorContext,
    ApplyMembershipCommand,
    CaseStatus,
    CreateCasePostCommand,
    HookResult,
    PrivateSupportRequest,
    UpdateCaseStatusCommand,
)
from bots.course_assistant.permissions import (
    MembershipRolePolicy,
    StaffPermissionPolicy,
)
from bots.course_assistant.repositories import (
    InMemoryCourseCaseRepository,
    InMemoryJoiningOrderRepository,
    generate_course_alias,
)
from bots.course_assistant.service import CourseAssistantService

GUILD_ID = "123456789012345678"
CHANNEL_ID = "223456789012345678"
MEMBER_ROLE_ID = "323456789012345678"
CLASS_ROLE_ID = "423456789012345678"
STAFF_ROLE_ID = "523456789012345678"


def harness() -> tuple[
    CourseAssistantService,
    FakeDiscordClient,
    InteractionHookRegistry,
]:
    config = load_course_assistant_config(
        {
            "COURSE_ASSISTANT_GUILD_ID": GUILD_ID,
            "COURSE_ASSISTANT_CHANNEL_IDS": CHANNEL_ID,
            "COURSE_ASSISTANT_ROLE_IDS": f"{MEMBER_ROLE_ID},{CLASS_ROLE_ID}",
        }
    )
    writer = FakeDiscordClient()
    hooks = InteractionHookRegistry()
    service = CourseAssistantService(
        config=config,
        writer=writer,
        mappings=InMemoryCaseThreadMappingRepository(),
        cases=InMemoryCourseCaseRepository(),
        joining_orders=InMemoryJoiningOrderRepository(),
        idempotency=InMemoryIdempotencyStore(),
        staff_policy=StaffPermissionPolicy(
            staff_user_ids=frozenset({"usr_staff_example"}),
            staff_role_ids=frozenset({STAFF_ROLE_ID}),
        ),
        role_policy=MembershipRolePolicy(
            broad_membership_role_id=MEMBER_ROLE_ID,
            class_role_ids={"01": CLASS_ROLE_ID},
        ),
        hooks=hooks,
        case_parent_channel_id=CHANNEL_ID,
        now=lambda: "2026-07-19T10:00:00+00:00",
    )
    return service, writer, hooks


def test_course_alias_requires_two_class_digits_and_three_order_digits() -> None:
    assert generate_course_alias("01", 1) == "01001"
    assert generate_course_alias("99", 999) == "99999"
    for class_code, order in (("1", 1), ("A1", 1), ("001", 1), ("01", 0), ("01", 1000)):
        with pytest.raises(ValueError):
            generate_course_alias(class_code, order)


def test_joining_order_allocation_is_sequential_per_class_and_idempotent_per_user() -> None:
    repository = InMemoryJoiningOrderRepository()
    assert repository.allocate_next("calculus_1151", "01", "usr_amber") == 1
    assert repository.allocate_next("calculus_1151", "01", "usr_amber") == 1
    assert repository.allocate_next("calculus_1151", "01", "usr_basil") == 2
    assert repository.allocate_next("calculus_1151", "02", "usr_coral") == 1


def test_student_can_create_one_idempotent_case_post_through_writer_port() -> None:
    async def scenario() -> tuple[str, bool, int, tuple[str, ...]]:
        service, writer, _ = harness()
        actor = ActorContext("usr_fixture_student", ())
        command = CreateCasePostCommand(
            "operation-create-1",
            "case_fixture",
            "Fixture question",
            "A fictional calculus question.",
        )
        first = await service.create_case_post(actor, command)
        replay = await service.create_case_post(actor, command)
        return (
            first.thread_id,
            replay.duplicate,
            len(writer.write_calls),
            tuple(call.operation for call in writer.write_calls),
        )

    thread_id, duplicate, call_count, operations = asyncio.run(scenario())
    assert thread_id == "fixture_thread_000001"
    assert duplicate is True
    assert call_count == 1
    assert operations == ("create_case_thread",)


def test_staff_membership_flow_sets_nnmmm_nickname_and_two_allowlisted_roles() -> None:
    async def scenario() -> tuple[str, bool, tuple[str, ...]]:
        service, writer, _ = harness()
        actor = ActorContext("usr_staff_example", ())
        command = ApplyMembershipCommand(
            "operation-membership-1",
            "usr_fixture_student",
            "623456789012345678",
            "calculus_1151",
            "01",
        )
        first = await service.apply_membership(actor, command)
        replay = await service.apply_membership(actor, command)
        return (
            first.course_alias,
            replay.duplicate,
            tuple(call.operation for call in writer.write_calls),
        )

    alias, duplicate, operations = asyncio.run(scenario())
    assert alias == "01001"
    assert duplicate is True
    assert operations == (
        "set_member_nickname",
        "add_member_role",
        "add_member_role",
    )


def test_non_staff_cannot_apply_membership_or_update_status() -> None:
    async def scenario() -> int:
        service, writer, _ = harness()
        actor = ActorContext("usr_fixture_student", ())
        with pytest.raises(AuthorizationError):
            await service.apply_membership(
                actor,
                ApplyMembershipCommand(
                    "operation-membership-2",
                    "usr_other_student",
                    "723456789012345678",
                    "calculus_1151",
                    "01",
                ),
            )
        with pytest.raises(AuthorizationError):
            await service.update_case_status(
                actor,
                UpdateCaseStatusCommand(
                    "operation-status-1",
                    "case_fixture",
                    CaseStatus.OPEN,
                    CaseStatus.ANSWERED,
                    "answered",
                ),
            )
        return len(writer.write_calls)

    assert asyncio.run(scenario()) == 0


def test_staff_status_update_uses_compare_and_set_and_status_writer_interface() -> None:
    async def scenario() -> tuple[CaseStatus, bool, tuple[str, ...]]:
        service, writer, _ = harness()
        student = ActorContext("usr_fixture_student", ())
        staff = ActorContext("usr_ta_fixture", (STAFF_ROLE_ID,))
        await service.create_case_post(
            student,
            CreateCasePostCommand(
                "operation-create-2",
                "case_status_fixture",
                "Fixture status question",
                "A fictional question body.",
            ),
        )
        command = UpdateCaseStatusCommand(
            "operation-status-2",
            "case_status_fixture",
            CaseStatus.OPEN,
            CaseStatus.ANSWERED,
            "answered",
        )
        updated = await service.update_case_status(staff, command)
        replay = await service.update_case_status(staff, command)
        with pytest.raises(ConflictError):
            await service.update_case_status(
                staff,
                UpdateCaseStatusCommand(
                    "operation-status-3",
                    "case_status_fixture",
                    CaseStatus.OPEN,
                    CaseStatus.CLOSED,
                    "closed",
                ),
            )
        return (
            updated.status,
            replay.duplicate,
            tuple(call.operation for call in writer.write_calls),
        )

    status, duplicate, operations = asyncio.run(scenario())
    assert status is CaseStatus.ANSWERED
    assert duplicate is True
    assert operations == ("create_case_thread", "update_thread_status")


def test_button_modal_and_private_support_hooks_are_explicit_and_unique() -> None:
    async def interaction_hook(value: str) -> HookResult:
        return HookResult("RECORDED", value)

    async def private_hook(request: PrivateSupportRequest) -> HookResult:
        return HookResult("FIXTURE_PRIVATE_SUPPORT", "private_fixture")

    async def scenario() -> tuple[tuple[str, ...], tuple[str, ...], str]:
        service, _, hooks = harness()
        hooks.register_button("case_refresh", interaction_hook)
        hooks.register_modal("anonymous_reply", interaction_hook)
        with pytest.raises(ConflictError):
            hooks.register_button("case_refresh", interaction_hook)
        with pytest.raises(NotConfiguredError):
            await service.create_private_support(
                ActorContext("usr_fixture_student", ()),
                "operation-private-1",
                "A fictional private-support request.",
            )
        hooks.register_private_support(private_hook)
        result = await service.create_private_support(
            ActorContext("usr_fixture_student", ()),
            "operation-private-2",
            "A fictional private-support request.",
        )
        return hooks.button_names, hooks.modal_names, result.outcome

    buttons, modals, outcome = asyncio.run(scenario())
    assert buttons == ("case_refresh",)
    assert modals == ("anonymous_reply",)
    assert outcome == "FIXTURE_PRIVATE_SUPPORT"


def test_discord_py_app_starts_without_token_and_registers_only_health_command() -> None:
    async def scenario() -> tuple[HealthStatus, tuple[str, ...], bool, bool, bool]:
        service, _, _ = harness()
        config = load_course_assistant_config(
            {
                "COURSE_ASSISTANT_GUILD_ID": GUILD_ID,
                "COURSE_ASSISTANT_CHANNEL_IDS": CHANNEL_ID,
            }
        )
        app = CourseAssistantDiscordApp(
            config,
            service,
            now=lambda: "2026-07-19T10:00:00+00:00",
        )
        await app.start()
        values = (
            app.status,
            tuple(command.name for command in app.bot.tree.get_commands()),
            app.bot.intents.guilds,
            app.bot.intents.members,
            app.bot.intents.message_content,
        )
        await app.stop()
        return values

    status, commands, guilds, members, message_content = asyncio.run(scenario())
    assert status is HealthStatus.READY
    assert commands == ("health",)
    assert guilds is True
    assert members is False
    assert message_content is False


def test_course_assistant_service_has_no_archive_or_moderation_surface() -> None:
    service, _, _ = harness()
    assert not hasattr(service, "fetch_thread")
    assert not hasattr(service, "export_thread")
    assert not hasattr(service, "moderate_member")
