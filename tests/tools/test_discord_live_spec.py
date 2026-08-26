from __future__ import annotations

import re

from tools.discord_provisioning.live_spec import (
    CATEGORIES,
    CHANNELS,
    MANAGED_FORUM_KEYS,
    ROLES,
    class_resource_errors,
    validate_spec,
)


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
