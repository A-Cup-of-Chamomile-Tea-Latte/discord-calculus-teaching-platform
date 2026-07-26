"""Fixture adapter plus an intentionally unavailable credential-gated live boundary."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from bots.common.contracts import ContractRegistry
from bots.common.errors import (
    AuthorizationError,
    ContractValidationError,
    ProviderUnavailableError,
    ResourceNotFoundError,
)
from tools.case_id import validate_case_number
from tools.discord_export.models import ExportCase, MessagePage

DISCORD_ID_PATTERN = re.compile(r"^[0-9]{17,20}$")
ENV_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError(f"Fixture JSON is unreadable: {path.name}") from error


class FixtureExportAdapter:
    """Read immutable project fixtures; never mutates them or falls back to a network."""

    def __init__(self, fixture_root: Path, contracts: ContractRegistry) -> None:
        self._root = fixture_root.resolve()
        if not self._root.is_dir():
            raise ContractValidationError("Fixture root does not exist.")
        self._contracts = contracts
        self._cases = self._load_records("cases/cases.json", "case.schema.json")
        self._users = {
            str(item["userId"]): item
            for item in self._load_records("users/users.json", "user.schema.json")
        }
        memberships = self._load_records(
            "users/course-memberships.json", "course-membership.schema.json"
        )
        self._aliases = {
            str(item["userId"]): str(item["courseAlias"])
            for item in memberships
            if item["status"] == "ACTIVE"
        }
        self._messages = self._load_messages()

    def resolve_case(self, case_number_or_thread_id: str) -> ExportCase:
        candidate = case_number_or_thread_id.strip()
        if validate_case_number(candidate.upper()):
            normalized = candidate.upper()
            matches = [item for item in self._cases if item["caseNumber"] == normalized]
        elif DISCORD_ID_PATTERN.fullmatch(candidate):
            matches = [
                item
                for item in self._cases
                if isinstance(item.get("discordMapping"), dict)
                and item["discordMapping"].get("threadId") == candidate
            ]
        else:
            raise ValueError("Selection must be a case number or a 17–20 digit thread ID.")
        if len(matches) != 1:
            raise ResourceNotFoundError("The exportable general case was not found.")
        record = matches[0]
        mapping = record.get("discordMapping")
        if (
            record["caseType"] != "GENERAL"
            or record["caseNumber"] is None
            or not isinstance(mapping, dict)
            or not isinstance(mapping.get("threadId"), str)
        ):
            raise ResourceNotFoundError("The exportable general case was not found.")
        return ExportCase(record, mapping["threadId"])

    def fetch_page(
        self,
        case: ExportCase,
        *,
        after_message_id: str | None,
        limit: int,
    ) -> MessagePage:
        if not 1 <= limit <= 100:
            raise ValueError("Page limit must be between 1 and 100.")
        messages = self._messages.get(case.case_id, ())
        start = 0
        if after_message_id is not None:
            matching_positions = [
                index
                for index, item in enumerate(messages)
                if item["discordMessageId"] == after_message_id
                or item["messageId"] == after_message_id
            ]
            if len(matching_positions) != 1:
                raise ResourceNotFoundError("The export checkpoint is not in the selected thread.")
            start = matching_positions[0] + 1
        page = messages[start : start + limit]
        has_more = start + len(page) < len(messages)
        cursor = str(page[-1]["discordMessageId"]) if page and has_more else None
        return MessagePage(tuple(page), cursor)

    def user_record(self, user_id: str) -> dict[str, Any]:
        value = self._users.get(user_id)
        if value is None:
            raise ResourceNotFoundError("A message author has no fixture user policy.")
        return value

    def course_alias(self, user_id: str) -> str | None:
        return self._aliases.get(user_id)

    def _load_records(self, relative_path: str, schema_name: str) -> tuple[dict[str, Any], ...]:
        return self._contracts.load_records(schema_name, self._root / relative_path)

    def _load_messages(self) -> dict[str, tuple[dict[str, Any], ...]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        message_directory = self._root / "messages"
        for path in sorted(message_directory.glob("*-thread.json")):
            for item in self._contracts.load_records("case-message.schema.json", path):
                grouped.setdefault(str(item["caseId"]), []).append(item)
        result: dict[str, tuple[dict[str, Any], ...]] = {}
        for case_id, values in grouped.items():
            ordered = sorted(values, key=_message_order_key)
            identifiers = [str(item["messageId"]) for item in ordered]
            discord_ids = [str(item["discordMessageId"]) for item in ordered]
            if len(identifiers) != len(set(identifiers)) or len(discord_ids) != len(
                set(discord_ids)
            ):
                raise ContractValidationError("Fixture thread contains duplicate message IDs.")
            result[case_id] = tuple(ordered)
        return result


class LiveDiscordExportAdapter:
    """Fail-closed REST boundary; network implementation is deferred to Task 32."""

    def __init__(
        self,
        credential_environment_variable: str,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        if not ENV_NAME_PATTERN.fullmatch(credential_environment_variable):
            raise ValueError("Credential environment variable name is invalid.")
        environment = os.environ if environ is None else environ
        if not environment.get(credential_environment_variable, "").strip():
            raise AuthorizationError(
                "Live export requires an explicit `dump_bot` credential environment variable."
            )
        self._credential_environment_variable = credential_environment_variable

    def resolve_case(self, case_number_or_thread_id: str) -> ExportCase:
        del case_number_or_thread_id
        raise ProviderUnavailableError(
            "Live Discord REST export is not implemented; fixture mode is the only active adapter."
        )

    def fetch_page(
        self,
        case: ExportCase,
        *,
        after_message_id: str | None,
        limit: int,
    ) -> MessagePage:
        del case, after_message_id, limit
        raise ProviderUnavailableError("Live Discord REST export is not implemented.")

    def user_record(self, user_id: str) -> dict[str, Any]:
        del user_id
        raise ProviderUnavailableError("Live identity policy is not implemented.")

    def course_alias(self, user_id: str) -> str | None:
        del user_id
        raise ProviderUnavailableError("Live membership policy is not implemented.")


def _message_order_key(item: dict[str, Any]) -> tuple[datetime, str]:
    created_at = str(item["createdAt"])
    try:
        parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractValidationError("Message timestamp is not RFC 3339.") from error
    if parsed.tzinfo is None:
        raise ContractValidationError("Message timestamp must include a timezone.")
    return parsed, str(item["messageId"])
