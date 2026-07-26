from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.discord_provisioning import (
    compute_diff,
    parse_fixture_document,
    print_plan,
    rollback_plan,
)

ROOT = Path(__file__).resolve().parents[2]


def fixture(name: str) -> dict[str, object]:
    value: object = json.loads(
        (ROOT / "fixtures/provisioning" / f"{name}-server.json").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_parse_validate_diff_print_and_rollback_are_deterministic() -> None:
    current = parse_fixture_document(fixture("current"))
    desired = parse_fixture_document(fixture("desired"))
    changes = compute_diff(current, desired)
    assert [change.resource_key for change in changes] == sorted(
        change.resource_key for change in changes
    )
    assert len(changes) == 5
    rendered = json.loads(print_plan(changes))
    assert rendered["dryRun"] is True
    assert rendered["fixtureOnly"] is True
    rollback = rollback_plan(changes)
    assert [change.resource_key for change in rollback] == [
        change.resource_key for change in reversed(changes)
    ]
    assert compute_diff(desired, current) == tuple(reversed(rollback))


def test_rejects_non_fixture_plan_and_excessive_bot_permissions() -> None:
    desired = fixture("desired")
    desired["fixtureOnly"] = False
    with pytest.raises(PermissionError):
        parse_fixture_document(desired)

    desired = fixture("desired")
    permissions = desired["botPermissions"]
    assert isinstance(permissions, list)
    permissions[0]["permissions"].append("ADMINISTRATOR")
    with pytest.raises(ValueError, match="unsupported bot permissions"):
        parse_fixture_document(desired)

    for permission in ("MANAGE_WEBHOOKS", "MENTION_EVERYONE"):
        desired = fixture("desired")
        bot_permissions = desired["botPermissions"]
        assert isinstance(bot_permissions, list)
        bot_permissions[0]["permissions"].append(permission)
        with pytest.raises(ValueError, match="unsupported bot permissions"):
            parse_fixture_document(desired)


def test_rejects_extra_resource_fields_and_nested_secrets() -> None:
    desired = fixture("desired")
    roles = desired["roles"]
    assert isinstance(roles, list)
    roles[0]["color"] = "red"
    with pytest.raises(ValueError, match="unexpected fields"):
        parse_fixture_document(desired)

    desired = fixture("desired")
    channels = desired["channels"]
    assert isinstance(channels, list)
    channels[0]["permissionOverwrites"][0]["botToken"] = "fixture-secret"
    with pytest.raises(ValueError, match="secret-shaped field"):
        parse_fixture_document(desired)


def test_tool_contains_no_apply_or_network_mode() -> None:
    source = (ROOT / "tools/discord_provisioning/cli.py").read_text(encoding="utf-8")
    assert "requests" not in source
    assert "discord.py" not in source
    assert "--apply" not in source
