from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import discord
import pytest

from tools.discord_provisioning.live import (
    REASON,
    delete_permission_overwrite,
    resolve_database_path,
)


def test_relative_database_path_uses_real_env_file_directory(tmp_path: Path) -> None:
    assert (
        resolve_database_path(
            {"DATABASE_PATH": "data/course_bots.sqlite3", "_ENV_FILE_DIR": str(tmp_path)}
        )
        == tmp_path / "data/course_bots.sqlite3"
    )


@pytest.mark.asyncio
async def test_delete_permission_overwrite_accepts_uncached_discord_object() -> None:
    delete_channel_permissions = AsyncMock()
    channel = SimpleNamespace(
        id=456,
        _state=SimpleNamespace(
            http=SimpleNamespace(delete_channel_permissions=delete_channel_permissions)
        ),
    )

    await delete_permission_overwrite(
        cast(discord.abc.GuildChannel, channel), discord.Object(id=123)
    )

    delete_channel_permissions.assert_awaited_once_with(456, 123, reason=REASON)
