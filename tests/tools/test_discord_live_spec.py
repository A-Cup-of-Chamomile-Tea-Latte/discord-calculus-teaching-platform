from __future__ import annotations

import re

from tools.discord_provisioning.live_spec import (
    CATEGORIES,
    CHANNELS,
    MANAGED_FORUM_KEYS,
    ROLES,
    validate_spec,
)


def test_live_spec_has_unique_logical_keys_and_supported_types() -> None:
    validate_spec()
    keys = [item.key for item in (*ROLES, *CATEGORIES, *CHANNELS)]
    assert len(keys) == len(set(keys))
    assert {channel.kind for channel in CHANNELS} == {"text", "forum", "voice"}


def test_only_approved_forums_enter_case_lifecycle() -> None:
    managed = {channel.key for channel in CHANNELS if channel.managed_case}
    assert managed == MANAGED_FORUM_KEYS
    assert all(channel.kind == "forum" for channel in CHANNELS if channel.managed_case)


def test_live_spec_contains_no_cxx_role_or_channel() -> None:
    names = [role.name for role in ROLES] + [channel.name for channel in CHANNELS]
    assert not any(re.fullmatch(r"C\d\d", name) for name in names)


def test_dump_and_course_bot_are_not_mutable_role_specs() -> None:
    names = {role.name for role in ROLES}
    assert "DC-Calculus-Manager" not in names
    assert "DC-Calculus-Archive" not in names
