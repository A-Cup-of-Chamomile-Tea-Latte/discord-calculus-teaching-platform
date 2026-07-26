from __future__ import annotations

import importlib
from dataclasses import asdict

import pytest

from bots.common.config import (
    RuntimeMode,
    load_archive_reader_config,
    load_course_assistant_config,
)
from bots.common.errors import ConfigurationError
from bots.common.health import build_health
from bots.common.models import HealthStatus

GUILD_ID = "123456789012345678"
CHANNEL_ID = "223456789012345678"
ROLE_ID = "323456789012345678"
FIXTURE_TOKEN = "fixture-token-value-that-must-never-be-logged"


def test_future_bot_packages_import_without_tokens_or_circular_imports() -> None:
    assert importlib.import_module("bots.course_assistant") is not None
    assert importlib.import_module("bots.archive_reader") is not None
    assert importlib.import_module("bots.moderation") is not None


def test_package_config_defaults_to_network_free_fixture_mode() -> None:
    config = load_course_assistant_config({})
    assert config.runtime_mode is RuntimeMode.FIXTURE
    assert config.token is None
    assert config.network_enabled is False


def test_live_course_config_is_named_typed_and_redacted() -> None:
    config = load_course_assistant_config(
        {
            "BOT_RUNTIME_MODE": "live",
            "COURSE_ASSISTANT_DISCORD_TOKEN": FIXTURE_TOKEN,
            "COURSE_ASSISTANT_GUILD_ID": GUILD_ID,
            "COURSE_ASSISTANT_CHANNEL_IDS": CHANNEL_ID,
            "COURSE_ASSISTANT_ROLE_IDS": ROLE_ID,
        }
    )
    assert config.bot_name == "course_assistant"
    assert config.channel_ids == (CHANNEL_ID,)
    assert config.role_ids == (ROLE_ID,)
    assert config.token is not None and config.token.reveal() == FIXTURE_TOKEN
    assert FIXTURE_TOKEN not in repr(config)
    assert FIXTURE_TOKEN not in str(config.token)


def test_live_missing_configuration_names_the_required_variable() -> None:
    with pytest.raises(ConfigurationError, match="COURSE_ASSISTANT_GUILD_ID"):
        load_course_assistant_config(
            {
                "BOT_RUNTIME_MODE": "live",
                "COURSE_ASSISTANT_DISCORD_TOKEN": FIXTURE_TOKEN,
            }
        )


def test_fixture_mode_rejects_tokens_and_cross_bot_token_colocation() -> None:
    with pytest.raises(ConfigurationError, match="must be absent"):
        load_course_assistant_config({"COURSE_ASSISTANT_DISCORD_TOKEN": FIXTURE_TOKEN})
    with pytest.raises(ConfigurationError, match="another bot runtime") as error:
        load_course_assistant_config(
            {
                "BOT_RUNTIME_MODE": "live",
                "COURSE_ASSISTANT_DISCORD_TOKEN": FIXTURE_TOKEN,
                "ARCHIVE_READER_DISCORD_TOKEN": "different-fixture-value",
                "COURSE_ASSISTANT_GUILD_ID": GUILD_ID,
                "COURSE_ASSISTANT_CHANNEL_IDS": CHANNEL_ID,
            }
        )
    assert FIXTURE_TOKEN not in str(error.value)


def test_archive_reader_live_mode_requires_explicit_message_content_capability() -> None:
    environment = {
        "BOT_RUNTIME_MODE": "live",
        "ARCHIVE_READER_DISCORD_TOKEN": FIXTURE_TOKEN,
        "ARCHIVE_READER_GUILD_ID": GUILD_ID,
        "ARCHIVE_READER_CHANNEL_IDS": CHANNEL_ID,
    }
    with pytest.raises(ConfigurationError, match="MESSAGE_CONTENT_ENABLED=true"):
        load_archive_reader_config(environment)
    config = load_archive_reader_config(
        {**environment, "ARCHIVE_READER_MESSAGE_CONTENT_ENABLED": "true"}
    )
    assert config.bot_name == "archive_reader"
    assert config.message_content_enabled is True


def test_health_projection_contains_no_secret_or_raw_ids() -> None:
    config = load_course_assistant_config(
        {
            "COURSE_ASSISTANT_GUILD_ID": GUILD_ID,
            "COURSE_ASSISTANT_CHANNEL_IDS": CHANNEL_ID,
        }
    )
    health = build_health(
        config,
        status=HealthStatus.READY,
        checked_at="2026-07-19T10:00:00+00:00",
    )
    serialized = str(asdict(health))
    assert health.ready is True
    assert health.network_enabled is False
    assert health.allowed_channel_count == 1
    assert GUILD_ID not in serialized
    assert CHANNEL_ID not in serialized
