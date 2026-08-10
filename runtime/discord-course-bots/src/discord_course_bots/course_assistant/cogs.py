from __future__ import annotations

from datetime import datetime, timezone
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .service import CourseService

LOGGER = logging.getLogger(__name__)


async def _reply(interaction: discord.Interaction, message: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def _staff_allowed(member: discord.Member, service: CourseService) -> bool:
    return service.is_staff(member)


class CaseCog(commands.Cog):
    case = app_commands.Group(name="case", description="公開案件測試命令")
    private = app_commands.Group(name="private", description="Private Support 測試命令")

    def __init__(self, bot: commands.Bot, service: CourseService) -> None:
        self.bot = bot
        self.service = service

    @case.command(name="close", description="由 Staff 關閉目前案件")
    async def close(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            await _reply(interaction, "只能在測試伺服器使用。")
            return
        if not isinstance(interaction.channel, discord.Thread):
            await _reply(interaction, "請在案件 Forum thread 內執行。")
            return
        if not _staff_allowed(interaction.user, self.service):
            await _reply(interaction, "只有 TA／Professor／測試管理者可結案。")
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.service.close_case(interaction.channel)
        except (RuntimeError, discord.HTTPException) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        await interaction.followup.send("案件已結束並封存。", ephemeral=True)

    @private.command(name="open", description="建立 Private Support 測試頻道")
    @app_commands.describe(ai_permission="是否允許 AI 分析文字正文")
    async def private_open(
        self, interaction: discord.Interaction, ai_permission: bool
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await _reply(interaction, "只能在測試伺服器使用。")
            return
        category_id = self.service.repo.get_config_int("private_support_category_id")
        if category_id is None:
            await _reply(interaction, "請先執行 `/lab bootstrap`。")
            return
        category = interaction.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            await _reply(interaction, "Private Support category 不存在，請重新 bootstrap。")
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        me = interaction.guild.me
        if me is None:
            await interaction.followup.send("找不到 Bot member。", ephemeral=True)
            return
        overwrites = dict(category.overwrites)
        overwrites[interaction.user] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
        )
        channel = await interaction.guild.create_text_channel(
            name=f"private-{interaction.user.id % 100000:05d}",
            category=category,
            overwrites=overwrites,
            reason="Private Support test request",
        )
        case_number = self.service.repo.create_private_support(
            channel.id, interaction.user.id, ai_permission
        )
        await channel.send(
            f"Private Support 測試案件已建立。案號：`{case_number}`\n"
            f"提出者：{interaction.user.mention}\n"
            f"AI 文字內容分析：**{'Yes' if ai_permission else 'No'}**\n\n"
            "⚠️ 測試版尚未接通結案匯出後自動刪除。",
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )
        await interaction.followup.send(f"已建立 {channel.mention}", ephemeral=True)

    @private.command(name="close", description="由 Staff 結束 Private Support，準備匯出")
    async def private_close(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not _staff_allowed(interaction.user, self.service):
            await _reply(interaction, "只有 TA／Professor／測試管理者可結案。")
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await _reply(interaction, "請在 Private Support 頻道內執行。")
            return
        dump_bot_id = self.service.settings.dump_bot_client_id
        if dump_bot_id is None:
            await _reply(interaction, "尚未設定 DUMP_BOT_CLIENT_ID。")
            return
        dump_member = interaction.guild.get_member(dump_bot_id) if interaction.guild else None
        if dump_member is None and interaction.guild is not None:
            try:
                dump_member = await interaction.guild.fetch_member(dump_bot_id)
            except discord.HTTPException:
                dump_member = None
        if dump_member is None:
            await _reply(interaction, "找不到 dump_bot member。")
            return
        overwrites = dict(interaction.channel.overwrites)
        overwrites[dump_member] = discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=False,
        )
        try:
            await interaction.channel.edit(
                overwrites=overwrites,
                reason="Private Support closed; grant dump_bot read-only export access",
            )
        except discord.HTTPException as exc:
            await _reply(interaction, f"無法設定 dump_bot 唯讀權限：{exc}")
            return
        if self.service.repo.close_private_support(interaction.channel.id) is None:
            await _reply(interaction, "Private Support 不是可結案的 OPEN 狀態。")
            return
        from .views import PrivateDumpView

        await interaction.channel.send(
            "✅ **Private Support 已結案。**\n\n"
            "確認不再需要追問後，請由 Staff 確認匯出；驗證成功後此頻道將被刪除。",
            view=PrivateDumpView(self.service),
        )
        await _reply(interaction, "已發布匯出確認介面。")

    @private.command(name="dump", description="確認匯出已結案的 Private Support")
    async def private_dump(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not _staff_allowed(interaction.user, self.service):
            await _reply(interaction, "只有 TA／Professor／測試管理者可要求匯出。")
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await _reply(interaction, "請在 Private Support 頻道內執行。")
            return
        if not self.service.repo.queue_private_dump(interaction.channel.id, interaction.user.id):
            await _reply(interaction, "此頻道尚未結案，或已有匯出工作。")
            return
        await _reply(interaction, "Private dump 已排入工作；驗證完成後將刪除此頻道。")


class DraftLifecycleCog(commands.Cog):
    def __init__(self, bot: commands.Bot, service: CourseService) -> None:
        self.bot = bot
        self.service = service
        self.draft_sweep.start()
        self.private_delete_sweep.start()

    def cog_unload(self) -> None:
        self.draft_sweep.cancel()
        self.private_delete_sweep.cancel()

    @tasks.loop(seconds=10)
    async def private_delete_sweep(self) -> None:
        for job in self.service.repo.pending_private_deletions():
            channel_id = int(job["channel_id"])
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.NotFound:
                    self.service.repo.mark_private_deleted(channel_id)
                    continue
                except discord.HTTPException:
                    continue
            if not isinstance(channel, discord.TextChannel):
                continue
            try:
                await channel.delete(reason="Verified Private Support dump completed")
            except discord.HTTPException:
                LOGGER.exception("Private channel deletion failed for %s", channel_id)
                continue
            self.service.repo.mark_private_deleted(channel_id)

    @tasks.loop(seconds=30)
    async def draft_sweep(self) -> None:
        now = datetime.now(timezone.utc)
        for draft in self.service.repo.pending_drafts():
            try:
                created = datetime.fromisoformat(str(draft["created_at"]))
                age = (now - created).total_seconds()
                thread = self.bot.get_channel(int(draft["thread_id"]))
                if not isinstance(thread, discord.Thread):
                    continue
                if (
                    age >= self.service.settings.draft_delete_seconds
                    and draft["deleted_at"] is None
                ):
                    self.service.repo.mark_draft_deleted(thread.id, "EXPIRED")
                    await thread.delete(reason="Draft expired in test lifecycle")
                    continue
                if (
                    age >= self.service.settings.draft_reminder_seconds
                    and draft["reminded_at"] is None
                ):
                    user = self.bot.get_user(int(draft["author_id"]))
                    if user is None:
                        try:
                            user = await self.bot.fetch_user(int(draft["author_id"]))
                        except discord.HTTPException:
                            user = None
                    if user is not None:
                        try:
                            await user.send(
                                f"您在 `{thread.name}` 的測試草稿尚未完成設定：{thread.jump_url}"
                            )
                        except discord.HTTPException:
                            LOGGER.info(
                                "Draft reminder DM failed for %s; Email fallback pending",
                                draft["author_id"],
                            )
                    self.service.repo.mark_draft_reminded(thread.id)
            except discord.HTTPException:
                LOGGER.exception("Draft lifecycle operation failed for thread %s", draft["thread_id"])

    @draft_sweep.before_loop
    async def before_draft_sweep(self) -> None:
        await self.bot.wait_until_ready()

    @private_delete_sweep.before_loop
    async def before_private_delete_sweep(self) -> None:
        await self.bot.wait_until_ready()
