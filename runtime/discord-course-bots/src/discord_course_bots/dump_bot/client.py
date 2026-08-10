from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import suppress
from pathlib import Path

import discord
from discord.ext import tasks

from discord_course_bots.repository import Repository
from discord_course_bots.settings import DumpBotSettings

from .exporter import collect_messages, verify_export, write_export

LOGGER = logging.getLogger(__name__)
PRIVATE_DUMP_LEASE_SECONDS = 900
PRIVATE_DUMP_HEARTBEAT_SECONDS = 300
PRIVATE_DUMP_MAX_JOBS_PER_SWEEP = 5


def classify_private_dump_error(error: Exception) -> tuple[str, bool]:
    """Return a privacy-safe error code and whether the job may be retried."""
    if isinstance(error, discord.Forbidden):
        return ("DISCORD_FORBIDDEN", False)
    if isinstance(error, discord.NotFound):
        return ("CHANNEL_NOT_FOUND", False)
    if isinstance(error, discord.HTTPException):
        return ("DISCORD_HTTP_ERROR", True)
    if isinstance(error, OSError):
        return ("FILESYSTEM_ERROR", True)
    if isinstance(error, RuntimeError):
        return ("EXPORT_VALIDATION_ERROR", True)
    return ("UNEXPECTED_ERROR", True)


class DumpClient(discord.Client):
    def __init__(
        self,
        settings: DumpBotSettings,
        *,
        mode: str,
        channel_id: int | None = None,
        output_dir: Path | None = None,
    ) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.settings = settings
        self.mode = mode
        self.channel_id = channel_id
        self.output_dir = output_dir or Path("exports")
        self.repo = Repository(settings.database_path)
        self.worker_id = f"dump-bot-{uuid.uuid4().hex}"

    async def on_ready(self) -> None:
        unexpected = [guild for guild in self.guilds if guild.id != self.settings.test_guild_id]
        guild = self.get_guild(self.settings.test_guild_id)
        if unexpected or guild is None:
            LOGGER.critical(
                "Guild guard failed. Expected=%s connected=%s",
                self.settings.test_guild_id,
                [item.id for item in self.guilds],
            )
            await self.close()
            return
        LOGGER.info("dump_bot online as %s in %s", self.user, guild.name)

        if self.mode == "online":
            if not self.private_dump_worker.is_running():
                self.private_dump_worker.start()
            return

        if self.mode == "probe":
            me = guild.me
            if me is None:
                raise RuntimeError("dump_bot member is unavailable")
            visible: list[str] = []
            for channel in guild.channels:
                perms = channel.permissions_for(me)
                if perms.view_channel:
                    visible.append(
                        f"{channel.id} {channel.name} "
                        f"view={perms.view_channel} history={perms.read_message_history} "
                        f"send={perms.send_messages}"
                    )
            print("\n".join(visible) or "No visible channels")
            await self.close()
            return

        if self.mode in {"export-public", "export-private"}:
            if self.channel_id is None:
                raise RuntimeError("channel_id is required for export")
            channel = self.get_channel(self.channel_id)
            if channel is None:
                try:
                    channel = await self.fetch_channel(self.channel_id)
                except discord.HTTPException as exc:
                    raise RuntimeError(f"Cannot fetch channel {self.channel_id}: {exc}") from exc
            if self.mode == "export-public":
                if not isinstance(channel, discord.Thread):
                    raise RuntimeError("Public exports require a Forum thread")
                case = self.repo.get_case_by_thread(channel.id)
                raw_forum_ids = self.repo.get_config("managed_forum_ids")
                try:
                    forum_ids = (
                        {int(value) for value in json.loads(raw_forum_ids)}
                        if raw_forum_ids
                        else set()
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    forum_ids = set()
                legacy_forum_id = self.repo.get_config_int("public_forum_channel_id")
                if legacy_forum_id is not None:
                    forum_ids.add(legacy_forum_id)
                if case is None or channel.parent_id not in forum_ids:
                    raise RuntimeError("Thread is not a registered public Forum case")
                export_scope = "public"
                case_number = str(case["case_number"])
            else:
                if not isinstance(channel, discord.TextChannel):
                    raise RuntimeError("Private exports require a text channel")
                private_case = self.repo.get_private_support(channel.id)
                if private_case is None:
                    raise RuntimeError("Channel is not a registered Private Support case")
                export_scope = "private"
                case_number = str(private_case["case_number"])
            me = guild.me
            if me is None:
                raise RuntimeError("dump_bot member is unavailable")
            perms = channel.permissions_for(me)
            if not perms.view_channel or not perms.read_message_history:
                raise RuntimeError("dump_bot lacks View Channel or Read Message History")
            messages = await collect_messages(channel)
            paths = write_export(
                output_dir=self.output_dir,
                guild_id=guild.id,
                channel_id=channel.id,
                channel_name=channel.name,
                messages=messages,
                export_scope=export_scope,
                case_number=case_number,
            )
            for kind, path in paths.items():
                print(f"{kind}: {path}")
            await self.close()

    async def on_error(self, event_method: str, *args: object, **kwargs: object) -> None:
        LOGGER.exception("Unhandled dump_bot event error in %s", event_method)
        if self.mode != "online":
            await self.close()

    async def export_private_channel(
        self, guild: discord.Guild, channel_id: int
    ) -> dict[str, Path]:
        channel = self.get_channel(channel_id)
        if channel is None:
            channel = await self.fetch_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            raise RuntimeError("Private dump target is not a text channel")
        private_case = self.repo.get_private_support(channel.id)
        if private_case is None or str(private_case["status"]) != "CLOSED":
            raise RuntimeError("Private dump target is not closed")
        me = guild.me
        if me is None:
            raise RuntimeError("dump_bot member is unavailable")
        perms = channel.permissions_for(me)
        if not perms.view_channel or not perms.read_message_history:
            raise RuntimeError("dump_bot lacks View Channel or Read Message History")
        messages = await collect_messages(channel)
        return write_export(
            output_dir=Path("exports/private"),
            guild_id=guild.id,
            channel_id=channel.id,
            channel_name=channel.name,
            messages=messages,
            export_scope="private",
            case_number=str(private_case["case_number"]),
        )

    @tasks.loop(seconds=10)
    async def private_dump_worker(self) -> None:
        guild = self.get_guild(self.settings.test_guild_id)
        if guild is None:
            return
        for _ in range(PRIVATE_DUMP_MAX_JOBS_PER_SWEEP):
            claim = self.repo.claim_private_dump_job(
                worker_id=self.worker_id,
                lease_seconds=PRIVATE_DUMP_LEASE_SECONDS,
            )
            if claim is None:
                break
            heartbeat = asyncio.create_task(
                self._renew_private_dump_lease(claim.channel_id, claim.claim_token)
            )
            try:
                paths = await self.export_private_channel(guild, claim.channel_id)
                if not verify_export(paths):
                    raise RuntimeError("Private dump manifest verification failed")
                completed = self.repo.complete_private_dump(
                    claim.channel_id,
                    claim.claim_token,
                    str(paths["manifest"]),
                )
                if completed:
                    LOGGER.info("Verified private dump for %s", claim.channel_id)
                else:
                    LOGGER.warning(
                        "Private dump claim became stale before completion for %s",
                        claim.channel_id,
                    )
            except Exception as error:
                error_code, retryable = classify_private_dump_error(error)
                failure = self.repo.fail_private_dump_job(
                    channel_id=claim.channel_id,
                    claim_token=claim.claim_token,
                    error_code=error_code,
                    retryable=retryable,
                )
                if failure is None:
                    LOGGER.exception(
                        "Private dump failed after its claim became stale for %s",
                        claim.channel_id,
                    )
                else:
                    LOGGER.exception(
                        "Private dump failed for %s with %s; state=%s",
                        claim.channel_id,
                        error_code,
                        failure.status,
                    )
            finally:
                heartbeat.cancel()
                with suppress(asyncio.CancelledError):
                    await heartbeat

    async def _renew_private_dump_lease(self, channel_id: int, claim_token: str) -> None:
        while True:
            await asyncio.sleep(PRIVATE_DUMP_HEARTBEAT_SECONDS)
            renewed = self.repo.renew_private_dump_lease(
                channel_id=channel_id,
                claim_token=claim_token,
                lease_seconds=PRIVATE_DUMP_LEASE_SECONDS,
            )
            if not renewed:
                LOGGER.warning("Private dump lease could not be renewed for %s", channel_id)
                return

    @private_dump_worker.before_loop
    async def before_private_dump_worker(self) -> None:
        await self.wait_until_ready()
