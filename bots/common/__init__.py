"""Shared bot infrastructure without bot-specific event ownership or credentials."""

from bots.common.config import (
    ArchiveReaderConfig,
    BotConfig,
    CourseAssistantConfig,
    RuntimeMode,
    SecretValue,
    load_archive_reader_config,
    load_course_assistant_config,
)
from bots.common.contracts import ContractRegistry
from bots.common.errors import BotCoreError
from bots.common.health import build_health
from bots.common.lifecycle import LifecycleManager

__all__ = [
    "ArchiveReaderConfig",
    "BotConfig",
    "BotCoreError",
    "ContractRegistry",
    "CourseAssistantConfig",
    "LifecycleManager",
    "RuntimeMode",
    "SecretValue",
    "build_health",
    "load_archive_reader_config",
    "load_course_assistant_config",
]
