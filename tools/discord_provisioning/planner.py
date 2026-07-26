"""Pure planning functions: no Discord client, token, REST call, or mutation adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ChangeAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass(frozen=True)
class ProvisioningChange:
    action: ChangeAction
    resource_key: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action.value,
            "resourceKey": self.resource_key,
            "before": self.before,
            "after": self.after,
        }


_top_level = frozenset(
    {"fixtureOnly", "serverName", "roles", "categories", "channels", "botPermissions"}
)
_resource_collections = ("roles", "categories", "channels", "botPermissions")
_allowed_bot_permissions = frozenset(
    {
        "VIEW_CHANNEL",
        "READ_MESSAGE_HISTORY",
        "USE_APPLICATION_COMMANDS",
        "SEND_MESSAGES",
        "ATTACH_FILES",
    }
)
_allowed_channel_types = frozenset({"TEXT", "FORUM", "VOICE"})
_resource_shapes = {
    "roles": frozenset({"key", "name"}),
    "categories": frozenset({"key", "name"}),
    "channels": frozenset({"key", "name", "type", "parent", "permissionOverwrites"}),
    "botPermissions": frozenset({"key", "name", "permissions"}),
}
_secret_keys = frozenset(
    {
        "token",
        "bottoken",
        "accesstoken",
        "refreshtoken",
        "secret",
        "clientsecret",
        "password",
        "privatekey",
    }
)


def _reject_secrets(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).replace("_", "").lower()
            if normalized in _secret_keys:
                raise ValueError("provisioning fixture contains a secret-shaped field")
            _reject_secrets(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secrets(child)
    elif isinstance(value, str) and (
        value.startswith(("ghp_", "gho_", "Bot ")) or "PRIVATE KEY-----" in value
    ):
        raise ValueError("provisioning fixture contains a secret-shaped value")


def parse_fixture_document(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _top_level:
        raise ValueError("provisioning document has an unexpected shape")
    if value.get("fixtureOnly") is not True:
        raise PermissionError("provisioning planner accepts fixture-only documents")
    _reject_secrets(value)
    server_name = value.get("serverName")
    if not isinstance(server_name, str) or not server_name.startswith("Fixture "):
        raise ValueError("fixture serverName must start with 'Fixture '")
    result: dict[str, Any] = dict(value)
    observed: set[str] = set()
    category_keys: set[str] = set()
    role_keys: set[str] = set()
    for collection in _resource_collections:
        items = value.get(collection)
        if not isinstance(items, list):
            raise ValueError(f"{collection} must be an array")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"{collection} entries must be objects")
            if set(item) != _resource_shapes[collection]:
                raise ValueError(f"{collection} entry has unexpected fields")
            key = item.get("key")
            if not isinstance(key, str) or not key.startswith("fixture_"):
                raise ValueError("resource keys must use the fixture_ prefix")
            resource_key = f"{collection}:{key}"
            if resource_key in observed:
                raise ValueError(f"duplicate resource key: {resource_key}")
            observed.add(resource_key)
            if collection == "categories":
                category_keys.add(key)
            if collection == "roles":
                role_keys.add(key)
            if collection == "channels" and item.get("type") not in _allowed_channel_types:
                raise ValueError("unsupported channel type")
            if collection == "botPermissions":
                permissions = item.get("permissions")
                if not isinstance(permissions, list) or not all(
                    isinstance(permission, str) for permission in permissions
                ):
                    raise ValueError("bot permissions must be a string array")
                unsupported = set(permissions).difference(_allowed_bot_permissions)
                if unsupported:
                    raise ValueError(f"unsupported bot permissions: {sorted(unsupported)}")
    for channel in value["channels"]:
        assert isinstance(channel, dict)
        parent = channel.get("parent")
        if not isinstance(parent, str) or parent not in category_keys:
            raise ValueError("channel parent must reference a declared category")
        for overwrite in channel.get("permissionOverwrites", []):
            if (
                not isinstance(overwrite, dict)
                or set(overwrite) != {"roleKey", "allow", "deny"}
                or overwrite.get("roleKey") not in role_keys
            ):
                raise ValueError("permission overwrite must reference a declared role")
            for decision in ("allow", "deny"):
                permissions = overwrite[decision]
                if not isinstance(permissions, list) or not all(
                    isinstance(permission, str) for permission in permissions
                ):
                    raise ValueError("overwrite permissions must be string arrays")
    return result


def _flatten(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    flattened: dict[str, dict[str, Any]] = {}
    for collection in _resource_collections:
        for raw in document[collection]:
            item = dict(raw)
            flattened[f"{collection}:{item['key']}"] = item
    return flattened


def compute_diff(
    current: dict[str, Any], desired: dict[str, Any]
) -> tuple[ProvisioningChange, ...]:
    current_resources = _flatten(parse_fixture_document(current))
    desired_resources = _flatten(parse_fixture_document(desired))
    changes: list[ProvisioningChange] = []
    for key in sorted(current_resources.keys() | desired_resources.keys()):
        before = current_resources.get(key)
        after = desired_resources.get(key)
        if before == after:
            continue
        if before is None:
            action = ChangeAction.CREATE
        elif after is None:
            action = ChangeAction.DELETE
        else:
            action = ChangeAction.UPDATE
        changes.append(ProvisioningChange(action, key, before, after))
    return tuple(changes)


def rollback_plan(changes: tuple[ProvisioningChange, ...]) -> tuple[ProvisioningChange, ...]:
    reverse_action = {
        ChangeAction.CREATE: ChangeAction.DELETE,
        ChangeAction.DELETE: ChangeAction.CREATE,
        ChangeAction.UPDATE: ChangeAction.UPDATE,
    }
    return tuple(
        ProvisioningChange(
            reverse_action[change.action], change.resource_key, change.after, change.before
        )
        for change in reversed(changes)
    )


def print_plan(changes: tuple[ProvisioningChange, ...]) -> str:
    return json.dumps(
        {
            "dryRun": True,
            "fixtureOnly": True,
            "changeCount": len(changes),
            "changes": [change.to_dict() for change in changes],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
