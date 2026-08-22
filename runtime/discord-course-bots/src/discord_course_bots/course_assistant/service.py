from __future__ import annotations

import asyncio
import json
import logging
import uuid

import discord

from discord_course_bots.domain.keyword import normalize_keyword
from discord_course_bots.domain.titles import canonical_title, closed_title, cycle_title
from discord_course_bots.jobs import DiscordLifecycleClaim
from discord_course_bots.repository import Repository
from discord_course_bots.settings import CourseAssistantSettings

from .interaction_throttle import InteractionThrottle

LOGGER = logging.getLogger(__name__)


class CaseAlreadyOpenError(RuntimeError):
    """Raised when a stale reopen control is used after the case was reopened."""


class CourseService:
    def __init__(self, bot: discord.Client, settings: CourseAssistantSettings, repo: Repository):
        self.bot = bot
        self.settings = settings
        self.repo = repo
        self.interaction_throttle = InteractionThrottle()

    def interaction_retry_after(self, action: str, user_id: int, resource_id: int) -> int | None:
        return self.interaction_throttle.retry_after((action, user_id, resource_id))

    def is_allowed_operator(self, member: discord.Member) -> bool:
        if member.guild.owner_id == member.id:
            return True
        return member.id in self.settings.owner_ids

    def is_staff(self, member: discord.Member) -> bool:
        if self.is_allowed_operator(member) or member.guild_permissions.manage_threads:
            return True
        staff_ids = {
            value
            for key in ("ta_role_id", "professor_role_id")
            if (value := self.repo.get_config_int(key)) is not None
        }
        return any(role.id in staff_ids for role in member.roles)

    def configured_forum_ids(self) -> set[int]:
        values = self.repo.get_config("managed_forum_ids")
        if values:
            try:
                decoded = json.loads(values)
                if isinstance(decoded, list):
                    return {int(value) for value in decoded}
            except (TypeError, ValueError, json.JSONDecodeError):
                LOGGER.warning("managed_forum_ids is invalid; using legacy public forum")
        value = self.repo.get_config_int("public_forum_channel_id")
        return set() if value is None else {value}

    async def register_new_thread(self, thread: discord.Thread) -> None:
        if thread.guild.id != self.settings.test_guild_id:
            return
        if thread.parent_id not in self.configured_forum_ids():
            return
        if self.repo.get_draft(thread.id) or self.repo.get_case_by_thread(thread.id):
            return

        starter: discord.Message | None = None
        for _ in range(5):
            try:
                starter = await thread.fetch_message(thread.id)
                break
            except discord.NotFound:
                await asyncio.sleep(0.5)
            except discord.HTTPException:
                break
        if starter is None:
            LOGGER.warning("Unable to fetch starter message for forum thread %s", thread.id)
            return

        self.repo.create_draft(
            thread_id=thread.id,
            forum_channel_id=thread.parent_id or 0,
            author_id=starter.author.id,
            original_title=thread.name,
            starter_message_id=starter.id,
        )
        from .views import DraftSetupView

        message = await thread.send(
            "🤖 **微積分課程助理（測試版）**\n\n"
            "完成以下設定，以正式成立案件。\n"
            "- 關鍵字：尚未設定\n"
            "- AI 文字內容分析：尚未選擇\n\n"
            "請在設定期限內完成。",
            view=DraftSetupView(self),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.repo.set_draft_setup_message(thread.id, message.id)

    async def finalize_draft(
        self,
        interaction: discord.Interaction,
        *,
        thread_id: int,
        keyword_raw: str,
        ai_permission: bool,
    ) -> tuple[str, str]:
        draft = self.repo.get_draft(thread_id)
        if draft is None:
            raise RuntimeError("找不到草稿；可能已被處理。")
        if int(draft["author_id"]) != interaction.user.id:
            raise PermissionError("只有原發文者可以完成設定。")
        existing = self.repo.get_case_by_thread(thread_id)
        if existing is not None:
            return str(existing["case_number"]), str(existing["canonical_title"])

        keyword = normalize_keyword(keyword_raw)
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            raise RuntimeError("這個操作只能在 Forum 文章內執行。")
        starter_id = int(draft["starter_message_id"])
        starter = await channel.fetch_message(starter_id)
        title = canonical_title(
            self.settings.module_code,
            keyword,
            str(draft["original_title"]),
        )
        await channel.edit(name=title, reason="Course case finalized")

        snapshot = {
            "title": title,
            "body": starter.content,
            "thread_id": channel.id,
            "starter_message_id": starter.id,
            "created_at": starter.created_at.isoformat(),
            "attachments": [
                {
                    "attachment_id": attachment.id,
                    "filename": attachment.filename,
                    "content_type": attachment.content_type,
                    "size": attachment.size,
                    "discord_url": attachment.url,
                    "message_id": starter.id,
                }
                for attachment in starter.attachments
            ],
        }
        case_number = self.repo.create_case(
            case_id=str(uuid.uuid4()),
            thread_id=channel.id,
            author_id=interaction.user.id,
            module_code=self.settings.module_code,
            keyword=keyword,
            ai_content_permission=ai_permission,
            canonical_title=title,
            initial_snapshot=snapshot,
        )

        setup_message_id = draft["setup_message_id"]
        if setup_message_id:
            try:
                setup_message = await channel.fetch_message(int(setup_message_id))
                await setup_message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                LOGGER.warning("Could not delete setup message in thread %s", channel.id)

        dm_sent = False
        try:
            await interaction.user.send(
                f"您的測試案件已成立。\n案號：`{case_number}`\n文章：{channel.jump_url}"
            )
            dm_sent = True
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.info(
                "DM failed for user %s; Email fallback is pending backend", interaction.user.id
            )

        if dm_sent:
            await channel.send("✅ 您的貼文已成立。案號已透過 Discord 私訊寄送。")
        else:
            await channel.send(
                "✅ 您的貼文已成立。Discord 私訊無法送達；"
                "Email fallback 已記錄，但測試版尚未接通寄信後端。"
            )
        return case_number, title

    async def delete_draft(self, interaction: discord.Interaction, thread_id: int) -> None:
        draft = self.repo.get_draft(thread_id)
        if draft is None:
            raise RuntimeError("找不到草稿。")
        if int(draft["author_id"]) != interaction.user.id:
            raise PermissionError("只有原發文者可以刪除草稿。")
        self.repo.mark_draft_deleted(thread_id, "AUTHOR_CANCELLED")
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.delete(reason="Draft cancelled by original author")

    async def reconcile_title(self, thread: discord.Thread) -> None:
        case = self.repo.get_case_by_thread(thread.id)
        if case is None:
            return
        desired = cycle_title(str(case["base_title"]), int(case["reopen_count"]))
        status = str(case["status"])
        if status == "CLOSED":
            desired = closed_title(desired, automatic=False)
        elif status == "AUTO_CLOSED":
            desired = closed_title(desired, automatic=True)
        if thread.name != desired:
            await thread.edit(name=desired, reason="Restore system case prefix")
            self.repo.update_case_title(thread.id, desired)

    async def close_case(self, thread: discord.Thread) -> None:
        case = self.repo.get_case_by_thread(thread.id)
        if case is None:
            raise RuntimeError("這個討論串尚未成案。")
        if str(case["status"]) != "TRACKED":
            raise RuntimeError("案件不是進行中狀態。")
        if self.repo.has_unfinished_discord_lifecycle_job(str(case["case_id"])):
            raise RuntimeError("上一個案件操作仍在處理中，請稍後再試。")
        if self.repo.close_case(thread.id) is None:
            raise RuntimeError("案件目前無法結案，請稍後再試。")

    def claim_reopen(self, author_id: int, thread_id: int):
        case = self.repo.get_case_by_thread(thread_id)
        if case is None:
            raise RuntimeError("找不到案件。")
        if int(case["author_id"]) != author_id:
            raise PermissionError("只有原發文者可以繼續詢問。")
        if self.repo.has_unfinished_discord_lifecycle_job(str(case["case_id"])):
            raise RuntimeError("結案仍在處理中；完成後即可繼續詢問。")
        updated = self.repo.reopen_case(thread_id)
        if updated is None:
            current = self.repo.get_case_by_thread(thread_id)
            if current is not None and str(current["status"]) == "TRACKED":
                raise CaseAlreadyOpenError(
                    "案件目前已經開啟；請先繼續提問，待再次結案後才能重新開啟下一輪。"
                )
            raise RuntimeError("案件無法重新開啟。")
        return updated

    async def apply_discord_lifecycle_job(self, claim: DiscordLifecycleClaim) -> None:
        job = self.repo.get_discord_lifecycle_job(claim.job_id)
        if job is None:
            raise RuntimeError("LIFECYCLE_JOB_MISSING")
        channel = self.bot.get_channel(int(job["thread_id"]))
        if channel is None:
            channel = await self.bot.fetch_channel(int(job["thread_id"]))
        if not isinstance(channel, discord.Thread):
            raise RuntimeError("LIFECYCLE_THREAD_INVALID")

        transition = str(job["transition"])
        stage = str(job["stage"])
        cycle_number = int(job["cycle_number"])
        desired_title = str(job["desired_title"])
        if transition == "CLOSE":
            if stage == "PENDING":
                from .views import ReopenView

                notice = await channel.send(
                    f"✅ **第 {cycle_number} 次提問已結束。**\n\n還想繼續詢問嗎？",
                    view=ReopenView(self),
                )
                if not self.repo.mark_discord_lifecycle_stage(
                    claim.job_id,
                    claim.claim_token,
                    "NOTICE_SENT",
                    control_message_id=notice.id,
                ):
                    raise RuntimeError("LIFECYCLE_CLAIM_LOST")
            await channel.edit(
                name=desired_title,
                archived=True,
                locked=False,
                reason="Course case closed",
            )
        elif transition == "REOPEN":
            if stage == "PENDING":
                await channel.edit(
                    archived=False,
                    locked=False,
                    name=desired_title,
                    reason="Course case reopened",
                )
                if not self.repo.mark_discord_lifecycle_stage(
                    claim.job_id, claim.claim_token, "DISCORD_APPLIED"
                ):
                    raise RuntimeError("LIFECYCLE_CLAIM_LOST")
            if job["control_message_id"] is None:
                notice = await channel.send(
                    f"🔄 **第 {cycle_number} 次提問已開始。** 請繼續提出問題。"
                )
                if not self.repo.mark_discord_lifecycle_stage(
                    claim.job_id,
                    claim.claim_token,
                    "DISCORD_APPLIED",
                    control_message_id=notice.id,
                ):
                    raise RuntimeError("LIFECYCLE_CLAIM_LOST")
        else:
            raise RuntimeError("LIFECYCLE_TRANSITION_INVALID")

        self.repo.update_case_title(channel.id, desired_title)


def classify_discord_lifecycle_error(error: Exception) -> tuple[str, bool]:
    if isinstance(error, discord.Forbidden):
        return ("DISCORD_FORBIDDEN", False)
    if isinstance(error, discord.NotFound):
        return ("THREAD_NOT_FOUND", False)
    if isinstance(error, discord.HTTPException):
        return ("DISCORD_HTTP_ERROR", True)
    if isinstance(error, RuntimeError):
        code = str(error)
        if code in {
            "LIFECYCLE_JOB_MISSING",
            "LIFECYCLE_THREAD_INVALID",
            "LIFECYCLE_TRANSITION_INVALID",
        }:
            return (code, False)
        if code == "LIFECYCLE_CLAIM_LOST":
            return (code, True)
    return ("UNEXPECTED_ERROR", True)
