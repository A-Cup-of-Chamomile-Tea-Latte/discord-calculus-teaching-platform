"""discord.py command skeleton with a network-free fixture runtime."""

from __future__ import annotations

from collections.abc import Callable

import discord
from discord.ext import commands

from bots.common.config import CourseAssistantConfig
from bots.common.errors import NotConfiguredError
from bots.common.models import HealthStatus
from bots.course_assistant.service import CourseAssistantService


class CourseAssistantDiscordApp:
    def __init__(
        self,
        config: CourseAssistantConfig,
        service: CourseAssistantService,
        *,
        now: Callable[[], str],
    ) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        self.bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
        self._config = config
        self._service = service
        self._now = now
        self.status = HealthStatus.STOPPED
        self._register_commands()

    @property
    def name(self) -> str:
        return "course_assistant_discord_app"

    async def start(self) -> None:
        if self._config.network_enabled:
            raise NotConfiguredError(
                "Live Discord startup is intentionally not configured in the fixture skeleton."
            )
        self.status = HealthStatus.READY

    async def stop(self) -> None:
        self.status = HealthStatus.STOPPING
        await self.bot.close()
        self.status = HealthStatus.STOPPED

    def _register_commands(self) -> None:
        @self.bot.tree.command(name="health", description="查看課程助理機器人狀態")
        async def health(interaction: discord.Interaction) -> None:
            info = self._service.health(self.status, self._now())
            await interaction.response.send_message(
                f"狀態：{info.status.value}；模式：{info.runtime_mode}",
                ephemeral=True,
            )
