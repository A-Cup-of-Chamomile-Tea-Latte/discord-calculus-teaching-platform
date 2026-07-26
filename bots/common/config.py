"""Typed per-bot environment configuration with fail-closed token handling."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from bots.common.errors import ConfigurationError

SNOWFLAKE_PATTERN = re.compile(r"^[0-9]{17,20}$")


class RuntimeMode(StrEnum):
    FIXTURE = "fixture"
    DRY_RUN = "dry-run"
    LIVE = "live"


@dataclass(frozen=True, repr=False)
class SecretValue:
    """Explicit secret wrapper whose display forms are always redacted."""

    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ConfigurationError("A configured secret must not be empty.")

    def reveal(self) -> str:
        """Return the value only at the provider boundary."""
        return self._value

    def __repr__(self) -> str:
        return "SecretValue(<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"


@dataclass(frozen=True)
class BotConfig:
    bot_name: str
    runtime_mode: RuntimeMode
    guild_id: str | None
    channel_ids: tuple[str, ...]
    token: SecretValue | None = field(repr=False)

    @property
    def network_enabled(self) -> bool:
        return self.runtime_mode is RuntimeMode.LIVE

    def redaction_values(self) -> tuple[str, ...]:
        return (self.token.reveal(),) if self.token else ()


@dataclass(frozen=True)
class CourseAssistantConfig(BotConfig):
    role_ids: tuple[str, ...]


@dataclass(frozen=True)
class ArchiveReaderConfig(BotConfig):
    message_content_enabled: bool


def _environment(source: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if source is None else source


def _mode(environment: Mapping[str, str]) -> RuntimeMode:
    raw = environment.get("BOT_RUNTIME_MODE", RuntimeMode.FIXTURE.value).strip().lower()
    try:
        return RuntimeMode(raw)
    except ValueError as error:
        choices = ", ".join(mode.value for mode in RuntimeMode)
        raise ConfigurationError(
            f"BOT_RUNTIME_MODE must be one of: {choices}; received an unsupported value."
        ) from error


def _optional(environment: Mapping[str, str], key: str) -> str | None:
    value = environment.get(key, "").strip()
    return value or None


def _ids(environment: Mapping[str, str], key: str) -> tuple[str, ...]:
    raw = _optional(environment, key)
    if raw is None:
        return ()
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not values or len(set(values)) != len(values):
        raise ConfigurationError(f"{key} must contain unique comma-separated Discord IDs.")
    invalid = [value for value in values if not SNOWFLAKE_PATTERN.fullmatch(value)]
    if invalid:
        raise ConfigurationError(f"{key} contains an invalid Discord ID.")
    return values


def _guild(environment: Mapping[str, str], key: str) -> str | None:
    value = _optional(environment, key)
    if value is not None and not SNOWFLAKE_PATTERN.fullmatch(value):
        raise ConfigurationError(f"{key} must be a 17–20 digit Discord ID.")
    return value


def _token(
    environment: Mapping[str, str],
    *,
    own_key: str,
    forbidden_key: str,
    mode: RuntimeMode,
) -> SecretValue | None:
    if _optional(environment, forbidden_key) is not None:
        raise ConfigurationError(
            f"{forbidden_key} belongs to another bot runtime and must not be co-located."
        )
    raw = _optional(environment, own_key)
    if mode is RuntimeMode.LIVE:
        if raw is None:
            raise ConfigurationError(f"{own_key} is required when BOT_RUNTIME_MODE=live.")
        return SecretValue(raw)
    if raw is not None:
        raise ConfigurationError(
            f"{own_key} must be absent in fixture/dry-run mode to prevent accidental connection."
        )
    return None


def _require_live_target(
    mode: RuntimeMode,
    *,
    guild_id: str | None,
    channel_ids: tuple[str, ...],
    guild_key: str,
    channels_key: str,
) -> None:
    if mode is RuntimeMode.LIVE and guild_id is None:
        raise ConfigurationError(f"{guild_key} is required when BOT_RUNTIME_MODE=live.")
    if mode is RuntimeMode.LIVE and not channel_ids:
        raise ConfigurationError(f"{channels_key} is required when BOT_RUNTIME_MODE=live.")


def load_course_assistant_config(
    source: Mapping[str, str] | None = None,
) -> CourseAssistantConfig:
    environment = _environment(source)
    mode = _mode(environment)
    guild_id = _guild(environment, "COURSE_ASSISTANT_GUILD_ID")
    channel_ids = _ids(environment, "COURSE_ASSISTANT_CHANNEL_IDS")
    _require_live_target(
        mode,
        guild_id=guild_id,
        channel_ids=channel_ids,
        guild_key="COURSE_ASSISTANT_GUILD_ID",
        channels_key="COURSE_ASSISTANT_CHANNEL_IDS",
    )
    return CourseAssistantConfig(
        bot_name="course_assistant",
        runtime_mode=mode,
        guild_id=guild_id,
        channel_ids=channel_ids,
        token=_token(
            environment,
            own_key="COURSE_ASSISTANT_DISCORD_TOKEN",
            forbidden_key="ARCHIVE_READER_DISCORD_TOKEN",
            mode=mode,
        ),
        role_ids=_ids(environment, "COURSE_ASSISTANT_ROLE_IDS"),
    )


def load_archive_reader_config(
    source: Mapping[str, str] | None = None,
) -> ArchiveReaderConfig:
    environment = _environment(source)
    mode = _mode(environment)
    guild_id = _guild(environment, "ARCHIVE_READER_GUILD_ID")
    channel_ids = _ids(environment, "ARCHIVE_READER_CHANNEL_IDS")
    raw_content = environment.get("ARCHIVE_READER_MESSAGE_CONTENT_ENABLED", "false")
    if raw_content not in {"true", "false"}:
        raise ConfigurationError("ARCHIVE_READER_MESSAGE_CONTENT_ENABLED must be true or false.")
    message_content_enabled = raw_content == "true"
    _require_live_target(
        mode,
        guild_id=guild_id,
        channel_ids=channel_ids,
        guild_key="ARCHIVE_READER_GUILD_ID",
        channels_key="ARCHIVE_READER_CHANNEL_IDS",
    )
    if mode is RuntimeMode.LIVE and not message_content_enabled:
        raise ConfigurationError(
            "ARCHIVE_READER_MESSAGE_CONTENT_ENABLED=true is required for live content fetch."
        )
    return ArchiveReaderConfig(
        bot_name="archive_reader",
        runtime_mode=mode,
        guild_id=guild_id,
        channel_ids=channel_ids,
        token=_token(
            environment,
            own_key="ARCHIVE_READER_DISCORD_TOKEN",
            forbidden_key="COURSE_ASSISTANT_DISCORD_TOKEN",
            mode=mode,
        ),
        message_content_enabled=message_content_enabled,
    )
