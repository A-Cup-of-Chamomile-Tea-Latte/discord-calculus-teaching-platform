from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from discord_course_bots.data_lab.repository import DataLabRepository

LAB_DIRECTORY_NAME = "phase2b-data-lab"
STAGING_DATABASE_NAME = "staging.sqlite3"


class StagingSafetyError(RuntimeError):
    """The requested carrier is not the explicit synthetic staging lab."""


@dataclass(frozen=True, slots=True)
class LabPaths:
    root: Path
    database: Path
    config: Path
    receipts: Path
    projection_bundles: Path


def lab_paths(root: Path) -> LabPaths:
    resolved = root.expanduser().resolve()
    return LabPaths(
        root=resolved,
        database=resolved / STAGING_DATABASE_NAME,
        config=resolved / "staging-config.json",
        receipts=resolved / "receipts",
        projection_bundles=resolved / "projection-bundles",
    )


def default_config() -> dict[str, Any]:
    return {
        "environment": "STAGING",
        "syntheticOnly": True,
        "liveDiscordEnabled": False,
        "transport": "FAKE_LOCAL",
        "expectedSourceFingerprint": "SYNTHETIC-SHEET-FINGERPRINT",
    }


def _validate_config(config: object) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise StagingSafetyError("STAGING_CONFIG_INVALID")
    if config.get("environment") != "STAGING":
        raise StagingSafetyError("STAGING_ENVIRONMENT_REQUIRED")
    if config.get("syntheticOnly") is not True:
        raise StagingSafetyError("SYNTHETIC_ONLY_REQUIRED")
    if config.get("liveDiscordEnabled") is not False:
        raise StagingSafetyError("LIVE_DISCORD_MUST_BE_DISABLED")
    fingerprint = config.get("expectedSourceFingerprint")
    if not isinstance(fingerprint, str) or not fingerprint.strip():
        raise StagingSafetyError("SOURCE_FINGERPRINT_REQUIRED")
    return config


def load_staging_config(paths: LabPaths) -> dict[str, Any]:
    try:
        config = json.loads(paths.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StagingSafetyError("STAGING_CONFIG_UNREADABLE") from error
    return _validate_config(config)


def assert_staging_paths(paths: LabPaths) -> None:
    if paths.root.name != LAB_DIRECTORY_NAME:
        raise StagingSafetyError("STAGING_DIRECTORY_NAME_REQUIRED")
    if paths.database.name != STAGING_DATABASE_NAME or paths.database.parent != paths.root:
        raise StagingSafetyError("STAGING_DATABASE_PATH_REQUIRED")
    lowered_parts = {part.lower() for part in paths.root.parts}
    if "discord-course-bots-runtime" in lowered_parts or "live" in lowered_parts:
        raise StagingSafetyError("LIVE_DATABASE_PATH_REFUSED")


def ensure_staging_carrier(root: Path, *, create: bool = True) -> LabPaths:
    paths = lab_paths(root)
    assert_staging_paths(paths)
    if create:
        paths.root.mkdir(parents=True, exist_ok=True)
        paths.receipts.mkdir(exist_ok=True)
        paths.projection_bundles.mkdir(exist_ok=True)
        if not paths.config.exists():
            paths.config.write_text(
                json.dumps(default_config(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    load_staging_config(paths)
    return paths


def open_staging_repository(paths: LabPaths) -> DataLabRepository:
    assert_staging_paths(paths)
    load_staging_config(paths)
    repository = DataLabRepository(paths.database)
    repository.set_config("environment", "STAGING")
    repository.set_config("synthetic_only", 1)
    repository.set_config("live_discord_enabled", 0)
    return repository
