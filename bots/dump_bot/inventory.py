"""Structure-only inventory capture from an injected fixture object."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol


class StructureInventorySource(Protocol):
    @property
    def fixture_only(self) -> bool: ...

    def read_structure(self) -> dict[str, Any]: ...


class FixtureStructureInventorySource:
    def __init__(self, inventory: dict[str, Any]) -> None:
        self._inventory = deepcopy(inventory)

    @property
    def fixture_only(self) -> bool:
        return True

    def read_structure(self) -> dict[str, Any]:
        return deepcopy(self._inventory)


class StructureInventoryService:
    """Reject any adapter that is not explicitly marked as fixture-only."""

    _required_fields = frozenset(
        {
            "schemaVersion",
            "inventoryId",
            "capturedAt",
            "fixtureOnly",
            "server",
            "categories",
            "channels",
            "roles",
            "permissionOverwrites",
            "forumTags",
            "threadCounts",
            "bots",
        }
    )
    _forbidden_fields = frozenset(
        {"messages", "messageBodies", "members", "memberList", "accessToken", "botToken"}
    )

    def capture(self, source: StructureInventorySource) -> dict[str, Any]:
        if not source.fixture_only:
            raise PermissionError("structure inventory is fixture-only")
        inventory = source.read_structure()
        if set(inventory) != self._required_fields or inventory.get("fixtureOnly") is not True:
            raise ValueError("fixture inventory has an unexpected top-level shape")
        self._reject_forbidden_fields(inventory)
        overwrites = inventory.get("permissionOverwrites")
        if not isinstance(overwrites, list) or any(
            not isinstance(item, dict) or item.get("targetType") != "ROLE" for item in overwrites
        ):
            raise ValueError("fixture inventory accepts role permission overwrites only")
        server = inventory.get("server")
        if not isinstance(server, dict) or "fixture" not in str(server.get("serverId", "")):
            raise ValueError("fixture inventory requires a visibly synthetic server ID")
        return inventory

    def _reject_forbidden_fields(self, value: object) -> None:
        if isinstance(value, dict):
            forbidden = self._forbidden_fields.intersection(value)
            if forbidden:
                raise ValueError(
                    f"structure inventory contains forbidden fields: {sorted(forbidden)}"
                )
            for child in value.values():
                self._reject_forbidden_fields(child)
        elif isinstance(value, list):
            for child in value:
                self._reject_forbidden_fields(child)
