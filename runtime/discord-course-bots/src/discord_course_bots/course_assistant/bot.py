from __future__ import annotations

import logging

import discord
from discord.ext import commands, tasks

from discord_course_bots.logging_config import configure_logging
from discord_course_bots.repository import Repository
from discord_course_bots.settings import SettingsError, load_course_assistant_settings

from .cogs import CaseCog, DraftLifecycleCog
from .service import CourseService
from .views import DraftSetupView, PrivateDumpView, ReopenView

LOGGER = logging.getLogger(__name__)


class CourseAssistantBot(commands.Bot):
    def __init__(self) -> None:
        self.settings = load_course_assistant_settings()
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.repo = Repository(self.settings.database_path)
        self.service = CourseService(self, self.settings, self.repo)

    async def setup_hook(self) -> None:
        self.add_view(DraftSetupView(self.service))
        self.add_view(ReopenView(self.service))
        self.add_view(PrivateDumpView(self.service))
        await self.add_cog(CaseCog(self, self.service))
        await self.add_cog(DraftLifecycleCog(self, self.service))
        test_guild = discord.Object(id=self.settings.test_guild_id)
        self.tree.copy_global_to(guild=test_guild)
        synced = await self.tree.sync(guild=test_guild)
        LOGGER.info("Synced %d application commands to test guild", len(synced))

    async def on_ready(self) -> None:
        unexpected = [guild for guild in self.guilds if guild.id != self.settings.test_guild_id]
        expected = self.get_guild(self.settings.test_guild_id)
        if unexpected or expected is None:
            LOGGER.critical(
                "Guild guard failed. Expected=%s connected=%s",
                self.settings.test_guild_id,
                [guild.id for guild in self.guilds],
            )
            await self.close()
            return
        LOGGER.info("course_assistant online as %s in %s", self.user, expected.name)
        self.repo.update_service_health(
            service_key="course-assistant",
            service="course_assistant",
            component="discord-gateway",
        )
        if not self.health_heartbeat.is_running():
            self.health_heartbeat.start()
        for row in self.repo.tracked_cases():
            if self.repo.has_unfinished_discord_lifecycle_job(str(row["case_id"])):
                continue
            thread_id = int(row["thread_id"])
            channel = self.get_channel(thread_id)
            if channel is None:
                try:
                    channel = await self.fetch_channel(thread_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    LOGGER.warning("Tracked thread %s is unavailable during startup", thread_id)
                    continue
            if isinstance(channel, discord.Thread):
                try:
                    await self.service.reconcile_title(channel)
                except discord.HTTPException:
                    LOGGER.exception("Startup reconciliation failed for %s", channel.id)

    @tasks.loop(seconds=60)
    async def health_heartbeat(self) -> None:
        self.repo.update_service_health(
            service_key="course-assistant",
            service="course_assistant",
            component="discord-gateway",
        )

    @health_heartbeat.before_loop
    async def before_health_heartbeat(self) -> None:
        await self.wait_until_ready()

    async def on_thread_create(self, thread: discord.Thread) -> None:
        try:
            await self.service.register_new_thread(thread)
        except discord.HTTPException:
            LOGGER.exception("New thread registration failed for %s", thread.id)

    async def on_thread_update(self, before: discord.Thread, after: discord.Thread) -> None:
        if before.name == after.name:
            return
        try:
            await self.service.reconcile_title(after)
        except discord.HTTPException:
            LOGGER.exception("Title reconciliation failed for %s", after.id)


def main() -> None:
    try:
        settings = load_course_assistant_settings()
        configure_logging(settings.log_level)
        bot = CourseAssistantBot()
        bot.run(settings.token, log_handler=None)
    except SettingsError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
