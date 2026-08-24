from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .service import CourseService, classify_discord_lifecycle_error

LOGGER = logging.getLogger(__name__)


async def _reply(interaction: discord.Interaction, message: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def _staff_allowed(member: discord.Member, service: CourseService) -> bool:
    return service.is_staff(member)


class CaseCog(commands.Cog):
    case = app_commands.Group(name="case", description="案件操作")
    private = app_commands.Group(name="private", description="隱密支援")
    ops = app_commands.Group(name="ops", description="管理者唯讀狀態命令")

    def __init__(self, bot: commands.Bot, service: CourseService) -> None:
        self.bot = bot
        self.service = service

    @case.command(name="close", description="由 Staff 關閉目前案件")
    async def close(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            await _reply(interaction, "請在課程 Discord 伺服器內使用。")
            return
        if not isinstance(interaction.channel, discord.Thread):
            await _reply(interaction, "請在案件 Forum thread 內執行。")
            return
        if not _staff_allowed(interaction.user, self.service):
            await _reply(interaction, "只有助教、教師或系統管理員可以結案。")
            return
        retry_after = self.service.interaction_retry_after(
            "case-close", interaction.user.id, interaction.channel.id
        )
        if retry_after is not None:
            await _reply(interaction, f"操作太頻繁，請約 {retry_after} 秒後再試。")
            return
        from .views import CloseConfirmView

        await interaction.response.send_message(
            "確定要結束這個案件嗎？結案後仍可沿用原案號重新開啟。",
            view=CloseConfirmView(
                self.service,
                actor_id=interaction.user.id,
                thread_id=interaction.channel.id,
            ),
            ephemeral=True,
        )

    @case.command(name="claim", description="接手目前案件")
    async def claim(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not self.service.is_staff(
            interaction.user
        ):
            await _reply(interaction, "只有助教、教師或系統管理員可以接手案件。")
            return
        if not isinstance(interaction.channel, discord.Thread):
            await _reply(interaction, "請在案件討論串內執行。")
            return
        row = self.service.repo.claim_case(interaction.channel.id, interaction.user.id)
        if row is None:
            await _reply(interaction, "這個案件已由其他人接手，或目前不能接手。")
            return
        await _reply(interaction, "已接手這個案件；後續結案由負責人或系統管理員操作。")

    @ops.command(name="status", description="查看不含個資的唯讀系統狀態")
    async def ops_status(self, interaction: discord.Interaction) -> None:
        if (
            interaction.guild is None
            or interaction.guild.id != self.service.settings.test_guild_id
            or not isinstance(interaction.user, discord.Member)
            or not self.service.is_allowed_operator(interaction.user)
        ):
            await _reply(interaction, "只有本伺服器的系統管理者可以查看狀態。")
            return
        snapshot = self.service.repo.safe_runtime_status()
        expected = ("course-assistant", "dump-bot", "data-bridge")
        states = {item["service"]: item["state"] for item in snapshot["health"]}
        labels = {
            "course-assistant": "課程助理",
            "dump-bot": "封存服務",
            "data-bridge": "雲端同步",
        }
        health_lines = [f"- {labels[key]}：{states.get(key, '尚無回報')}" for key in expected]
        queues = snapshot["queues"]
        failures = snapshot["failures"]
        await _reply(
            interaction,
            "**系統狀態（唯讀）**\n"
            + "\n".join(health_lines)
            + f"\n- 資料庫結構：v{snapshot['schema_version']}"
            + f"\n- 待完成案件操作：{queues['discord']}"
            + f"\n- 待同步雲端更新：{queues['projection']}"
            + f"\n- 待處理私人匯出：{queues['private_dump']}"
            + "\n- 需人工處理："
            + str(failures["discord"] + failures["projection"] + failures["private_dump"]),
        )

    @private.command(name="open", description="建立隱密支援空間")
    @app_commands.describe(ai_permission="是否允許 AI 分析文字正文")
    async def private_open(self, interaction: discord.Interaction, ai_permission: bool) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await _reply(interaction, "請在課程 Discord 伺服器內使用。")
            return
        request = self.service.repo.begin_private_open_request(
            interaction_id=str(interaction.id),
            guild_id=interaction.guild.id,
            requester_id=interaction.user.id,
            ai_content_permission=ai_permission,
            capacity=self.service.settings.private_open_capacity,
        )
        if str(request["status"]) == "REJECTED":
            await _reply(interaction, "操作太頻繁，請稍後再試。")
            return
        if str(request["status"]) == "COMPLETED":
            await _reply(interaction, f"這個申請已完成：{request['jump_url']}")
            return
        if str(request["rejection_code"] or "") == "CAPACITY_WAIT":
            await _reply(interaction, "已收到，正在等待建立。完成後會用 Discord 私訊通知您。")
            return
        category_id = self.service.repo.get_config_int("private_support_category_id")
        if category_id is None:
            await _reply(interaction, "隱密支援目前尚未開放，請聯絡教學團隊。")
            return
        await _reply(interaction, "已收到，正在建立隱密支援。完成後會用 Discord 私訊通知您。")

    @private.command(name="close", description="由 Staff 結束 Private Support，準備匯出")
    async def private_close(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not _staff_allowed(
            interaction.user, self.service
        ):
            await _reply(interaction, "只有助教、教師或系統管理員可以結案。")
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await _reply(interaction, "請在 Private Support 頻道內執行。")
            return
        case = self.service.repo.get_case_by_thread(interaction.channel.id)
        if case is None:
            await _reply(interaction, "這個頻道不是隱密支援案件。")
            return
        if str(case["status"]) == "OPEN":
            self.service.repo.claim_case(interaction.channel.id, interaction.user.id)
        from .views import CloseConfirmView

        await interaction.response.send_message(
            "確定要結束這個隱密支援案件嗎？頻道與資料會保留，也可以重新開啟。",
            view=CloseConfirmView(
                self.service,
                actor_id=interaction.user.id,
                thread_id=interaction.channel.id,
            ),
            ephemeral=True,
        )

    async def private_dump(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not _staff_allowed(
            interaction.user, self.service
        ):
            await _reply(interaction, "只有 TA／Professor／測試管理者可要求匯出。")
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await _reply(interaction, "請在 Private Support 頻道內執行。")
            return
        if not self.service.repo.queue_private_dump(interaction.channel.id, interaction.user.id):
            await _reply(interaction, "此頻道尚未結案，或已有匯出工作。")
            return
        await _reply(interaction, "Private dump 已排入工作；驗證完成後將刪除此頻道。")


class CourseManagerCog(commands.Cog):
    review = app_commands.Group(name="join-review", description="加入申請審核")
    admin = app_commands.Group(name="join-admin", description="Course Manager 系統管理")

    def __init__(self, bot: commands.Bot, service: CourseService) -> None:
        self.bot = bot
        self.service = service

    async def _require_reviewer(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member) or not self.service.is_reviewer(
            interaction.user
        ):
            await _reply(interaction, "只有已授權的助教、教師或系統管理員可以審核申請。")
            return False
        return True

    async def _require_admin(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member) or not self.service.is_allowed_operator(
            interaction.user
        ):
            await _reply(interaction, "只有系統管理員可以執行這個操作。")
            return False
        return True

    @review.command(name="queue", description="查看待審核申請的必要欄位")
    async def queue(self, interaction: discord.Interaction) -> None:
        if not await self._require_reviewer(interaction):
            return
        rows = self.service.repo.pending_join_applications(limit=10)
        if not rows:
            await _reply(interaction, "目前沒有待審核的加入申請。")
            return
        lines = []
        for row in rows:
            detail = row["class_code"] or row["visit_reason"] or "—"
            lines.append(
                f"`{row['application_id']}`｜{row['applicant_type']}｜"
                f"{row['discord_username']}｜{detail}｜{row['status']}"
            )
        await _reply(interaction, "**待審核申請**\n" + "\n".join(lines))

    @review.command(name="waiting", description="標記為等待 Discord 成員")
    async def waiting(self, interaction: discord.Interaction, application_id: str) -> None:
        if not await self._require_reviewer(interaction):
            return
        try:
            self.service.repo.transition_join_application(
                application_id,
                action="WAITING",
                actor_id=interaction.user.id,
                reason_code="MEMBER_NOT_FOUND",
            )
        except RuntimeError:
            await _reply(interaction, "找不到這筆申請。")
            return
        await _reply(interaction, "已保留申請並標記為等待加入 Discord；不會刪除資料。")

    @review.command(name="reject", description="拒絕加入申請")
    async def reject(
        self, interaction: discord.Interaction, application_id: str, reason: str
    ) -> None:
        if not await self._require_reviewer(interaction):
            return
        try:
            self.service.repo.transition_join_application(
                application_id,
                action="REJECT",
                actor_id=interaction.user.id,
                reason_code=reason.strip()[:64] or "REJECTED_BY_REVIEWER",
            )
        except RuntimeError:
            await _reply(interaction, "找不到這筆申請。")
            return
        await _reply(interaction, "已拒絕申請；通知會透過 Discord 私訊送出。")

    @review.command(name="approve", description="核准並套用課程角色")
    async def approve(self, interaction: discord.Interaction, application_id: str) -> None:
        if not await self._require_reviewer(interaction):
            return
        row = self.service.repo.get_join_application(application_id)
        if row is None:
            await _reply(interaction, "找不到這筆申請。")
            return
        if row["discord_user_id"] is None:
            self.service.repo.transition_join_application(
                application_id,
                action="WAITING",
                actor_id=interaction.user.id,
                reason_code="MEMBER_NOT_FOUND",
            )
            await _reply(interaction, "尚未解析到 Discord 成員；申請已保留並改為等待加入。")
            return
        role_ids = [self.service.repo.get_config_int("course_role_id")]
        if row["applicant_type"] == "VISITOR":
            role_ids.append(self.service.repo.get_config_int("visitor_role_id"))
        elif row["class_code"]:
            role_ids.append(self.service.repo.get_config_int(f"class_role_{row['class_code']}"))
        if any(value is None for value in role_ids):
            await _reply(interaction, "課程角色設定尚未完成；申請保持待審核。")
            return
        nickname = None if row["applicant_type"] == "VISITOR" else str(row["class_code"])
        self.service.repo.transition_join_application(
            application_id,
            action="APPROVE",
            actor_id=interaction.user.id,
            reason_code="REVIEW_APPROVED",
            desired_role_ids=tuple(int(value) for value in role_ids if value is not None),
            desired_nickname=nickname,
        )
        await _reply(
            interaction,
            "已核准；Course Manager 正在套用角色與暱稱。完成後會用 Discord 私訊通知。",
        )

    @admin.command(name="grant", description="新增或更新審核者")
    async def grant(
        self, interaction: discord.Interaction, member: discord.Member, system_admin: bool = False
    ) -> None:
        if not await self._require_admin(interaction):
            return
        level = "SYSTEM_ADMIN" if system_admin else "REVIEWER"
        self.service.repo.set_reviewer_grant(
            member.id, level=level, actor_id=interaction.user.id, active=True
        )
        await _reply(interaction, "已更新 Course Manager 授權。")

    @admin.command(name="revoke", description="撤銷審核者")
    async def revoke(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if not await self._require_admin(interaction):
            return
        level = self.service.repo.reviewer_level(member.id) or "REVIEWER"
        self.service.repo.set_reviewer_grant(
            member.id, level=level, actor_id=interaction.user.id, active=False
        )
        await _reply(interaction, "已撤銷 Course Manager 授權。")

    @admin.command(name="archive", description="可逆封存加入申請")
    async def archive(
        self, interaction: discord.Interaction, application_id: str, reason: str
    ) -> None:
        if not await self._require_admin(interaction):
            return
        try:
            self.service.repo.archive_join_application(
                application_id, actor_id=interaction.user.id, reason=reason
            )
        except RuntimeError:
            await _reply(interaction, "找不到這筆申請。")
            return
        await _reply(interaction, "已可逆封存；資料與前一狀態均已保留。")

    @admin.command(name="restore", description="還原已封存申請")
    async def restore(self, interaction: discord.Interaction, application_id: str) -> None:
        if not await self._require_admin(interaction):
            return
        try:
            self.service.repo.restore_join_application(application_id, actor_id=interaction.user.id)
        except RuntimeError:
            await _reply(interaction, "這筆申請不存在或目前不是已封存狀態。")
            return
        await _reply(interaction, "已還原申請到封存前狀態。")


class DraftLifecycleCog(commands.Cog):
    def __init__(self, bot: commands.Bot, service: CourseService) -> None:
        self.bot = bot
        self.service = service
        self.lifecycle_worker_id = f"course-assistant-{uuid.uuid4().hex}"
        self.lifecycle_tasks: set[asyncio.Task[None]] = set()
        self.side_effect_tasks: set[asyncio.Task[None]] = set()
        self.draft_sweep.start()
        self.lifecycle_sweep.start()
        self.case_idle_sweep.start()
        self.dm_sweep.start()
        self.private_open_sweep.start()
        self.course_role_sweep.start()

    def cog_unload(self) -> None:
        self.draft_sweep.cancel()
        self.lifecycle_sweep.cancel()
        self.case_idle_sweep.cancel()
        self.dm_sweep.cancel()
        self.private_open_sweep.cancel()
        self.course_role_sweep.cancel()
        for task in self.lifecycle_tasks:
            task.cancel()
        for task in self.side_effect_tasks:
            task.cancel()

    @tasks.loop(seconds=2)
    async def lifecycle_sweep(self) -> None:
        available = 4 - len(self.lifecycle_tasks)
        for _ in range(available):
            claim = self.service.repo.claim_discord_lifecycle_job(self.lifecycle_worker_id)
            if claim is None:
                return
            task = asyncio.create_task(self._run_lifecycle_claim(claim))
            self.lifecycle_tasks.add(task)
            task.add_done_callback(self.lifecycle_tasks.discard)

    async def _run_lifecycle_claim(self, claim) -> None:
        try:
            await self.service.apply_discord_lifecycle_job(claim)
        except Exception as exc:  # noqa: BLE001 - queue boundary records safe codes
            error_code, retryable = classify_discord_lifecycle_error(exc)
            self.service.repo.fail_discord_lifecycle_job(
                claim.job_id,
                claim.claim_token,
                error_code=error_code,
                retryable=retryable,
            )
            LOGGER.exception("Discord lifecycle job failed with %s", error_code)
            return
        if not self.service.repo.complete_discord_lifecycle_job(claim.job_id, claim.claim_token):
            LOGGER.error("Discord lifecycle job lost its claim before completion")

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
        now = datetime.now(UTC)
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
                                f"您在 `{thread.name}` 的草稿尚未完成設定：{thread.jump_url}"
                            )
                        except discord.HTTPException:
                            LOGGER.info(
                                "Draft reminder DM failed for %s; Email fallback pending",
                                draft["author_id"],
                            )
                    self.service.repo.mark_draft_reminded(thread.id)
            except discord.HTTPException:
                LOGGER.exception(
                    "Draft lifecycle operation failed for thread %s", draft["thread_id"]
                )

    @tasks.loop(seconds=60)
    async def case_idle_sweep(self) -> None:
        self.service.repo.mark_due_cases_idle(self.service.settings.case_idle_seconds)
        self.service.repo.auto_close_due_cases(self.service.settings.case_auto_close_seconds)

    @tasks.loop(seconds=10)
    async def dm_sweep(self) -> None:
        for row in self.service.repo.pending_dm_messages():
            user = self.bot.get_user(int(row["recipient_id"]))
            if user is None:
                try:
                    user = await self.bot.fetch_user(int(row["recipient_id"]))
                except discord.HTTPException:
                    user = None
            if user is None:
                self.service.repo.fail_dm_message(str(row["message_key"]), "USER_NOT_FOUND")
                continue
            try:
                await user.send(str(row["body"]))
            except discord.Forbidden:
                self.service.repo.fail_dm_message(str(row["message_key"]), "DM_BLOCKED")
            except discord.HTTPException:
                continue
            else:
                self.service.repo.complete_dm_message(str(row["message_key"]))

    @tasks.loop(seconds=2)
    async def private_open_sweep(self) -> None:
        if len(self.side_effect_tasks) >= 4:
            return
        claim = self.service.repo.claim_private_open_request(self.lifecycle_worker_id)
        if claim is None:
            return
        task = asyncio.create_task(self._run_private_open_claim(claim))
        self.side_effect_tasks.add(task)
        task.add_done_callback(self.side_effect_tasks.discard)

    async def _run_private_open_claim(self, claim) -> None:
        try:
            await self.service.apply_private_open_request(claim)
        except discord.Forbidden:
            self.service.repo.fail_private_open_request(
                claim.interaction_id,
                claim.claim_token,
                error_code="DISCORD_FORBIDDEN",
                retryable=False,
            )
        except (discord.HTTPException, RuntimeError):
            self.service.repo.fail_private_open_request(
                claim.interaction_id,
                claim.claim_token,
                error_code="PRIVATE_CREATE_RETRY",
                retryable=True,
            )

    @tasks.loop(seconds=2)
    async def course_role_sweep(self) -> None:
        if len(self.side_effect_tasks) >= 4:
            return
        claim = self.service.repo.claim_course_role_job(self.lifecycle_worker_id)
        if claim is None:
            return
        task = asyncio.create_task(self._run_course_role_claim(claim))
        self.side_effect_tasks.add(task)
        task.add_done_callback(self.side_effect_tasks.discard)

    async def _run_course_role_claim(self, claim) -> None:
        try:
            await self.service.apply_course_role_job(claim)
        except discord.Forbidden:
            self.service.repo.fail_course_role_job(
                claim.job_id,
                claim.claim_token,
                error_code="DISCORD_FORBIDDEN",
                retryable=False,
            )
        except (discord.HTTPException, RuntimeError, ValueError, json.JSONDecodeError):
            self.service.repo.fail_course_role_job(
                claim.job_id,
                claim.claim_token,
                error_code="COURSE_ROLE_RETRY",
                retryable=True,
            )

    @draft_sweep.before_loop
    async def before_draft_sweep(self) -> None:
        await self.bot.wait_until_ready()

    @private_delete_sweep.before_loop
    async def before_private_delete_sweep(self) -> None:
        await self.bot.wait_until_ready()

    @lifecycle_sweep.before_loop
    async def before_lifecycle_sweep(self) -> None:
        await self.bot.wait_until_ready()

    @case_idle_sweep.before_loop
    async def before_case_idle_sweep(self) -> None:
        await self.bot.wait_until_ready()

    @dm_sweep.before_loop
    async def before_dm_sweep(self) -> None:
        await self.bot.wait_until_ready()

    @private_open_sweep.before_loop
    async def before_private_open_sweep(self) -> None:
        await self.bot.wait_until_ready()

    @course_role_sweep.before_loop
    async def before_course_role_sweep(self) -> None:
        await self.bot.wait_until_ready()
