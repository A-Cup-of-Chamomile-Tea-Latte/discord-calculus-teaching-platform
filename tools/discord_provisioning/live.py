# mypy: ignore-errors
"""Rerunnable live provisioning CLI for the allowlisted empty Discord test Guild.

This operator-only adapter mirrors discord.py's highly dynamic resource surface.
Its pure desired-state specification remains covered by strict mypy and tests.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

import discord
from dotenv import dotenv_values

from tools.discord_provisioning.live_spec import (
    CATEGORIES,
    CHANNELS,
    GUIDELINES_CONTENT,
    GUIDELINES_TITLE,
    MANAGED_FORUM_KEYS,
    PRIVATE_SUPPORT_ENTRY_CONTENT,
    ROLES,
    WELCOME_CONTENT,
    ChannelSpec,
    class_resource_errors,
    validate_spec,
)

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / ".local" / "discord-course-bots-runtime"
DEFAULT_ENV_FILE = RUNTIME_ROOT / ".env"
DEFAULT_MAP_FILE = RUNTIME_ROOT / "data" / "discord_provisioning_resources.json"
DEFAULT_ARTIFACT_ROOT = RUNTIME_ROOT / "artifacts" / "provisioning"
REASON = "2026-07-30 approved calculus server infrastructure provisioning"
LEGACY_ROLE_NAMES = {
    "verified_student_role_id": "Verified Student",
    "guest_role_id": "Guest",
    "ta_role_id": "TA",
    "professor_role_id": "Professor",
}
LEGACY_CHANNEL_NAMES = {
    "bot_control_channel_id": "bot-control",
    "public_forum_channel_id": "math-questions",
}
APPROVED_DEFAULT_CHANNELS = {
    "資訊": {"歡迎訊息與相關規則", "公告", "資源"},
    "文字頻道": {"一般", "會議計畫", "離題"},
    "語音頻道": {"聊天室", "會議室 1", "會議室 2"},
}
T = TypeVar("T")


class ProvisioningError(RuntimeError):
    """A live state prevents safe deterministic provisioning."""


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def json_dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def resolve_database_path(env: dict[str, str | None]) -> Path:
    raw = Path(str(env.get("DATABASE_PATH") or "data/course_bots.sqlite3"))
    if raw.is_absolute():
        return raw
    env_root = Path(str(env.get("_ENV_FILE_DIR") or RUNTIME_ROOT))
    return env_root / raw


def permission_names(value: discord.Permissions) -> list[str]:
    return sorted(name for name, enabled in value if enabled)


def channel_kind(channel: discord.abc.GuildChannel) -> str:
    if isinstance(channel, discord.CategoryChannel):
        return "category"
    if isinstance(channel, discord.ForumChannel):
        return "forum"
    if isinstance(channel, discord.TextChannel):
        return "text"
    if isinstance(channel, discord.VoiceChannel):
        return "voice"
    return str(channel.type)


def inventory_document(guild: discord.Guild) -> dict[str, object]:
    roles = [
        {
            "id": role.id,
            "name": role.name,
            "position": role.position,
            "managed": role.managed,
            "permissions": permission_names(role.permissions),
        }
        for role in sorted(guild.roles, reverse=True)
    ]
    channels: list[dict[str, object]] = []
    for channel in guild.channels:
        overwrites = []
        for target, overwrite in channel.overwrites.items():
            allow, deny = overwrite.pair()
            overwrites.append(
                {
                    "target_id": target.id,
                    "target_type": "role" if isinstance(target, discord.Role) else "member",
                    "target_name": target.name
                    if isinstance(target, discord.Role)
                    else "[member overwrite]",
                    "allow": permission_names(allow),
                    "deny": permission_names(deny),
                }
            )
        channels.append(
            {
                "id": channel.id,
                "name": channel.name,
                "type": channel_kind(channel),
                "position": channel.position,
                "category_id": channel.category_id,
                "category_name": channel.category.name if channel.category else None,
                "overwrites": sorted(overwrites, key=lambda item: int(item["target_id"])),
            }
        )
    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "guild": {"id": guild.id, "name": guild.name, "owner_id": guild.owner_id},
        "roles": roles,
        "channels": channels,
    }


class ResourceStore:
    def __init__(self, path: Path, guild_id: int) -> None:
        self.path = path
        self.guild_id = guild_id
        if path.exists():
            value: object = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ProvisioningError("resource mapping is not a JSON object")
            mapped_guild = value.get("guild_id")
            if mapped_guild is not None and int(mapped_guild) != guild_id:
                raise ProvisioningError("resource mapping belongs to another Guild")
            raw = value.get("resources", {})
            if not isinstance(raw, dict):
                raise ProvisioningError("resource mapping resources is not an object")
            self.resources = {
                str(key): dict(item)
                for key, item in raw.items()
                if isinstance(item, dict) and "id" in item
            }
        else:
            self.resources: dict[str, dict[str, object]] = {}

    def get_id(self, key: str) -> int | None:
        item = self.resources.get(key)
        return None if item is None else int(item["id"])

    def set(self, key: str, resource_id: int, kind: str, name: str) -> None:
        self.resources[key] = {"id": resource_id, "kind": kind, "name": name}
        self.save()

    def remove(self, key: str) -> None:
        if key in self.resources:
            del self.resources[key]
            self.save()

    def save(self) -> None:
        json_dump(
            self.path,
            {
                "schema_version": 1,
                "guild_id": self.guild_id,
                "updated_at": datetime.now(UTC).isoformat(),
                "resources": dict(sorted(self.resources.items())),
                "managed_case_forums": sorted(MANAGED_FORUM_KEYS),
            },
        )


class OperationLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        os.chmod(path, 0o600)
        self.mutations = 0
        self.actions: dict[str, int] = {}

    def record(self, action: str, key: str, resource_id: int | None = None) -> None:
        entry = {
            "at": datetime.now(UTC).isoformat(),
            "action": action,
            "key": key,
            "resource_id": resource_id,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if action not in {"verified", "inventory", "adopted"}:
            self.mutations += 1
        self.actions[action] = self.actions.get(action, 0) + 1


def _overwrite(**values: bool | None) -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(**values)


MEMBER_TEXT = {
    "view_channel": True,
    "send_messages": True,
    "read_message_history": True,
    "attach_files": True,
    "embed_links": True,
}
MEMBER_FORUM = {
    **MEMBER_TEXT,
    "send_messages_in_threads": True,
    "create_public_threads": True,
}
READ_ONLY = {
    "view_channel": True,
    "read_message_history": True,
    "send_messages": False,
    "send_messages_in_threads": False,
    "create_public_threads": False,
    "create_private_threads": False,
    "add_reactions": False,
    "attach_files": False,
    "embed_links": False,
}
PRIVATE_SUPPORT_ENTRY_MEMBER = {
    "view_channel": True,
    "read_message_history": True,
    "use_application_commands": True,
    "send_messages": False,
    "send_messages_in_threads": False,
    "create_public_threads": False,
    "create_private_threads": False,
    "add_reactions": False,
    "attach_files": False,
    "embed_links": False,
    "send_voice_messages": False,
    "send_polls": False,
}
PRIVATE_SUPPORT_ENTRY_STAFF = {
    **PRIVATE_SUPPORT_ENTRY_MEMBER,
    "send_messages": True,
    "manage_messages": True,
    "manage_channels": False,
    "mention_everyone": False,
}
PRIVATE_SUPPORT_ENTRY_ADMIN = {
    **PRIVATE_SUPPORT_ENTRY_STAFF,
    "manage_channels": True,
}
HIDDEN = {
    "view_channel": False,
    "send_messages": False,
    "send_messages_in_threads": False,
    "create_public_threads": False,
    "create_private_threads": False,
}
STAFF_TEXT = {
    **MEMBER_TEXT,
    "manage_threads": True,
}
STAFF_FORUM = {
    **MEMBER_FORUM,
    "manage_threads": True,
}
COURSE_CASE = {
    **MEMBER_FORUM,
    "manage_threads": True,
    "manage_channels": True,
    "mention_everyone": False,
}
PROVISIONER_ACCESS = {
    "view_channel": True,
    "manage_channels": True,
    "read_message_history": False,
    "send_messages": False,
    "send_messages_in_threads": False,
    "mention_everyone": False,
}
PROVISIONER_FORUM = {
    **MEMBER_FORUM,
    "manage_channels": True,
    "mention_everyone": False,
}
PROVISIONER_TEXT = {
    **MEMBER_TEXT,
    "manage_channels": True,
    "mention_everyone": False,
}
PROVISIONER_VOICE = {
    "view_channel": True,
    "connect": True,
    "speak": True,
    "stream": True,
    "use_embedded_activities": True,
    "manage_channels": True,
}
DUMP_GLOBAL_DENY = {
    "send_messages": False,
    "send_messages_in_threads": False,
    "create_public_threads": False,
    "create_private_threads": False,
    "attach_files": False,
    "embed_links": False,
    "add_reactions": False,
    "mention_everyone": False,
    "connect": False,
    "speak": False,
    "stream": False,
    "use_embedded_activities": False,
}


def desired_overwrites(
    spec: ChannelSpec,
    *,
    everyone: discord.Role,
    admin: discord.Role,
    staff: discord.Role,
    verified: discord.Role,
    guest: discord.Role,
    course: discord.Role | discord.Member,
    dump: discord.Role | discord.Member,
) -> dict[discord.Role | discord.Member, discord.PermissionOverwrite]:
    targets: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {}

    def add(target: discord.Role | discord.Member, values: dict[str, bool]) -> None:
        targets[target] = _overwrite(**values)

    if spec.policy == "welcome":
        add(everyone, MEMBER_TEXT)
        add(verified, MEMBER_TEXT)
        add(guest, MEMBER_TEXT)
        add(admin, STAFF_TEXT)
        add(staff, STAFF_TEXT)
        add(course, COURSE_CASE)
        add(dump, READ_ONLY)
    elif spec.policy == "staff_forum":
        add(everyone, {**READ_ONLY, "view_channel": True})
        add(verified, READ_ONLY)
        add(guest, READ_ONLY)
        add(admin, STAFF_FORUM)
        add(staff, STAFF_FORUM)
        add(course, COURSE_CASE)
        add(dump, READ_ONLY)
    elif spec.policy == "member_forum":
        add(
            everyone,
            READ_ONLY if spec.key == "forum.course_resources" else HIDDEN,
        )
        add(verified, MEMBER_FORUM)
        add(guest, MEMBER_FORUM)
        add(admin, STAFF_FORUM)
        add(staff, STAFF_FORUM)
        add(course, COURSE_CASE)
        add(dump, READ_ONLY if spec.key == "forum.course_resources" else HIDDEN)
    elif spec.policy == "case_forum":
        add(everyone, HIDDEN)
        add(verified, MEMBER_FORUM)
        add(guest, MEMBER_FORUM)
        add(admin, STAFF_FORUM)
        add(staff, STAFF_FORUM)
        add(course, COURSE_CASE)
        add(dump, READ_ONLY)
    elif spec.policy == "member_text":
        add(everyone, HIDDEN)
        add(verified, MEMBER_TEXT)
        add(guest, MEMBER_TEXT)
        add(admin, STAFF_TEXT)
        add(staff, STAFF_TEXT)
        add(course, COURSE_CASE)
        add(dump, HIDDEN)
    elif spec.policy == "private_support_entry":
        add(everyone, HIDDEN)
        add(verified, PRIVATE_SUPPORT_ENTRY_MEMBER)
        add(guest, PRIVATE_SUPPORT_ENTRY_MEMBER)
        add(admin, PRIVATE_SUPPORT_ENTRY_ADMIN)
        add(staff, PRIVATE_SUPPORT_ENTRY_STAFF)
        add(course, PRIVATE_SUPPORT_ENTRY_ADMIN)
        add(dump, HIDDEN)
    elif spec.policy == "member_voice":
        voice_member = {
            "view_channel": True,
            "connect": True,
            "speak": True,
            "stream": True,
            "use_embedded_activities": True,
        }
        voice_staff = {
            **voice_member,
        }
        add(everyone, HIDDEN)
        add(verified, voice_member)
        add(guest, voice_member)
        add(admin, voice_staff)
        add(staff, voice_staff)
        add(course, PROVISIONER_VOICE)
        add(dump, HIDDEN)
    elif spec.policy == "staff_only" or spec.policy == "staff_bot":
        add(everyone, HIDDEN)
        add(verified, HIDDEN)
        add(guest, HIDDEN)
        add(admin, STAFF_TEXT)
        add(staff, STAFF_TEXT)
        add(course, COURSE_CASE)
        add(dump, HIDDEN)
    else:
        raise ProvisioningError(f"unknown permission policy: {spec.policy}")
    return targets


def desired_category_overwrites(
    key: str,
    *,
    everyone: discord.Role,
    admin: discord.Role,
    staff: discord.Role,
    verified: discord.Role,
    guest: discord.Role,
    course: discord.Role | discord.Member,
    dump: discord.Role | discord.Member,
) -> dict[discord.Role | discord.Member, discord.PermissionOverwrite]:
    targets: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {}

    def add(target: discord.Role | discord.Member, values: dict[str, bool]) -> None:
        targets[target] = _overwrite(**values)

    visible = {"view_channel": True, "read_message_history": True}
    staff_visible = {**visible, "manage_channels": True}
    if key == "category.information":
        for target in (everyone, verified, guest):
            add(target, visible)
        for target in (admin, staff):
            add(target, staff_visible)
        add(course, COURSE_CASE)
        add(dump, READ_ONLY)
    elif key == "category.question":
        add(everyone, HIDDEN)
        for target in (verified, guest):
            add(target, visible)
        for target in (admin, staff):
            add(target, staff_visible)
        add(course, COURSE_CASE)
        add(dump, READ_ONLY)
    elif key == "category.community":
        add(everyone, HIDDEN)
        for target in (verified, guest):
            add(target, visible)
        for target in (admin, staff):
            add(target, staff_visible)
        add(course, COURSE_CASE)
        add(dump, HIDDEN)
    elif key == "category.private_support":
        add(everyone, HIDDEN)
        add(verified, HIDDEN)
        add(guest, HIDDEN)
        add(admin, STAFF_TEXT | {"manage_channels": True})
        add(staff, STAFF_TEXT | {"manage_channels": True})
        add(course, COURSE_CASE)
        add(dump, HIDDEN)
    elif key == "category.voice":
        add(everyone, HIDDEN)
        for target in (verified, guest, admin, staff):
            add(target, {"view_channel": True})
        add(course, PROVISIONER_VOICE)
        add(dump, HIDDEN)
    elif key == "category.staff":
        add(everyone, HIDDEN)
        add(verified, HIDDEN)
        add(guest, HIDDEN)
        add(admin, STAFF_TEXT | {"manage_channels": True})
        add(staff, STAFF_TEXT | {"manage_channels": True})
        add(course, COURSE_CASE)
        add(dump, HIDDEN)
    else:
        raise ProvisioningError(f"unknown category policy: {key}")
    return targets


def overwrite_signature(
    value: dict[discord.Role | discord.Member, discord.PermissionOverwrite],
) -> dict[int, tuple[int, int]]:
    result: dict[int, tuple[int, int]] = {}
    for target, overwrite in value.items():
        allow, deny = overwrite.pair()
        result[target.id] = (allow.value, deny.value)
    return result


async def retry(  # noqa: UP047 - Python 3.11 remains a supported project runtime.
    operation: Callable[[], Awaitable[T]],
    *,
    label: str,
    attempts: int = 3,
) -> T:
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except (discord.Forbidden, discord.NotFound):
            raise
        except discord.HTTPException:
            if attempt == attempts:
                raise
            await asyncio.sleep(2 ** (attempt - 1))
    raise AssertionError(f"retry loop exhausted for {label}")


async def delete_permission_overwrite(channel: discord.abc.GuildChannel, target: object) -> None:
    """Delete cached or unresolved member/role overwrites safely.

    With guild-only intents, discord.py represents an uncached member overwrite as
    ``discord.Object``. ``set_permissions`` rejects that placeholder even though
    Discord's delete endpoint only needs the target snowflake.
    """

    if isinstance(target, (discord.Member, discord.Role)):
        await channel.set_permissions(target, overwrite=None, reason=REASON)
        return
    target_id = int(target.id)  # type: ignore[attr-defined]
    await channel._state.http.delete_channel_permissions(  # type: ignore[attr-defined]
        channel.id, target_id, reason=REASON
    )


class LiveProvisioner:
    def __init__(
        self,
        guild: discord.Guild,
        *,
        env: dict[str, str | None],
        store: ResourceStore,
        operations: OperationLog,
        run_dir: Path,
    ) -> None:
        self.guild = guild
        self.env = env
        self.store = store
        self.operations = operations
        self.run_dir = run_dir
        self.database_path = resolve_database_path(env)
        self.course_client_id = int(str(env["COURSE_ASSISTANT_CLIENT_ID"]))
        self.dump_client_id = int(str(env["DUMP_BOT_CLIENT_ID"]))
        self.course: discord.Member
        self.dump: discord.Member
        self.roles: dict[str, discord.Role] = {}
        self.categories: dict[str, discord.CategoryChannel] = {}
        self.channels: dict[str, discord.abc.GuildChannel] = {}
        self.warnings: list[str] = []

    async def initialize(self) -> None:
        if self.guild.id != int(str(self.env["TEST_GUILD_ID"])):
            raise ProvisioningError("connected Guild does not match TEST_GUILD_ID")
        try:
            self.course = await self.guild.fetch_member(self.course_client_id)
            self.dump = await self.guild.fetch_member(self.dump_client_id)
        except discord.HTTPException as exc:
            raise ProvisioningError(f"cannot resolve both approved bot members: {exc}") from exc
        if self.guild.me is None or self.guild.me.id != self.course.id:
            raise ProvisioningError("live CLI is not authenticated as course_assistant")
        if not self.course.guild_permissions.manage_channels:
            raise ProvisioningError("course_assistant lacks Manage Channels")
        if not self.course.guild_permissions.manage_roles:
            raise ProvisioningError("course_assistant lacks Manage Roles")
        if self.course.guild_permissions.administrator:
            raise ProvisioningError("course_assistant unexpectedly has Administrator")

    def db_config(self) -> dict[str, str]:
        with sqlite3.connect(self.database_path) as db:
            rows = db.execute("SELECT key, value FROM runtime_config").fetchall()
        return {str(key): str(value) for key, value in rows}

    async def inspect_channel_read_only(
        self, key: str, name: str, expected: type[discord.abc.GuildChannel]
    ) -> tuple[discord.abc.GuildChannel | None, bool]:
        """Resolve one resource without changing the mapping or Discord state.

        The boolean reports whether an existing exact-name resource would need to be
        adopted into the local mapping by the targeted ensure command.
        """

        mapped = self.store.get_id(key)
        if mapped is not None:
            channel = self.guild.get_channel(mapped)
            if channel is None:
                try:
                    fetched = await self.guild.fetch_channel(mapped)
                except discord.NotFound as exc:
                    raise ProvisioningError(f"mapped channel is missing: {key}") from exc
                except discord.Forbidden as exc:
                    raise ProvisioningError(
                        f"mapped channel is inaccessible to course_assistant: {key}"
                    ) from exc
                channel = fetched if isinstance(fetched, discord.abc.GuildChannel) else None
            if not isinstance(channel, expected) or channel.name != name:
                raise ProvisioningError(f"mapped channel drift for {key}")
            return channel, False
        candidates = [
            channel
            for channel in self.guild.channels
            if channel.name == name and isinstance(channel, expected)
        ]
        wrong_type = [
            channel
            for channel in self.guild.channels
            if channel.name == name and not isinstance(channel, expected)
        ]
        if wrong_type or len(candidates) > 1:
            raise ProvisioningError(f"unknown or ambiguous same-name channel: {name}")
        return (candidates[0], True) if candidates else (None, False)

    def inspect_role_read_only(self, key: str, name: str) -> tuple[discord.Role, bool]:
        mapped = self.store.get_id(key)
        if mapped is not None:
            role = self.guild.get_role(mapped)
            if role is None or role.managed or role.name != name:
                raise ProvisioningError(f"mapped role drift for {key}")
            return role, False
        candidates = [role for role in self.guild.roles if role.name == name and not role.managed]
        if len(candidates) != 1:
            raise ProvisioningError(f"required role is missing or ambiguous: {name}")
        return candidates[0], True

    async def resolve_private_entry_context(self, *, persist_adoptions: bool) -> list[str]:
        """Resolve only the allowlisted Private Support entry dependencies."""

        adoptions: list[str] = []
        role_names = {spec.key: spec.name for spec in ROLES}
        for key in (
            "role.admin",
            "role.staff",
            "role.verified_member",
            "role.guest",
        ):
            role, adopt = self.inspect_role_read_only(key, role_names[key])
            self.roles[key] = role
            if adopt:
                adoptions.append(key)
                if persist_adoptions:
                    self.store.set(key, role.id, "role", role.name)
                    self.operations.record("adopted", key, role.id)

        category_spec = next(spec for spec in CATEGORIES if spec.key == "category.private_support")
        category, adopt_category = await self.inspect_channel_read_only(
            category_spec.key, category_spec.name, discord.CategoryChannel
        )
        if not isinstance(category, discord.CategoryChannel):
            raise ProvisioningError(
                "Private Support category is missing; targeted ensure will not create it"
            )
        self.categories[category_spec.key] = category
        if adopt_category:
            adoptions.append(category_spec.key)
            if persist_adoptions:
                self.store.set(category_spec.key, category.id, "category", category.name)
                self.operations.record("adopted", category_spec.key, category.id)

        entry_spec = next(spec for spec in CHANNELS if spec.key == "channel.private_support_entry")
        channel, adopt_channel = await self.inspect_channel_read_only(
            entry_spec.key, entry_spec.name, discord.TextChannel
        )
        if isinstance(channel, discord.TextChannel):
            if adopt_channel and channel.category_id != category.id:
                raise ProvisioningError(
                    "unmapped same-name Private Support entry is outside the approved category"
                )
            self.channels[entry_spec.key] = channel
            if adopt_channel:
                adoptions.append(entry_spec.key)
                if persist_adoptions:
                    self.store.set(entry_spec.key, channel.id, "text", channel.name)
                    self.operations.record("adopted", entry_spec.key, channel.id)
        return adoptions

    def unrelated_mapping_drift(self) -> list[str]:
        """Report mapped-resource drift outside the targeted entry scope without repairing it."""

        ignored = {
            "category.private_support",
            "channel.private_support_entry",
            "message.private_support_entry",
            "forum.managed_case",
        }
        drift: list[str] = []
        for key, item in sorted(self.store.resources.items()):
            if key in ignored or item.get("kind") == "metadata":
                continue
            resource_id = int(item["id"])
            kind = str(item.get("kind"))
            expected_name = str(item.get("name"))
            if kind in {"role", "managed_role"}:
                resource = self.guild.get_role(resource_id)
            elif kind == "thread":
                resource = self.guild.get_thread(resource_id)
            elif kind == "message":
                continue
            else:
                resource = self.guild.get_channel(resource_id)
            if resource is None:
                drift.append(f"{key}: mapped resource is missing")
            elif getattr(resource, "name", expected_name) != expected_name:
                drift.append(f"{key}: mapped resource name drifted")
        return drift

    async def resolve_role(
        self, key: str, name: str, *, allow_adopt: bool = True
    ) -> discord.Role | None:
        mapped = self.store.get_id(key)
        if mapped is not None:
            role = self.guild.get_role(mapped)
            if role is None:
                self.store.remove(key)
            else:
                if role.managed or role.name != name:
                    raise ProvisioningError(f"mapped role drift for {key}")
                return role
        candidates = [role for role in self.guild.roles if role.name == name]
        if len(candidates) > 1:
            raise ProvisioningError(f"ambiguous same-name role: {name}")
        if candidates:
            if not allow_adopt:
                raise ProvisioningError(f"unverified existing role conflicts with {name}")
            role = candidates[0]
            if role.managed:
                raise ProvisioningError(f"managed role conflicts with mutable role {name}")
            self.store.set(key, role.id, "role", role.name)
            self.operations.record("adopted", key, role.id)
            return role
        return None

    async def resolve_channel(
        self, key: str, name: str, expected: type[discord.abc.GuildChannel]
    ) -> discord.abc.GuildChannel | None:
        mapped = self.store.get_id(key)
        if mapped is not None:
            channel = self.guild.get_channel(mapped)
            if channel is None:
                try:
                    fetched = await self.guild.fetch_channel(mapped)
                except discord.NotFound:
                    self.store.remove(key)
                except discord.Forbidden as exc:
                    raise ProvisioningError(
                        f"mapped channel is inaccessible to course_assistant: {key}"
                    ) from exc
                else:
                    channel = fetched if isinstance(fetched, discord.abc.GuildChannel) else None
                    if channel is not None:
                        if not isinstance(channel, expected):
                            raise ProvisioningError(f"mapped channel type drift for {key}")
                        return channel
            else:
                if not isinstance(channel, expected):
                    raise ProvisioningError(f"mapped channel type drift for {key}")
                return channel
        candidates = [
            channel
            for channel in self.guild.channels
            if channel.name == name and isinstance(channel, expected)
        ]
        wrong_type = [
            channel
            for channel in self.guild.channels
            if channel.name == name and not isinstance(channel, expected)
        ]
        if wrong_type or len(candidates) > 1:
            raise ProvisioningError(f"unknown or ambiguous same-name channel: {name}")
        if candidates:
            channel = candidates[0]
            self.store.set(key, channel.id, channel_kind(channel), channel.name)
            self.operations.record("adopted", key, channel.id)
            return channel
        return None

    async def reset_legacy_lab(self) -> None:
        config = self.db_config()
        if config.get("discord_provisioning_version") == "2026-07-30":
            return
        allowed_channel_ids = {
            int(config[key])
            for key in LEGACY_CHANNEL_NAMES
            if key in config and config[key].isdigit()
        }
        private_ids: set[int] = set()
        with sqlite3.connect(self.database_path) as db:
            for (channel_id,) in db.execute("SELECT channel_id FROM private_support"):
                private_ids.add(int(channel_id))

        legacy_category_id = None
        for key, expected_name in LEGACY_CHANNEL_NAMES.items():
            raw = config.get(key)
            if raw is None or not raw.isdigit():
                continue
            channel = self.guild.get_channel(int(raw))
            if channel is None:
                continue
            if channel.name != expected_name:
                raise ProvisioningError(f"legacy provenance mismatch for {key}")
            if channel.category is None or channel.category.name != "BOT LAB":
                raise ProvisioningError(f"legacy channel escaped BOT LAB: {channel.name}")
            legacy_category_id = channel.category.id

        if legacy_category_id is not None:
            category = self.guild.get_channel(legacy_category_id)
            if not isinstance(category, discord.CategoryChannel) or category.name != "BOT LAB":
                raise ProvisioningError("legacy BOT LAB category provenance mismatch")
            unknown_children = [
                child for child in category.channels if child.id not in allowed_channel_ids
            ]
            if unknown_children:
                raise ProvisioningError(
                    "BOT LAB contains unverified children: "
                    + ", ".join(child.name for child in unknown_children)
                )
            for child in list(category.channels):
                await retry(
                    lambda child=child: child.delete(reason=REASON),
                    label="delete lab child",
                )
                self.operations.record("deleted", f"legacy.channel.{child.name}", child.id)
            await retry(lambda: category.delete(reason=REASON), label="delete BOT LAB")
            self.operations.record("deleted", "legacy.category.bot_lab", category.id)

        private_category_raw = config.get("private_support_category_id")
        if private_category_raw and private_category_raw.isdigit():
            channel = self.guild.get_channel(int(private_category_raw))
            if channel is not None:
                if (
                    not isinstance(channel, discord.CategoryChannel)
                    or channel.name != "PRIVATE SUPPORT"
                ):
                    raise ProvisioningError("legacy PRIVATE SUPPORT provenance mismatch")
                unknown_children = [
                    child for child in channel.channels if child.id not in private_ids
                ]
                if unknown_children:
                    raise ProvisioningError(
                        "PRIVATE SUPPORT contains unverified children: "
                        + ", ".join(child.name for child in unknown_children)
                    )
                for child in list(channel.channels):
                    await retry(
                        lambda child=child: child.delete(reason=REASON),
                        label="delete private test child",
                    )
                    self.operations.record(
                        "deleted", f"legacy.private_channel.{child.name}", child.id
                    )
                await retry(lambda: channel.delete(reason=REASON), label="delete PRIVATE SUPPORT")
                self.operations.record("deleted", "legacy.category.private_support", channel.id)

        for key, expected_name in LEGACY_ROLE_NAMES.items():
            raw = config.get(key)
            if raw is None or not raw.isdigit():
                continue
            role = self.guild.get_role(int(raw))
            if role is None:
                continue
            if role.name != expected_name or role.managed:
                raise ProvisioningError(f"legacy role provenance mismatch for {key}")
            if role >= self.course.top_role:
                raise ProvisioningError(f"cannot safely delete legacy role {role.name}")
            await retry(lambda role=role: role.delete(reason=REASON), label="delete legacy role")
            self.operations.record("deleted", f"legacy.role.{role.name}", role.id)

        for category_name, child_names in APPROVED_DEFAULT_CHANNELS.items():
            matches = [
                category for category in self.guild.categories if category.name == category_name
            ]
            if len(matches) > 1:
                raise ProvisioningError(f"ambiguous approved old category: {category_name}")
            if not matches:
                continue
            category = matches[0]
            actual_names = {child.name for child in category.channels}
            if actual_names != child_names:
                raise ProvisioningError(
                    f"approved old category children drifted: {category_name} "
                    f"expected={sorted(child_names)} actual={sorted(actual_names)}"
                )
            for child in list(category.channels):
                await retry(
                    lambda child=child: child.delete(reason=REASON),
                    label=f"delete approved old channel {child.name}",
                )
                self.operations.record("deleted", f"legacy.default_channel.{child.name}", child.id)
            await retry(
                lambda category=category: category.delete(reason=REASON),
                label=f"delete approved old category {category_name}",
            )
            self.operations.record(
                "deleted", f"legacy.default_category.{category_name}", category.id
            )

        backup = self.run_dir / "legacy-test-data.sqlite3"
        if not backup.exists():
            source = sqlite3.connect(self.database_path)
            destination = sqlite3.connect(backup)
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
            os.chmod(backup, 0o600)
        with sqlite3.connect(self.database_path) as db:
            db.execute("DELETE FROM private_dump_jobs")
            db.execute("DELETE FROM private_support")
            db.execute("DELETE FROM cases")
            db.execute("DELETE FROM drafts")
            db.commit()
        self.operations.record("deleted", "legacy.local_test_records")

    async def ensure_roles(self) -> None:
        for spec in ROLES:
            role = await self.resolve_role(spec.key, spec.name)
            if role is None:
                role = await retry(
                    lambda spec=spec: self.guild.create_role(
                        name=spec.name,
                        permissions=discord.Permissions.none(),
                        reason=REASON,
                    ),
                    label=f"create role {spec.name}",
                )
                self.store.set(spec.key, role.id, "role", role.name)
                self.operations.record("created", spec.key, role.id)
            elif (
                spec.key in {"role.verified_member", "role.guest"}
                or spec.key.startswith("role.class_")
            ) and role.permissions.value != 0:
                if role >= self.course.top_role:
                    raise ProvisioningError(f"cannot narrow role permissions: {role.name}")
                await retry(
                    lambda role=role: role.edit(
                        permissions=discord.Permissions.none(), reason=REASON
                    ),
                    label=f"narrow role {role.name}",
                )
                self.operations.record("updated", spec.key, role.id)
            self.roles[spec.key] = role

        hierarchy = [
            self.roles["role.admin"],
            self.roles["role.staff"],
            self.course.top_role,
            self.roles["role.verified_member"],
            self.roles["role.guest"],
            self.dump.top_role,
        ]
        unsafe_class_roles = [
            role.name
            for key, role in self.roles.items()
            if key.startswith("role.class_") and role >= self.course.top_role
        ]
        if unsafe_class_roles:
            self.warnings.append(
                "Course Manager must remain above class identity roles: "
                + ", ".join(unsafe_class_roles)
            )
        if not all(hierarchy[index] > hierarchy[index + 1] for index in range(len(hierarchy) - 1)):
            self.warnings.append(
                "Role hierarchy still needs the Guild owner to enforce "
                "Admin > Staff / TA > Manager > Verified > Guest > Archive."
            )
        staff_permissions = self.roles["role.staff"].permissions
        if not all(
            (
                staff_permissions.manage_messages,
                staff_permissions.mute_members,
                staff_permissions.deafen_members,
                staff_permissions.move_members,
            )
        ):
            self.warnings.append(
                "Staff / TA still lacks one or more owner-managed message/voice permissions."
            )
        admin_permissions = self.roles["role.admin"].permissions
        if not all(
            (
                admin_permissions.manage_messages,
                admin_permissions.mute_members,
                admin_permissions.deafen_members,
                admin_permissions.move_members,
            )
        ):
            self.warnings.append("Admin role still lacks owner-managed message/voice permissions.")
        self.store.set(
            "role.course_assistant",
            self.course.top_role.id,
            "managed_role",
            self.course.top_role.name,
        )
        self.store.set(
            "role.dump_bot", self.dump.top_role.id, "managed_role", self.dump.top_role.name
        )

    async def ensure_categories(self) -> None:
        role_args = {
            "everyone": self.guild.default_role,
            "admin": self.roles["role.admin"],
            "staff": self.roles["role.staff"],
            "verified": self.roles["role.verified_member"],
            "guest": self.roles["role.guest"],
            "course": self.course.top_role,
            "dump": self.dump.top_role,
        }
        for spec in CATEGORIES:
            try:
                category = await self.resolve_channel(spec.key, spec.name, discord.CategoryChannel)
            except ProvisioningError:
                if spec.key != "category.question":
                    raise
                self.warnings.append(
                    "category.question is pending an owner repair: grant "
                    "DC-Calculus-Manager View Channel or delete the inaccessible category."
                )
                continue
            if (
                spec.key == "category.question"
                and category is not None
                and not category.permissions_for(self.course).view_channel
            ):
                self.warnings.append(
                    "category.question exists but currently denies the provisioning bot; "
                    "owner repair is required before its three forums can be created."
                )
                continue
            overwrites = desired_category_overwrites(spec.key, **role_args)
            if category is None:
                category = await retry(
                    lambda spec=spec: self.guild.create_category(spec.name, reason=REASON),
                    label=f"create category {spec.name}",
                )
                self.store.set(spec.key, category.id, "category", category.name)
                self.operations.record("created", spec.key, category.id)
            await self.ensure_overwrites(category, overwrites, spec.key)
            self.categories[spec.key] = category

    async def ensure_overwrites(
        self,
        channel: discord.abc.GuildChannel,
        desired: dict[discord.Role | discord.Member, discord.PermissionOverwrite],
        key: str,
    ) -> None:
        desired_ids = {target.id for target in desired}
        course_target_ids = {self.course.id, self.course.top_role.id}
        if not desired_ids.intersection(course_target_ids):
            for target in list(channel.overwrites):
                if target.id in course_target_ids:
                    await retry(
                        lambda target=target: channel.set_permissions(
                            target, overwrite=None, reason=REASON
                        ),
                        label=f"remove inherited course overwrite {key}:{target.id}",
                    )
                    self.operations.record("updated", f"{key}.permission.remove_course", channel.id)
        ordered = sorted(
            desired.items(),
            key=lambda item: (
                0
                if item[0].id in {self.course.id, self.course.top_role.id}
                else 3
                if item[0].id == self.guild.default_role.id
                else 2
                if item[0].id == self.dump.top_role.id
                else 1
            ),
        )
        for target, overwrite in ordered:
            if channel.overwrites_for(target).pair() == overwrite.pair():
                continue
            try:
                await retry(
                    lambda target=target, overwrite=overwrite: channel.set_permissions(
                        target, overwrite=overwrite, reason=REASON
                    ),
                    label=f"set overwrite {key}:{target.id}",
                )
            except discord.Forbidden as exc:
                if target.id != self.dump.top_role.id:
                    raise ProvisioningError(
                        f"cannot set overwrite {key} for target {target.id}"
                    ) from exc
                self.warnings.append(
                    "Discord rejected dump_bot permission overwrites because both managed bot "
                    "roles have the same immutable position. dump_bot must remain offline until "
                    "the Guild owner moves its role below DC-Calculus-Manager."
                )
                continue
            self.operations.record("updated", f"{key}.permission.{target.id}", channel.id)
        for target in list(channel.overwrites):
            if target.id not in desired_ids:
                await retry(
                    lambda target=target: delete_permission_overwrite(channel, target),
                    label=f"remove stale overwrite {key}:{target.id}",
                )
                self.operations.record("updated", f"{key}.permission.remove", channel.id)

    async def ensure_channels(self) -> None:
        role_args = {
            "everyone": self.guild.default_role,
            "admin": self.roles["role.admin"],
            "staff": self.roles["role.staff"],
            "verified": self.roles["role.verified_member"],
            "guest": self.roles["role.guest"],
            "course": self.course.top_role,
            "dump": self.dump.top_role,
        }
        expected_types: dict[str, type[discord.abc.GuildChannel]] = {
            "text": discord.TextChannel,
            "forum": discord.ForumChannel,
            "voice": discord.VoiceChannel,
        }
        for spec in CHANNELS:
            if spec.category_key not in self.categories:
                self.warnings.append(
                    f"{spec.key} is pending because {spec.category_key} is inaccessible."
                )
                continue
            expected = expected_types[spec.kind]
            channel = await self.resolve_channel(spec.key, spec.name, expected)
            category = self.categories[spec.category_key]
            overwrites = desired_overwrites(spec, **role_args)
            if channel is None:
                if spec.kind == "text":
                    channel = await retry(
                        lambda spec=spec, category=category: self.guild.create_text_channel(
                            spec.name,
                            category=category,
                            topic=spec.topic,
                            reason=REASON,
                        ),
                        label=f"create text {spec.name}",
                    )
                elif spec.kind == "forum":
                    channel = await retry(
                        lambda spec=spec, category=category: self.guild.create_forum(
                            spec.name,
                            category=category,
                            topic=spec.topic or "",
                            default_auto_archive_duration=10080,
                            reason=REASON,
                        ),
                        label=f"create forum {spec.name}",
                    )
                else:
                    channel = await retry(
                        lambda spec=spec, category=category: self.guild.create_voice_channel(
                            spec.name,
                            category=category,
                            reason=REASON,
                        ),
                        label=f"create voice {spec.name}",
                    )
                self.store.set(spec.key, channel.id, spec.kind, channel.name)
                self.operations.record("created", spec.key, channel.id)
            else:
                changes: dict[str, object] = {}
                if channel.name != spec.name:
                    changes["name"] = spec.name
                if channel.category_id != category.id:
                    changes["category"] = category
                if (
                    isinstance(channel, (discord.TextChannel, discord.ForumChannel))
                    and channel.topic != spec.topic
                ):
                    changes["topic"] = spec.topic
                if (
                    isinstance(channel, discord.ForumChannel)
                    and channel.default_auto_archive_duration != 10080
                ):
                    changes["default_auto_archive_duration"] = 10080
                if changes:
                    changes["reason"] = REASON
                    await retry(
                        lambda channel=channel, changes=changes: channel.edit(**changes),
                        label=f"edit channel {spec.name}",
                    )
                    self.operations.record("updated", spec.key, channel.id)
            await self.ensure_overwrites(channel, overwrites, spec.key)
            self.channels[spec.key] = channel

    async def plan_private_entry(self) -> dict[str, object]:
        """Plan the allowlisted entry change without mutating Discord or local mapping."""

        adoptions = await self.resolve_private_entry_context(persist_adoptions=False)
        spec = next(item for item in CHANNELS if item.key == "channel.private_support_entry")
        category = self.categories["category.private_support"]
        channel = self.channels.get(spec.key)
        actions: list[str] = []
        if channel is None:
            actions.append("CREATE_CHANNEL")
            actions.extend(("SET_EXACT_OVERWRITES", "CREATE_AND_PIN_INSTRUCTION"))
        else:
            desired = self.private_entry_overwrites(spec)
            if channel.category_id != category.id:
                actions.append("MOVE_TO_PRIVATE_SUPPORT_CATEGORY")
            if channel.topic != spec.topic:
                actions.append("UPDATE_TOPIC")
            if overwrite_signature(channel.overwrites) != overwrite_signature(desired):
                actions.append("SET_EXACT_OVERWRITES")

            message_id = self.store.get_id("message.private_support_entry")
            if message_id is None:
                actions.append("CREATE_AND_PIN_INSTRUCTION")
            else:
                try:
                    message = await channel.fetch_message(message_id)
                except discord.NotFound:
                    actions.append("RECREATE_AND_PIN_INSTRUCTION")
                except discord.HTTPException as exc:
                    raise ProvisioningError(
                        f"cannot inspect mapped Private Support entry message: {exc}"
                    ) from exc
                else:
                    if message.content != PRIVATE_SUPPORT_ENTRY_CONTENT:
                        actions.append("UPDATE_INSTRUCTION")
                    if not message.pinned:
                        actions.append("PIN_INSTRUCTION")

        return {
            "ok": True,
            "target": spec.key,
            "discord_mutations": list(dict.fromkeys(actions)),
            "mapping_adoptions": adoptions,
            "unrelated_drift": self.unrelated_mapping_drift(),
            "category_action": "PRESERVE_EXISTING",
            "dynamic_case_channels_action": "PRESERVE_EXISTING",
            "other_resources_action": "REPORT_ONLY",
        }

    async def ensure_private_entry_seed(self) -> None:
        channel = self.channels["channel.private_support_entry"]
        assert isinstance(channel, discord.TextChannel)
        message_id = self.store.get_id("message.private_support_entry")
        message: discord.Message | None = None
        if message_id is not None:
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                self.store.remove("message.private_support_entry")
            except discord.HTTPException as exc:
                raise ProvisioningError(
                    f"cannot inspect mapped Private Support entry message: {exc}"
                ) from exc
        if message is None:
            message = await retry(
                lambda: channel.send(
                    PRIVATE_SUPPORT_ENTRY_CONTENT,
                    allowed_mentions=discord.AllowedMentions.none(),
                ),
                label="create Private Support entry message",
            )
            self.store.set(
                "message.private_support_entry", message.id, "message", "private-support-entry"
            )
            self.operations.record("created", "message.private_support_entry", message.id)
        elif message.content != PRIVATE_SUPPORT_ENTRY_CONTENT:
            await retry(
                lambda: message.edit(content=PRIVATE_SUPPORT_ENTRY_CONTENT),
                label="edit Private Support entry message",
            )
            self.operations.record("updated", "message.private_support_entry", message.id)
        if not message.pinned:
            await retry(
                lambda: message.pin(reason=REASON),
                label="pin Private Support entry message",
            )
            self.operations.record("updated", "message.private_support_entry.pin", message.id)

    def private_entry_overwrites(
        self, spec: ChannelSpec
    ) -> dict[discord.Role | discord.Member, discord.PermissionOverwrite]:
        desired = desired_overwrites(
            spec,
            everyone=self.guild.default_role,
            admin=self.roles["role.admin"],
            staff=self.roles["role.staff"],
            verified=self.roles["role.verified_member"],
            guest=self.roles["role.guest"],
            course=self.course,
            dump=self.dump.top_role,
        )
        # Discord-managed integration roles cannot be edited by their own bot.
        # Preserve the category's already-verified Course Manager role boundary,
        # then use a direct member overwrite for the entry-only capabilities.
        desired[self.course.top_role] = _overwrite(**COURSE_CASE)
        return desired

    def update_private_entry_runtime_config(self) -> None:
        channel_id = self.channels["channel.private_support_entry"].id
        with sqlite3.connect(self.database_path) as db:
            before_row = db.execute(
                "SELECT value FROM runtime_config WHERE key = ?",
                ("private_support_entry_channel_id",),
            ).fetchone()
            before = None if before_row is None else str(before_row[0])
            db.execute(
                """
                INSERT INTO runtime_config(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE
                SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (
                    "private_support_entry_channel_id",
                    str(channel_id),
                    datetime.now(UTC).isoformat(),
                ),
            )
            db.commit()
        if before != str(channel_id):
            self.operations.record("updated", "runtime_config.private_support_entry_channel_id")

    async def private_entry_errors(self) -> list[str]:
        errors: list[str] = []
        category = self.categories.get("category.private_support")
        channel = self.channels.get("channel.private_support_entry")
        if not isinstance(category, discord.CategoryChannel):
            return ["category.private_support: missing category"]
        if not isinstance(channel, discord.TextChannel):
            return ["channel.private_support_entry: missing or wrong type"]
        if channel.category_id != category.id:
            errors.append("channel.private_support_entry: wrong category")

        for role in (self.roles.get("role.verified_member"), self.roles.get("role.guest")):
            if role is None:
                errors.append("Private Support entry member role mapping is incomplete")
                continue
            entry = channel.permissions_for(role)
            if not (
                entry.view_channel and entry.read_message_history and entry.use_application_commands
            ):
                errors.append(f"{role.name} cannot use the Private Support entry")
            if any(
                (
                    entry.send_messages,
                    entry.send_messages_in_threads,
                    entry.create_public_threads,
                    entry.create_private_threads,
                    entry.attach_files,
                )
            ):
                errors.append(f"{role.name} can post content in the Private Support entry")

        if channel.permissions_for(self.guild.default_role).view_channel:
            errors.append("@everyone can see the Private Support entry without a course role")
        for role in (
            self.roles.get("role.staff"),
            self.roles.get("role.admin"),
            self.course,
        ):
            if role is None:
                errors.append("Private Support entry staff role mapping is incomplete")
                continue
            entry = channel.permissions_for(role)
            if not (
                entry.view_channel
                and entry.read_message_history
                and entry.send_messages
                and entry.manage_messages
            ):
                errors.append(f"{role.name} cannot manage the Private Support entry")
        if channel.permissions_for(self.dump).view_channel:
            errors.append("dump_bot can see the Private Support entry")

        entry_message_id = self.store.get_id("message.private_support_entry")
        if entry_message_id is None:
            errors.append("Private Support entry message mapping is incomplete")
        else:
            try:
                entry_message = await channel.fetch_message(entry_message_id)
            except (discord.NotFound, discord.HTTPException):
                errors.append("Private Support entry message is unavailable")
            else:
                if entry_message.content != PRIVATE_SUPPORT_ENTRY_CONTENT:
                    errors.append("Private Support entry message content drifted")
                if not entry_message.pinned:
                    errors.append("Private Support entry message is not pinned")
        return errors

    async def ensure_private_entry(self) -> dict[str, object]:
        """Apply only the allowlisted permanent Private Support entry resource."""

        before_plan = await self.plan_private_entry()
        await self.resolve_private_entry_context(persist_adoptions=True)
        spec = next(item for item in CHANNELS if item.key == "channel.private_support_entry")
        category = self.categories["category.private_support"]
        channel = self.channels.get(spec.key)
        created_by_this_apply = False
        if channel is None:
            channel = await retry(
                lambda: self.guild.create_text_channel(
                    spec.name,
                    category=category,
                    topic=spec.topic,
                    reason=REASON,
                ),
                label=f"create text {spec.name}",
            )
            self.store.set(spec.key, channel.id, spec.kind, channel.name)
            self.operations.record("created", spec.key, channel.id)
            self.channels[spec.key] = channel
            created_by_this_apply = True
        else:
            changes: dict[str, object] = {}
            if channel.category_id != category.id:
                changes["category"] = category
            if channel.topic != spec.topic:
                changes["topic"] = spec.topic
            if changes:
                changes["reason"] = REASON
                await retry(
                    lambda: channel.edit(**changes),
                    label=f"edit channel {spec.name}",
                )
                self.operations.record("updated", spec.key, channel.id)

        try:
            overwrites = self.private_entry_overwrites(spec)
            await self.ensure_overwrites(channel, overwrites, spec.key)
            await self.ensure_private_entry_seed()
            errors = await self.private_entry_errors()
            if errors:
                raise ProvisioningError("Private Support entry verify failed: " + "; ".join(errors))
        except BaseException:
            if created_by_this_apply:
                await retry(
                    lambda: channel.delete(reason=f"{REASON} rollback"),
                    label="rollback newly created Private Support entry",
                )
                self.store.remove("message.private_support_entry")
                self.store.remove(spec.key)
                self.operations.record("rolled_back", spec.key, channel.id)
                self.channels.pop(spec.key, None)
            raise
        self.update_private_entry_runtime_config()
        result = {
            "ok": not errors,
            "target": spec.key,
            "mutations": self.operations.mutations,
            "actions": self.operations.actions,
            "errors": errors,
            "unrelated_drift": before_plan["unrelated_drift"],
            "category_action": "PRESERVED_EXISTING",
            "dynamic_case_channels_action": "PRESERVED_EXISTING",
            "other_resources_action": "REPORTED_ONLY",
            "run_dir": str(self.run_dir),
            "mapping": str(self.store.path),
        }
        json_dump(self.run_dir / "verify-private-entry.json", result)
        self.operations.record("verified", spec.key, channel.id)
        return result

    async def cleanup_partial_channels(self) -> None:
        if self.store.get_id("message.welcome") or self.store.get_id("thread.server_guidelines"):
            return
        for spec in CHANNELS:
            mapped = self.store.get_id(spec.key)
            channel = self.guild.get_channel(mapped) if mapped else None
            if channel is None or self.course not in channel.overwrites:
                continue
            await retry(
                lambda channel=channel: channel.delete(reason=REASON),
                label=f"replace partial channel {spec.key}",
            )
            self.store.remove(spec.key)
            self.operations.record("deleted", f"partial.{spec.key}", channel.id)

    async def enforce_bot_boundaries(self) -> None:
        # The integration roles are Discord-managed and cannot be edited by a bot.
        # Member overwrites enforce the approved effective boundary on every channel,
        # including pre-existing out-of-scope channels that are deliberately preserved.
        managed_ids = {
            int(item["id"])
            for item in self.store.resources.values()
            if int(item["id"]) > 0 and item.get("kind") != "metadata"
        }
        for channel in self.guild.channels:
            if channel.id in managed_ids:
                continue
            dump_overwrite = channel.overwrites_for(self.dump.top_role)
            for name, value in DUMP_GLOBAL_DENY.items():
                setattr(dump_overwrite, name, value)
            if channel.overwrites_for(self.dump.top_role).pair() != dump_overwrite.pair():
                try:
                    await retry(
                        lambda channel=channel, overwrite=dump_overwrite: channel.set_permissions(
                            self.dump.top_role, overwrite=overwrite, reason=REASON
                        ),
                        label=f"restrict dump bot in {channel.name}",
                    )
                    self.operations.record("updated", f"boundary.dump.{channel.id}", channel.id)
                except discord.Forbidden:
                    self.warnings.append(
                        "dump_bot global read-only boundary is pending the owner role move."
                    )

    async def ensure_seed_content(self) -> None:
        welcome = self.channels["channel.welcome"]
        assert isinstance(welcome, discord.TextChannel)
        welcome_id = self.store.get_id("message.welcome")
        message: discord.Message | None = None
        if welcome_id is not None:
            try:
                message = await welcome.fetch_message(welcome_id)
            except discord.NotFound:
                self.store.remove("message.welcome")
            except discord.HTTPException as exc:
                raise ProvisioningError(f"cannot inspect mapped welcome message: {exc}") from exc
        if message is None:
            message = await retry(
                lambda: welcome.send(
                    WELCOME_CONTENT, allowed_mentions=discord.AllowedMentions.none()
                ),
                label="create welcome message",
            )
            self.store.set("message.welcome", message.id, "message", "welcome")
            self.operations.record("created", "message.welcome", message.id)
        elif message.content != WELCOME_CONTENT:
            await retry(
                lambda: message.edit(content=WELCOME_CONTENT),
                label="edit welcome message",
            )
            self.operations.record("updated", "message.welcome", message.id)

        announcements = self.channels["forum.announcements"]
        assert isinstance(announcements, discord.ForumChannel)
        thread_id = self.store.get_id("thread.server_guidelines")
        thread: discord.Thread | None = None
        if thread_id is not None:
            candidate = self.guild.get_thread(thread_id)
            if candidate is None:
                try:
                    fetched = await self.guild.fetch_channel(thread_id)
                    candidate = fetched if isinstance(fetched, discord.Thread) else None
                except discord.NotFound:
                    self.store.remove("thread.server_guidelines")
                except discord.HTTPException as exc:
                    raise ProvisioningError(f"cannot inspect guidelines thread: {exc}") from exc
            thread = candidate
        if thread is None:
            created = await retry(
                lambda: announcements.create_thread(
                    name=GUIDELINES_TITLE,
                    content=GUIDELINES_CONTENT,
                    auto_archive_duration=10080,
                    allowed_mentions=discord.AllowedMentions.none(),
                    reason=REASON,
                ),
                label="create guidelines forum post",
            )
            thread = created.thread
            self.store.set("thread.server_guidelines", thread.id, "thread", GUIDELINES_TITLE)
            self.store.set(
                "message.server_guidelines",
                created.message.id,
                "message",
                GUIDELINES_TITLE,
            )
            self.operations.record("created", "thread.server_guidelines", thread.id)
        else:
            message_id = self.store.get_id("message.server_guidelines") or thread.id
            try:
                starter = await thread.fetch_message(message_id)
            except discord.NotFound as exc:
                raise ProvisioningError("mapped guidelines starter message is missing") from exc
            if thread.name != GUIDELINES_TITLE:
                await retry(
                    lambda: thread.edit(name=GUIDELINES_TITLE, reason=REASON),
                    label="rename guidelines thread",
                )
                self.operations.record("updated", "thread.server_guidelines", thread.id)
            if starter.content != GUIDELINES_CONTENT:
                await retry(
                    lambda: starter.edit(content=GUIDELINES_CONTENT),
                    label="edit guidelines content",
                )
                self.operations.record("updated", "message.server_guidelines", starter.id)
            self.store.set("message.server_guidelines", starter.id, "message", GUIDELINES_TITLE)

        private_entry = self.channels["channel.private_support_entry"]
        assert isinstance(private_entry, discord.TextChannel)
        entry_message_id = self.store.get_id("message.private_support_entry")
        entry_message: discord.Message | None = None
        if entry_message_id is not None:
            try:
                entry_message = await private_entry.fetch_message(entry_message_id)
            except discord.NotFound:
                self.store.remove("message.private_support_entry")
            except discord.HTTPException as exc:
                raise ProvisioningError(
                    f"cannot inspect mapped Private Support entry message: {exc}"
                ) from exc
        if entry_message is None:
            entry_message = await retry(
                lambda: private_entry.send(
                    PRIVATE_SUPPORT_ENTRY_CONTENT,
                    allowed_mentions=discord.AllowedMentions.none(),
                ),
                label="create Private Support entry message",
            )
            self.store.set(
                "message.private_support_entry",
                entry_message.id,
                "message",
                "Private Support entry",
            )
            self.operations.record("created", "message.private_support_entry", entry_message.id)
        elif entry_message.content != PRIVATE_SUPPORT_ENTRY_CONTENT:
            await retry(
                lambda: entry_message.edit(content=PRIVATE_SUPPORT_ENTRY_CONTENT),
                label="edit Private Support entry message",
            )
            self.operations.record("updated", "message.private_support_entry", entry_message.id)
        if not entry_message.pinned:
            await retry(
                lambda: entry_message.pin(reason=REASON),
                label="pin Private Support entry message",
            )
            self.operations.record("updated", "message.private_support_entry.pin", entry_message.id)

    def update_runtime_config(self) -> None:
        managed_ids = [
            self.channels[key].id for key in sorted(MANAGED_FORUM_KEYS) if key in self.channels
        ]
        values = {
            "verified_member_role_id": self.roles["role.verified_member"].id,
            "verified_student_role_id": self.roles["role.verified_member"].id,
            "guest_role_id": self.roles["role.guest"].id,
            "course_role_id": self.roles["role.verified_member"].id,
            "visitor_role_id": self.roles["role.guest"].id,
            "ta_role_id": self.roles["role.staff"].id,
            "professor_role_id": self.roles["role.staff"].id,
            "bot_control_channel_id": self.channels["channel.bot_control"].id,
            "system_log_channel_id": self.channels["channel.system_log"].id,
            "managed_forum_ids": json.dumps(managed_ids),
            "private_support_category_id": self.categories["category.private_support"].id,
            "private_support_entry_channel_id": self.channels["channel.private_support_entry"].id,
            "discord_provisioning_version": "2026-07-30",
        }
        values.update(
            {
                f"class_role_{number:02d}": self.roles[f"role.class_{number:02d}"].id
                for number in range(1, 17)
            }
        )
        if "forum.math_questions" in self.channels:
            values["public_forum_channel_id"] = self.channels["forum.math_questions"].id
        with sqlite3.connect(self.database_path) as db:
            before = {
                key: value
                for key, value in db.execute("SELECT key, value FROM runtime_config").fetchall()
            }
            for key, value in values.items():
                db.execute(
                    """
                    INSERT INTO runtime_config(key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE
                    SET value=excluded.value, updated_at=excluded.updated_at
                    """,
                    (key, str(value), datetime.now(UTC).isoformat()),
                )
            db.commit()
        if any(str(before.get(key)) != str(value) for key, value in values.items()):
            self.operations.record("updated", "runtime_config")

    def _perms(self, key: str, target: discord.Role | discord.Member) -> discord.Permissions:
        channel = self.channels.get(key) or self.categories.get(key)
        if channel is None:
            raise ProvisioningError(f"unresolved permission target: {key}")
        return channel.permissions_for(target)

    async def verify(self) -> dict[str, object]:
        errors: list[str] = []
        warnings = list(dict.fromkeys(self.warnings))

        for spec in ROLES:
            mapped = self.store.get_id(spec.key)
            role = self.guild.get_role(mapped) if mapped else None
            if not isinstance(role, discord.Role) or role.name != spec.name:
                errors.append(f"{spec.key}: missing or wrong role")

        expected_types: dict[str, type[discord.abc.GuildChannel]] = {
            "text": discord.TextChannel,
            "forum": discord.ForumChannel,
            "voice": discord.VoiceChannel,
        }
        for spec in CHANNELS:
            mapped = self.store.get_id(spec.key)
            channel = self.guild.get_channel(mapped) if mapped else None
            if not isinstance(channel, expected_types[spec.kind]):
                errors.append(f"{spec.key}: missing or wrong type")
                continue
            if channel.category_id != self.store.get_id(spec.category_key):
                errors.append(f"{spec.key}: wrong category")
        for spec in CATEGORIES:
            mapped = self.store.get_id(spec.key)
            channel = self.guild.get_channel(mapped) if mapped else None
            if not isinstance(channel, discord.CategoryChannel):
                errors.append(f"{spec.key}: missing category")

        errors.extend(
            class_resource_errors(
                [role.name for role in self.guild.roles],
                [channel.name for channel in self.guild.channels],
            )
        )

        managed = set(self.store.resources.get("forum.managed_case", {}).get("keys", []))
        if managed and managed != MANAGED_FORUM_KEYS:
            errors.append("stored managed_case forum flags drifted")

        forbidden_course = {
            "administrator": self.course.guild_permissions.administrator,
            "manage_guild": self.course.guild_permissions.manage_guild,
            "kick_members": self.course.guild_permissions.kick_members,
            "ban_members": self.course.guild_permissions.ban_members,
            "manage_webhooks": self.course.guild_permissions.manage_webhooks,
        }
        if any(forbidden_course.values()):
            errors.append(f"course_assistant has forbidden Guild permission: {forbidden_course}")
        for channel in self.guild.channels:
            if (
                isinstance(channel, (discord.TextChannel, discord.ForumChannel))
                and channel.permissions_for(self.course).mention_everyone
            ):
                errors.append(f"course_assistant can Mention Everyone in {channel.name}")
            if isinstance(channel, discord.CategoryChannel):
                continue
            dump_perms = channel.permissions_for(self.dump)
            if any(
                (
                    dump_perms.send_messages,
                    dump_perms.send_messages_in_threads,
                    dump_perms.create_public_threads,
                    dump_perms.create_private_threads,
                    dump_perms.manage_threads,
                    dump_perms.manage_channels,
                    dump_perms.manage_messages,
                    dump_perms.attach_files,
                )
            ):
                errors.append(f"dump_bot has write/manage permission in {channel.name}")

        everyone = self.guild.default_role
        verified = self.roles.get("role.verified_member")
        guest = self.roles.get("role.guest")
        staff = self.roles.get("role.staff")
        admin = self.roles.get("role.admin")
        if not all((verified, guest, staff, admin)):
            errors.append("one or more managed roles are unavailable")
        else:
            welcome_everyone = self._perms("channel.welcome", everyone)
            if not (
                welcome_everyone.view_channel
                and welcome_everyone.read_message_history
                and welcome_everyone.send_messages
            ):
                errors.append("@everyone cannot read/write welcome")
            for role in (verified, guest):
                for key in MANAGED_FORUM_KEYS:
                    if key not in self.channels:
                        continue
                    perms = self._perms(key, role)
                    if not (
                        perms.view_channel
                        and perms.create_public_threads
                        and perms.send_messages_in_threads
                        and perms.attach_files
                        and perms.embed_links
                    ):
                        errors.append(f"{role.name} cannot fully use {key}")
                for key in ("channel.zh_chat", "channel.en_chat"):
                    perms = self._perms(key, role)
                    if not (perms.view_channel and perms.send_messages and perms.attach_files):
                        errors.append(f"{role.name} cannot fully use {key}")
                for key in ("voice.office_hours", "voice.study_room"):
                    perms = self._perms(key, role)
                    if not (perms.view_channel and perms.connect and perms.speak and perms.stream):
                        errors.append(f"{role.name} cannot fully use {key}")
                resource = self._perms("forum.course_resources", role)
                if not (resource.view_channel and resource.create_public_threads):
                    errors.append(f"{role.name} cannot create Course Resources posts")
                for key in ("forum.announcements", "forum.faq"):
                    perms = self._perms(key, role)
                    if not perms.view_channel or perms.create_public_threads:
                        errors.append(f"{role.name} has wrong read-only policy in {key}")
                if self._perms("channel.staff_chat", role).view_channel:
                    errors.append(f"{role.name} can see Staff")
            if self._perms("category.private_support", everyone).view_channel:
                errors.append("@everyone can see Private Support")

        errors.extend(await self.private_entry_errors())

        for key in MANAGED_FORUM_KEYS:
            if key not in self.channels:
                continue
            perms = self._perms(key, self.dump)
            if not (perms.view_channel and perms.read_message_history):
                errors.append(f"dump_bot cannot read {key}")
            if perms.send_messages or perms.send_messages_in_threads:
                errors.append(f"dump_bot can write {key}")
            course = self._perms(key, self.course)
            if not (
                course.view_channel
                and course.send_messages_in_threads
                and course.read_message_history
                and course.manage_threads
            ):
                errors.append(f"course_assistant cannot manage {key}")

        hierarchy = [
            self.guild.get_role(self.store.get_id(key) or 0)
            for key in (
                "role.admin",
                "role.staff",
                "role.course_assistant",
                "role.verified_member",
                "role.guest",
                "role.dump_bot",
            )
        ]
        if all(isinstance(role, discord.Role) for role in hierarchy):
            desired_hierarchy = all(
                hierarchy[index] > hierarchy[index + 1]  # type: ignore[operator]
                for index in range(len(hierarchy) - 1)
            )
            if not desired_hierarchy:
                warnings.append(
                    "Role hierarchy is provisioned safely below the course bot but still needs "
                    "the Guild owner to move Admin and Staff / TA above DC-Calculus-Manager."
                )
        else:
            errors.append("role hierarchy mapping is incomplete")

        result = {
            "ok": not errors,
            "checked_at": datetime.now(UTC).isoformat(),
            "guild_id": self.guild.id,
            "errors": errors,
            "warnings": list(dict.fromkeys(warnings)),
            "managed_case_forums": sorted(MANAGED_FORUM_KEYS),
            "resource_count": len(self.store.resources),
        }
        json_dump(self.run_dir / "verify.json", result)
        self.operations.record("verified", "guild", self.guild.id)
        return result

    async def apply(self, *, reset_lab: bool) -> dict[str, object]:
        json_dump(self.run_dir / "inventory-before.json", inventory_document(self.guild))
        self.operations.record("inventory", "before", self.guild.id)
        if reset_lab:
            await self.reset_legacy_lab()
        await self.ensure_roles()
        await self.ensure_categories()
        await self.cleanup_partial_channels()
        await self.ensure_channels()
        self.store.resources["forum.managed_case"] = {
            "id": 0,
            "kind": "metadata",
            "name": "managed_case",
            "keys": sorted(MANAGED_FORUM_KEYS),
        }
        self.store.save()
        await self.enforce_bot_boundaries()
        await self.ensure_seed_content()
        self.update_runtime_config()
        json_dump(self.run_dir / "inventory-after.json", inventory_document(self.guild))
        self.operations.record("inventory", "after", self.guild.id)
        verify = await self.verify()
        return {
            "ok": bool(verify["ok"]),
            "mutations": self.operations.mutations,
            "actions": self.operations.actions,
            "warnings": verify["warnings"],
            "errors": verify["errors"],
            "run_dir": str(self.run_dir),
            "mapping": str(self.store.path),
        }


class ProvisioningClient(discord.Client):
    def __init__(
        self,
        *,
        command: str,
        requested_guild_id: int,
        reset_lab: bool,
        env: dict[str, str | None],
        map_file: Path,
        run_dir: Path,
    ) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(intents=intents)
        self.command = command
        self.requested_guild_id = requested_guild_id
        self.reset_lab = reset_lab
        self.env = env
        self.map_file = map_file
        self.run_dir = run_dir
        self.result: dict[str, object] | None = None
        self.failure: BaseException | None = None
        self._executed = False

    async def on_ready(self) -> None:
        if self._executed:
            return
        self._executed = True
        try:
            connected = [guild.id for guild in self.guilds]
            if connected != [self.requested_guild_id]:
                raise ProvisioningError(
                    f"Guild guard failed: expected {self.requested_guild_id}, connected {connected}"
                )
            guild = self.get_guild(self.requested_guild_id)
            if guild is None:
                raise ProvisioningError("allowlisted Guild is unavailable")
            store = ResourceStore(self.map_file, guild.id)
            operations = OperationLog(self.run_dir / "operations.jsonl")
            provisioner = LiveProvisioner(
                guild,
                env=self.env,
                store=store,
                operations=operations,
                run_dir=self.run_dir,
            )
            await provisioner.initialize()
            if self.command == "inventory":
                path = self.run_dir / "inventory.json"
                json_dump(path, inventory_document(guild))
                operations.record("inventory", "guild", guild.id)
                self.result = {"ok": True, "inventory": str(path)}
            elif self.command == "plan-private-entry":
                inventory_path = self.run_dir / "inventory.json"
                json_dump(inventory_path, inventory_document(guild))
                operations.record("inventory", "guild", guild.id)
                self.result = await provisioner.plan_private_entry()
                self.result["inventory"] = str(inventory_path)
                self.result["discord_mutation_executed"] = False
                json_dump(self.run_dir / "plan-private-entry.json", self.result)
            elif self.command == "ensure-private-entry":
                before_path = self.run_dir / "inventory-before.json"
                json_dump(before_path, inventory_document(guild))
                operations.record("inventory", "before", guild.id)
                self.result = await provisioner.ensure_private_entry()
                after_path = self.run_dir / "inventory-after.json"
                json_dump(after_path, inventory_document(guild))
                operations.record("inventory", "after", guild.id)
                self.result["inventory_before"] = str(before_path)
                self.result["inventory_after"] = str(after_path)
            elif self.command == "verify":
                for spec in ROLES:
                    role = await provisioner.resolve_role(spec.key, spec.name)
                    if role is not None:
                        provisioner.roles[spec.key] = role
                for spec in CATEGORIES:
                    channel = await provisioner.resolve_channel(
                        spec.key, spec.name, discord.CategoryChannel
                    )
                    if isinstance(channel, discord.CategoryChannel):
                        provisioner.categories[spec.key] = channel
                expected = {
                    "text": discord.TextChannel,
                    "forum": discord.ForumChannel,
                    "voice": discord.VoiceChannel,
                }
                for spec in CHANNELS:
                    channel = await provisioner.resolve_channel(
                        spec.key, spec.name, expected[spec.kind]
                    )
                    if channel is not None:
                        provisioner.channels[spec.key] = channel
                self.result = await provisioner.verify()
            else:
                self.result = await provisioner.apply(reset_lab=self.reset_lab)
        except BaseException as exc:
            self.failure = exc
        finally:
            await self.close()


def load_environment(path: Path) -> dict[str, str | None]:
    if not path.is_file():
        raise ProvisioningError(f"environment file is missing: {path}")
    env = dict(dotenv_values(path))
    env["_ENV_FILE_DIR"] = str(path.resolve().parent)
    required = {
        "TEST_GUILD_ID",
        "COURSE_ASSISTANT_TOKEN",
        "COURSE_ASSISTANT_CLIENT_ID",
        "DUMP_BOT_CLIENT_ID",
    }
    missing = sorted(key for key in required if not str(env.get(key) or "").strip())
    if missing:
        raise ProvisioningError(f"missing environment keys: {', '.join(missing)}")
    return env


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision or verify the allowlisted Discord test Guild"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "apply",
        "verify",
        "inventory",
        "plan-private-entry",
        "ensure-private-entry",
    ):
        child = subparsers.add_parser(command)
        child.add_argument("--guild-id", required=True, type=int)
        child.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
        child.add_argument("--mapping", type=Path, default=DEFAULT_MAP_FILE)
        if command == "apply":
            child.add_argument("--reset-lab", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    validate_spec()
    args = parse_args(argv)
    env = load_environment(args.env_file)
    allowlisted = int(str(env["TEST_GUILD_ID"]))
    if args.guild_id != allowlisted:
        raise SystemExit("refusing non-allowlisted Guild ID")
    run_dir = DEFAULT_ARTIFACT_ROOT / f"{utc_stamp()}-{args.command}"
    run_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(run_dir, 0o700)
    client = ProvisioningClient(
        command=args.command,
        requested_guild_id=args.guild_id,
        reset_lab=bool(getattr(args, "reset_lab", False)),
        env=env,
        map_file=args.mapping,
        run_dir=run_dir,
    )
    client.run(str(env["COURSE_ASSISTANT_TOKEN"]), log_handler=None)
    if client.failure is not None:
        error = {
            "ok": False,
            "error_type": type(client.failure).__name__,
            "error": str(client.failure),
            "run_dir": str(run_dir),
        }
        json_dump(run_dir / "failure.json", error)
        print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    assert client.result is not None
    print(json.dumps(client.result, ensure_ascii=False, indent=2))
    return 0 if bool(client.result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
