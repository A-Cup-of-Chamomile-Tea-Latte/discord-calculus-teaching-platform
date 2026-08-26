from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from discord_course_bots.domain.keyword import KeywordValidationError

LOGGER = logging.getLogger(__name__)


async def _ephemeral_error(interaction: discord.Interaction, message: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


class KeywordModal(discord.ui.Modal, title="設定這篇文章"):
    keyword = discord.ui.TextInput(
        label="關鍵字",
        placeholder="例如：隱函數微分",
        required=True,
        max_length=30,
    )

    def __init__(self, service: CourseService, thread_id: int, author_id: int) -> None:
        super().__init__(timeout=300)
        self.service = service
        self.thread_id = thread_id
        self.author_id = author_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.author_id:
            await _ephemeral_error(interaction, "只有原發文者可以設定這篇文章。")
            return
        await interaction.response.send_message(
            "請選擇是否允許後台以 AI 分析本篇貼文的文字內容。",
            view=AIPermissionView(
                self.service,
                thread_id=self.thread_id,
                author_id=self.author_id,
                keyword=str(self.keyword.value),
            ),
            ephemeral=True,
        )


class AIPermissionView(discord.ui.View):
    def __init__(
        self,
        service: CourseService,
        *,
        thread_id: int,
        author_id: int,
        keyword: str,
    ) -> None:
        super().__init__(timeout=300)
        self.service = service
        self.thread_id = thread_id
        self.author_id = author_id
        self.keyword = keyword
        self.ai_permission: bool | None = None

    async def _choose_permission(
        self, interaction: discord.Interaction, *, allow_analysis: bool
    ) -> None:
        if interaction.user.id != self.author_id:
            await _ephemeral_error(interaction, "只有原發文者可以完成設定。")
            return
        self.ai_permission = allow_analysis
        self.allow_ai.style = (
            discord.ButtonStyle.success if allow_analysis else discord.ButtonStyle.secondary
        )
        self.deny_ai.style = (
            discord.ButtonStyle.danger if not allow_analysis else discord.ButtonStyle.secondary
        )
        choice = "允許" if allow_analysis else "不允許"
        await interaction.response.edit_message(
            content=f"AI 文字內容分析：**{choice}**",
            view=self,
        )

    @discord.ui.button(label="允許", style=discord.ButtonStyle.secondary, row=0)
    async def allow_ai(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._choose_permission(interaction, allow_analysis=True)

    @discord.ui.button(label="不允許", style=discord.ButtonStyle.secondary, row=0)
    async def deny_ai(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._choose_permission(interaction, allow_analysis=False)

    @discord.ui.button(label="完成設定", style=discord.ButtonStyle.success, row=1)
    async def finish(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.user.id != self.author_id:
            await _ephemeral_error(interaction, "只有原發文者可以完成設定。")
            return
        if self.ai_permission is None:
            await _ephemeral_error(interaction, "請先選擇是否允許 AI 分析文字內容。")
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            case_number, title = await self.service.finalize_draft(
                interaction,
                thread_id=self.thread_id,
                keyword_raw=self.keyword,
                ai_permission=self.ai_permission,
            )
        except (RuntimeError, PermissionError, KeywordValidationError) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        await interaction.followup.send(
            f"設定完成。\n標題：`{title}`\n案號：`{case_number}`",
            ephemeral=True,
        )
        self.stop()

    @discord.ui.button(label="取消", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.user.id != self.author_id:
            await _ephemeral_error(interaction, "只有原發文者可以操作。")
            return
        await interaction.response.edit_message(content="已取消設定。", view=None)
        self.stop()


class DraftSetupView(discord.ui.View):
    def __init__(self, service: CourseService) -> None:
        super().__init__(timeout=None)
        self.service = service

    @discord.ui.button(
        label="設定這篇文章",
        style=discord.ButtonStyle.primary,
        custom_id="course:draft:setup:v1",
    )
    async def setup(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            await _ephemeral_error(interaction, "這個按鈕只能在 Forum 文章內使用。")
            return
        draft = self.service.repo.get_draft(channel.id)
        if draft is None:
            await _ephemeral_error(interaction, "找不到草稿；可能已經完成設定。")
            return
        if int(draft["author_id"]) != interaction.user.id:
            await _ephemeral_error(interaction, "只有原發文者可以設定這篇文章。")
            return
        await interaction.response.send_modal(
            KeywordModal(self.service, channel.id, int(draft["author_id"]))
        )

    @discord.ui.button(
        label="我沒有問題了，刪除貼文",
        style=discord.ButtonStyle.danger,
        custom_id="course:draft:delete:v1",
    )
    async def delete(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            await _ephemeral_error(interaction, "這個按鈕只能在 Forum 文章內使用。")
            return
        draft = self.service.repo.get_draft(channel.id)
        if draft is None or int(draft["author_id"]) != interaction.user.id:
            await _ephemeral_error(interaction, "只有原發文者可以刪除草稿。")
            return
        await interaction.response.send_message("正在刪除草稿。", ephemeral=True)
        try:
            await self.service.delete_draft(interaction, channel.id)
        except (RuntimeError, PermissionError, discord.HTTPException) as exc:
            LOGGER.warning("Draft deletion failed for thread %s: %s", channel.id, exc)
            await interaction.followup.send(
                "刪除失敗，貼文仍保留；請稍後重試或聯絡教學團隊。",
                ephemeral=True,
            )

    @discord.ui.button(
        label="隱私與資料說明",
        style=discord.ButtonStyle.secondary,
        custom_id="course:draft:privacy:v1",
    )
    async def privacy(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "**資料與隱私說明**\n"
            "- 可見範圍：目前 Forum 頻道成員。\n"
            "- AI 選項只控制文字正文是否可交由 AI 分析。\n"
            "- 成案時只保存案件所需資料與 Discord 附件參照。\n"
            "- 是否允許 AI 分析會逐案記錄，不會沿用到其他案件。",
            ephemeral=True,
        )


class CloseConfirmView(discord.ui.View):
    def __init__(self, service: CourseService, *, actor_id: int, thread_id: int) -> None:
        super().__init__(timeout=120)
        self.service = service
        self.actor_id = actor_id
        self.thread_id = thread_id

    @discord.ui.button(label="確認結案", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.actor_id:
            await _ephemeral_error(interaction, "只有發起結案的人可以確認。")
            return
        if not isinstance(interaction.user, discord.Member) or not isinstance(
            interaction.channel, (discord.Thread, discord.TextChannel)
        ):
            await _ephemeral_error(interaction, "請在案件討論串內操作。")
            return
        try:
            await self.service.close_case(interaction.channel, interaction.user)
        except (RuntimeError, PermissionError) as exc:
            await _ephemeral_error(interaction, str(exc))
            return
        button.disabled = True
        await interaction.response.edit_message(
            content="已收到；案件正在結案。完成後會更新標題並封存討論串。",
            view=self,
        )
        self.stop()

    @discord.ui.button(label="取消", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.user.id != self.actor_id:
            await _ephemeral_error(interaction, "只有發起結案的人可以取消。")
            return
        await interaction.response.edit_message(content="已取消結案。", view=None)
        self.stop()


class ReopenView(discord.ui.View):
    def __init__(self, service: CourseService) -> None:
        super().__init__(timeout=None)
        self.service = service

    @discord.ui.button(
        label="繼續詢問",
        style=discord.ButtonStyle.primary,
        custom_id="course:case:reopen:v1",
    )
    async def reopen(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        channel = interaction.channel
        if not isinstance(channel, (discord.Thread, discord.TextChannel)):
            await _ephemeral_error(interaction, "這個按鈕只能在案件討論串內使用。")
            return
        retry_after = self.service.interaction_retry_after(
            "case-reopen", interaction.user.id, channel.id
        )
        if retry_after is not None:
            await interaction.response.send_message(
                f"操作太頻繁，請約 {retry_after} 秒後再試。", ephemeral=True
            )
            return
        try:
            self.service.claim_reopen(interaction.user.id, channel.id)
        except (RuntimeError, PermissionError) as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        _.disabled = True
        await interaction.response.send_message(
            "已收到；案件正在重新開啟。完成後會在討論串通知您。",
            ephemeral=True,
        )
        if interaction.message is not None:
            try:
                await interaction.message.edit(view=self)
            except discord.HTTPException:
                LOGGER.warning("Could not disable a claimed reopen button")

    @discord.ui.button(
        label="隱私與資料說明",
        style=discord.ButtonStyle.secondary,
        custom_id="course:case:privacy:v1",
    )
    async def privacy(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "繼續詢問會沿用同一個討論串與案號，不會再寄送新的案號。",
            ephemeral=True,
        )


if TYPE_CHECKING:
    from .service import CourseService
