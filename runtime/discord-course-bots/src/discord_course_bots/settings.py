from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class SettingsError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _required_int(name: str) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        raise SettingsError(f"Missing required environment variable: {name}")
    try:
        return int(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be an integer Discord snowflake") from exc


def _optional_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be an integer Discord snowflake") from exc


def _csv_ints(name: str) -> frozenset[int]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return frozenset()
    try:
        return frozenset(int(part.strip()) for part in raw.split(",") if part.strip())
    except ValueError as exc:
        raise SettingsError(f"{name} must contain comma-separated Discord user IDs") from exc


@dataclass(frozen=True, slots=True)
class CommonSettings:
    test_guild_id: int
    owner_ids: frozenset[int]
    database_path: Path
    log_level: str


@dataclass(frozen=True, slots=True)
class CourseAssistantSettings(CommonSettings):
    token: str
    client_id: int | None
    dump_bot_client_id: int | None
    module_code: str
    draft_reminder_seconds: int
    draft_delete_seconds: int


@dataclass(frozen=True, slots=True)
class DumpBotSettings(CommonSettings):
    token: str
    client_id: int | None


def _load_common() -> dict[str, object]:
    load_dotenv()
    database_path = Path(os.getenv("DATABASE_PATH", "./data/course_bots.sqlite3"))
    return {
        "test_guild_id": _required_int("TEST_GUILD_ID"),
        "owner_ids": _csv_ints("BOT_OWNER_IDS"),
        "database_path": database_path,
        "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
    }


def load_course_assistant_settings() -> CourseAssistantSettings:
    common = _load_common()
    token = os.getenv("COURSE_ASSISTANT_TOKEN", "").strip()
    if not token:
        raise SettingsError("Missing required environment variable: COURSE_ASSISTANT_TOKEN")
    reminder = int(os.getenv("DRAFT_REMINDER_SECONDS", "86400"))
    delete = int(os.getenv("DRAFT_DELETE_SECONDS", "172800"))
    if reminder <= 0 or delete <= reminder:
        raise SettingsError("Draft timing must satisfy 0 < reminder < delete")
    module_code = os.getenv("TEST_MODULE_CODE", "M1").strip().upper()
    if not module_code:
        raise SettingsError("TEST_MODULE_CODE cannot be empty")
    return CourseAssistantSettings(
        **common,
        token=token,
        client_id=_optional_int("COURSE_ASSISTANT_CLIENT_ID"),
        dump_bot_client_id=_optional_int("DUMP_BOT_CLIENT_ID"),
        module_code=module_code,
        draft_reminder_seconds=reminder,
        draft_delete_seconds=delete,
    )


def load_dump_bot_settings() -> DumpBotSettings:
    common = _load_common()
    token = os.getenv("DUMP_BOT_TOKEN", "").strip()
    if not token:
        raise SettingsError("Missing required environment variable: DUMP_BOT_TOKEN")
    return DumpBotSettings(
        **common,
        token=token,
        client_id=_optional_int("DUMP_BOT_CLIENT_ID"),
    )
