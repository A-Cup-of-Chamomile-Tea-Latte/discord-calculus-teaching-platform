# mypy: disable-error-code="no-untyped-def,assignment,method-assign,union-attr"
from __future__ import annotations

import re
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from tools.discord_provisioning.live import (
    LiveProvisioner,
    ProvisioningError,
    desired_overwrites,
    parse_args,
)
from tools.discord_provisioning.live_spec import (
    CATEGORIES,
    CHANNELS,
    MANAGED_FORUM_KEYS,
    ROLES,
    class_resource_errors,
    validate_spec,
)


class _Target:
    def __init__(self, target_id: int, name: str) -> None:
        self.id = target_id
        self.name = name


def test_live_spec_has_unique_logical_keys_and_supported_types() -> None:
    validate_spec()
    keys = (
        [item.key for item in ROLES]
        + [item.key for item in CATEGORIES]
        + [item.key for item in CHANNELS]
    )
    assert len(keys) == len(set(keys))
    assert {channel.kind for channel in CHANNELS} == {"text", "forum", "voice"}


def test_only_approved_forums_enter_case_lifecycle() -> None:
    managed = {channel.key for channel in CHANNELS if channel.managed_case}
    assert managed == MANAGED_FORUM_KEYS
    assert all(channel.kind == "forum" for channel in CHANNELS if channel.managed_case)


def test_live_spec_contains_exactly_the_sixteen_class_identity_roles() -> None:
    role_names = [role.name for role in ROLES]
    channel_names = [channel.name for channel in CHANNELS]
    assert [name for name in role_names if re.fullmatch(r"C\d\d", name)] == [
        f"C{number:02d}" for number in range(1, 17)
    ]
    assert not any(re.fullmatch(r"C\d\d", name) for name in channel_names)


def test_class_resource_validation_accepts_exact_roles_only() -> None:
    expected = [f"C{number:02d}" for number in range(1, 17)]

    assert class_resource_errors(expected, ["welcome"]) == []
    assert class_resource_errors(expected[:-1], ["welcome"]) == [
        "class roles must be exactly C01 through C16"
    ]
    assert class_resource_errors(expected, ["C01"]) == ["forbidden Cxx channel exists"]


def test_dump_and_course_bot_are_not_mutable_role_specs() -> None:
    names = {role.name for role in ROLES}
    assert "DC-Calculus-Manager" not in names
    assert "DC-Calculus-Archive" not in names


def test_private_support_has_one_permanent_non_case_entry() -> None:
    entries = [
        channel for channel in CHANNELS if channel.category_key == "category.private_support"
    ]

    assert [
        (entry.key, entry.name, entry.kind, entry.policy, entry.managed_case) for entry in entries
    ] == [
        (
            "channel.private_support_entry",
            "開啟隱密案件",
            "text",
            "private_support_entry",
            False,
        )
    ]


def test_private_entry_allows_commands_but_rejects_member_content() -> None:
    spec = next(channel for channel in CHANNELS if channel.key == "channel.private_support_entry")
    everyone = _Target(1, "@everyone")
    admin = _Target(2, "Admin")
    staff = _Target(3, "Staff / TA")
    verified = _Target(4, "Verified Member")
    guest = _Target(5, "Guest")
    course = _Target(6, "DC-Calculus-Manager")
    dump = _Target(7, "DC-Calculus-Archive")

    overwrites = desired_overwrites(
        spec,
        everyone=everyone,  # type: ignore[arg-type]
        admin=admin,  # type: ignore[arg-type]
        staff=staff,  # type: ignore[arg-type]
        verified=verified,  # type: ignore[arg-type]
        guest=guest,  # type: ignore[arg-type]
        course=course,  # type: ignore[arg-type]
        dump=dump,  # type: ignore[arg-type]
    )

    for member in (verified, guest):
        permission = overwrites[member]  # type: ignore[index]
        assert permission.view_channel is True
        assert permission.read_message_history is True
        assert permission.use_application_commands is True
        assert permission.send_messages is False
        assert permission.send_messages_in_threads is False
        assert permission.create_public_threads is False
        assert permission.create_private_threads is False
        assert permission.attach_files is False
    for operator in (admin,):
        permission = overwrites[operator]  # type: ignore[index]
        assert permission.view_channel is True
        assert permission.send_messages is True
        assert permission.manage_messages is None
        assert permission.manage_channels is True
    staff_permission = overwrites[staff]  # type: ignore[index]
    assert staff_permission.view_channel is True
    assert staff_permission.send_messages is True
    assert staff_permission.manage_messages is None
    assert staff_permission.manage_channels is False
    course_permission = overwrites[course]  # type: ignore[index]
    assert course_permission.manage_channels is True
    assert course_permission.manage_messages is None
    assert overwrites[everyone].view_channel is True  # type: ignore[index]
    assert overwrites[everyone].use_application_commands is True  # type: ignore[index]
    assert overwrites[everyone].send_messages is False  # type: ignore[index]
    assert overwrites[dump].view_channel is False  # type: ignore[index]


def test_private_entry_preserves_existing_managed_bot_role_boundary() -> None:
    provisioner = object.__new__(LiveProvisioner)
    provisioner.guild = MagicMock(spec=discord.Guild)
    provisioner.guild.default_role = MagicMock(spec=discord.Role)
    provisioner.course = MagicMock(spec=discord.Member)
    provisioner.course.top_role = MagicMock(spec=discord.Role)
    provisioner.course.guild_permissions = discord.Permissions.all()
    provisioner.dump = MagicMock(spec=discord.Member)
    provisioner.dump.top_role = MagicMock(spec=discord.Role)
    provisioner.roles = {
        "role.admin": MagicMock(spec=discord.Role),
        "role.staff": MagicMock(spec=discord.Role),
        "role.verified_member": MagicMock(spec=discord.Role),
        "role.guest": MagicMock(spec=discord.Role),
    }
    spec = next(item for item in CHANNELS if item.key == "channel.private_support_entry")

    overwrites = provisioner.private_entry_overwrites(spec)

    assert provisioner.course not in overwrites
    assert provisioner.course.top_role not in overwrites
    assert provisioner.dump.top_role not in overwrites


def test_private_entry_rejects_acl_bits_the_bot_cannot_write() -> None:
    provisioner = object.__new__(LiveProvisioner)
    provisioner.course = MagicMock(spec=discord.Member)
    provisioner.course.guild_permissions = discord.Permissions(view_channel=True)
    role = cast(discord.Role, MagicMock(spec=discord.Role))
    desired: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {
        role: discord.PermissionOverwrite(view_channel=True, send_voice_messages=False)
    }

    with pytest.raises(ProvisioningError, match="send_voice_messages"):
        provisioner.validate_private_entry_writable_permissions(desired)


@pytest.mark.asyncio
async def test_private_entry_never_writes_managed_bot_role_overwrites() -> None:
    provisioner = object.__new__(LiveProvisioner)
    provisioner.course = MagicMock(spec=discord.Member)
    provisioner.course.top_role = MagicMock(spec=discord.Role)
    provisioner.course.guild_permissions = discord.Permissions.all()
    provisioner.course.top_role.id = 90
    provisioner.dump = MagicMock(spec=discord.Member)
    provisioner.dump.top_role = MagicMock(spec=discord.Role)
    provisioner.dump.top_role.id = 91
    provisioner.operations = MagicMock()
    provisioner.guild = MagicMock(spec=discord.Guild)
    provisioner.guild.default_role = MagicMock(spec=discord.Role)
    provisioner.guild.default_role.id = 1
    provisioner.roles = {
        "role.verified_member": MagicMock(spec=discord.Role),
        "role.guest": MagicMock(spec=discord.Role),
        "role.admin": MagicMock(spec=discord.Role),
        "role.staff": MagicMock(spec=discord.Role),
    }
    for role_id, role in enumerate(provisioner.roles.values(), start=10):
        role.id = role_id

    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 100
    channel.edit = AsyncMock()
    channel.set_permissions = AsyncMock()
    managed = discord.PermissionOverwrite(view_channel=True)
    channel.overwrites_for.side_effect = lambda target: (
        managed
        if target in {provisioner.course.top_role, provisioner.dump.top_role}
        else discord.PermissionOverwrite()
    )
    channel.overwrites = {
        provisioner.course.top_role: managed,
        provisioner.dump.top_role: managed,
    }
    member_role = provisioner.roles["role.verified_member"]
    desired: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {
        member_role: discord.PermissionOverwrite(view_channel=True)
    }

    await provisioner.ensure_private_entry_overwrites(channel, desired)

    channel.edit.assert_not_awaited()
    written_targets = [call.args[0] for call in channel.set_permissions.await_args_list]
    assert written_targets == [member_role]
    assert provisioner.course.top_role not in written_targets
    assert provisioner.dump.top_role not in written_targets


def test_private_entry_targeted_commands_are_explicitly_allowlisted() -> None:
    for command in ("plan-private-entry", "ensure-private-entry"):
        args = parse_args([command, "--guild-id", "123"])
        assert args.command == command
        assert not hasattr(args, "reset_lab")


@pytest.mark.asyncio
async def test_targeted_ensure_does_not_enter_full_reconciliation(tmp_path) -> None:
    provisioner = object.__new__(LiveProvisioner)
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = 100
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 101
    channel.category_id = 100
    channel.topic = next(
        item for item in CHANNELS if item.key == "channel.private_support_entry"
    ).topic
    roles = {
        "role.admin": MagicMock(spec=discord.Role),
        "role.staff": MagicMock(spec=discord.Role),
        "role.verified_member": MagicMock(spec=discord.Role),
        "role.guest": MagicMock(spec=discord.Role),
    }
    guild = MagicMock(spec=discord.Guild)
    guild.default_role = MagicMock(spec=discord.Role)
    provisioner.guild = guild
    provisioner.course = MagicMock(spec=discord.Member)
    provisioner.course.top_role = MagicMock(spec=discord.Role)
    provisioner.course.guild_permissions = discord.Permissions.all()
    provisioner.dump = MagicMock(spec=discord.Member)
    provisioner.dump.top_role = MagicMock(spec=discord.Role)
    provisioner.roles = roles
    provisioner.categories = {"category.private_support": category}
    provisioner.channels = {"channel.private_support_entry": channel}
    provisioner.operations = MagicMock(mutations=0, actions={})
    provisioner.store = MagicMock(path=tmp_path / "mapping.json")
    provisioner.run_dir = tmp_path
    provisioner.plan_private_entry = AsyncMock(
        return_value={"unrelated_drift": ["forum.example: report only"]}
    )
    provisioner.resolve_private_entry_context = AsyncMock()
    provisioner.ensure_private_entry_overwrites = AsyncMock()
    provisioner.update_private_entry_runtime_config = MagicMock()
    provisioner.private_entry_errors = AsyncMock(return_value=[])
    provisioner.ensure_roles = AsyncMock(side_effect=AssertionError("full role reconcile called"))
    provisioner.ensure_categories = AsyncMock(
        side_effect=AssertionError("full category reconcile called")
    )
    provisioner.ensure_channels = AsyncMock(
        side_effect=AssertionError("full channel reconcile called")
    )
    provisioner.enforce_bot_boundaries = AsyncMock(
        side_effect=AssertionError("global boundary reconcile called")
    )

    result = await provisioner.ensure_private_entry()

    assert result["ok"] is True
    assert result["other_resources_action"] == "REPORTED_ONLY"
    provisioner.ensure_private_entry_overwrites.assert_awaited_once()
    assert provisioner.ensure_private_entry_overwrites.await_args.args[0] is channel
    provisioner.ensure_roles.assert_not_awaited()
    provisioner.ensure_categories.assert_not_awaited()
    provisioner.ensure_channels.assert_not_awaited()
    provisioner.enforce_bot_boundaries.assert_not_awaited()


@pytest.mark.asyncio
async def test_targeted_ensure_rolls_back_a_new_channel_when_acl_fails(tmp_path) -> None:
    provisioner = object.__new__(LiveProvisioner)
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = 100
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 101
    channel.name = "開啟隱密案件"
    channel.delete = AsyncMock()
    guild = MagicMock(spec=discord.Guild)
    guild.default_role = MagicMock(spec=discord.Role)
    guild.create_text_channel = AsyncMock(return_value=channel)
    provisioner.guild = guild
    provisioner.course = MagicMock(spec=discord.Member)
    provisioner.course.top_role = MagicMock(spec=discord.Role)
    provisioner.course.guild_permissions = discord.Permissions.all()
    provisioner.dump = MagicMock(spec=discord.Member)
    provisioner.dump.top_role = MagicMock(spec=discord.Role)
    provisioner.roles = {
        "role.admin": MagicMock(spec=discord.Role),
        "role.staff": MagicMock(spec=discord.Role),
        "role.verified_member": MagicMock(spec=discord.Role),
        "role.guest": MagicMock(spec=discord.Role),
    }
    provisioner.categories = {"category.private_support": category}
    provisioner.channels = {}
    provisioner.operations = MagicMock(mutations=0, actions={})
    provisioner.store = MagicMock(path=tmp_path / "mapping.json")
    provisioner.run_dir = tmp_path
    provisioner.plan_private_entry = AsyncMock(return_value={"unrelated_drift": []})
    provisioner.resolve_private_entry_context = AsyncMock()
    provisioner.ensure_private_entry_overwrites = AsyncMock(side_effect=RuntimeError("ACL_FAILED"))
    provisioner.update_private_entry_runtime_config = MagicMock()

    with pytest.raises(RuntimeError, match="ACL_FAILED"):
        await provisioner.ensure_private_entry()

    channel.delete.assert_awaited_once()
    assert [item.args[0] for item in provisioner.store.remove.call_args_list] == [
        "channel.private_support_entry"
    ]
    provisioner.update_private_entry_runtime_config.assert_not_called()
