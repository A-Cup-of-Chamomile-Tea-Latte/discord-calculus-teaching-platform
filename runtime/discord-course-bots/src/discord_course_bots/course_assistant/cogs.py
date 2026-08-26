from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from discord_course_bots.domain.applicants import normalize_class_code
from discord_course_bots.domain.keyword import normalize_keyword

from .service import CourseService, PrivateDumpPending, classify_discord_lifecycle_error

LOGGER = logging.getLogger(__name__)
STATIC_ROLE_CONFIG_KEYS = frozenset(
    {
        "course_role_id",
        "visitor_role_id",
        "ta_role_id",
        "professor_role_id",
        "system_admin_role_id",
    }
)


def normalized_role_config_key(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in STATIC_ROLE_CONFIG_KEYS:
        return normalized
    match = re.fullmatch(r"class_role_(0[1-9]|1[0-6])", normalized)
    if match is None:
        raise ValueError("不支援的角色設定鍵。")
    return f"class_role_{match.group(1)}"


def normalized_class_module(class_code: str, module_code: str) -> tuple[str, str]:
    normalized_class = normalize_class_code(class_code)
    normalized_module = module_code.strip().upper()
    if normalized_module not in {"M1", "M2", "M3", "M4"}:
        raise ValueError("Module 必須是 M1 至 M4。")
    return normalized_class, normalized_module


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
    ops = app_commands.Group(name="ops", description="系統管理與人工接管")

    def __init__(self, bot: commands.Bot, service: CourseService) -> None:
        self.bot = bot
        self.service = service

    async def _require_operator(self, interaction: discord.Interaction) -> bool:
        allowed = (
            interaction.guild is not None
            and interaction.guild.id == self.service.settings.test_guild_id
            and isinstance(interaction.user, discord.Member)
            and self.service.is_allowed_operator(interaction.user)
        )
        if not allowed:
            await _reply(interaction, "只有本伺服器的系統管理者可以執行此操作。")
        return bool(allowed)

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
        if not await self._require_operator(interaction):
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
            + f"\n- 待發 Discord 私訊：{queues['dm']}"
            + f"\n- 待建立隱密支援：{queues['private_open']}"
            + f"\n- 待套用加入權限：{queues['course_role']}"
            + f"\n- 待寄 Email 驗證：{queues['email']}"
            + f"\n- 歷史 Private dump queue：{queues['private_dump']}"
            + f"\n- 需人工處理：{sum(failures.values())}",
        )

    @ops.command(name="attention-list", description="列出不含內容與個資的人工接管項目")
    async def attention_list(self, interaction: discord.Interaction) -> None:
        if not await self._require_operator(interaction):
            return
        items = self.service.repo.list_manual_attention(limit=10)
        if not items:
            await _reply(interaction, "目前沒有未解決的人工接管項目。")
            return
        lines = [
            f"`{item['kind']}`｜`{item['itemKey']}`｜{item['errorCode']}｜"
            f"嘗試 {item['attempts']} 次"
            for item in items
        ]
        await _reply(interaction, "**人工接管清單（不含內容／個資）**\n" + "\n".join(lines))

    @ops.command(name="attention-inspect", description="檢查一個人工接管項目的安全狀態")
    async def attention_inspect(
        self, interaction: discord.Interaction, queue_kind: str, item_key: str
    ) -> None:
        if not await self._require_operator(interaction):
            return
        try:
            item = self.service.repo.inspect_manual_attention(queue_kind, item_key)
        except (ValueError, TypeError):
            await _reply(interaction, "queue kind 或 item key 無效。")
            return
        if item is None:
            await _reply(interaction, "找不到這個人工接管項目。")
            return
        await _reply(
            interaction,
            f"`{item['kind']}`｜`{item['itemKey']}`\n"
            f"狀態：{item['status']}\n錯誤碼：{item['errorCode']}\n"
            f"嘗試：{item['attempts']}\n最後 owner 動作：{item['lastOwnerAction'] or '無'}",
        )

    @ops.command(name="attention-retry", description="重試 allowlisted 的 terminal failure")
    async def attention_retry(
        self,
        interaction: discord.Interaction,
        queue_kind: str,
        item_key: str,
        reason_code: str,
    ) -> None:
        if not await self._require_operator(interaction):
            return
        try:
            changed = self.service.repo.retry_manual_attention(
                queue_kind,
                item_key,
                actor_id=interaction.user.id,
                reason_code=reason_code.strip().upper(),
            )
        except (ValueError, TypeError):
            await _reply(interaction, "參數無效；reason_code 請用大寫英文、數字或底線。")
            return
        await _reply(
            interaction,
            "已重新排入可靠 queue。" if changed else "此項目目前不可安全重試。",
        )

    @ops.command(name="attention-resolve", description="標記 terminal failure 已由 owner 處理")
    async def attention_resolve(
        self,
        interaction: discord.Interaction,
        queue_kind: str,
        item_key: str,
        reason_code: str,
    ) -> None:
        if not await self._require_operator(interaction):
            return
        try:
            changed = self.service.repo.resolve_manual_attention(
                queue_kind,
                item_key,
                actor_id=interaction.user.id,
                reason_code=reason_code.strip().upper(),
            )
        except (ValueError, TypeError):
            await _reply(interaction, "參數無效；reason_code 請用大寫英文、數字或底線。")
            return
        await _reply(
            interaction, "已留下 owner resolve 稽核。" if changed else "找不到 terminal failure。"
        )

    @ops.command(name="replacement-case", description="為已自動刪除的 Private 案件建立新案件")
    async def replacement_case(
        self,
        interaction: discord.Interaction,
        previous_case_number: str,
        member: discord.Member,
        reason_code: str,
    ) -> None:
        if not await self._require_operator(interaction) or interaction.guild is None:
            return
        try:
            request = self.service.repo.create_replacement_private_request(
                previous_case_number=previous_case_number,
                requester_id=member.id,
                actor_id=interaction.user.id,
                reason_code=reason_code.strip().upper(),
                guild_id=interaction.guild.id,
                module_code=self.service.settings.module_code,
            )
        except (RuntimeError, ValueError):
            await _reply(interaction, "來源案件不可建立 replacement，或參數不安全。")
            return
        await _reply(
            interaction,
            f"已建立 replacement request `{request['interaction_id']}`；完成後會私訊當事人。",
        )

    @private.command(name="open", description="建立隱密支援空間")
    @app_commands.describe(
        keyword="與公開提問相同的主標籤", ai_permission="是否允許 AI 分析文字正文"
    )
    async def private_open(
        self, interaction: discord.Interaction, keyword: str, ai_permission: bool
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await _reply(interaction, "請在課程 Discord 伺服器內使用。")
            return
        try:
            normalized_keyword = normalize_keyword(keyword)
        except ValueError as exc:
            await _reply(interaction, str(exc))
            return
        module_code = self.service.private_module_for_member(interaction.user)
        request = self.service.repo.begin_private_open_request(
            interaction_id=str(interaction.id),
            guild_id=interaction.guild.id,
            requester_id=interaction.user.id,
            module_code=module_code,
            keyword=normalized_keyword,
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

    @private.command(name="close", description="由 Staff 結束隱密支援案件")
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
            "確定要結束這個隱密支援案件嗎？結案後 48 小時內仍可重新開啟；"
            "逾時會先完成 Private dump 驗證，再刪除受限頻道。",
            view=CloseConfirmView(
                self.service,
                actor_id=interaction.user.id,
                thread_id=interaction.channel.id,
            ),
            ephemeral=True,
        )


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

    @review.command(name="bind", description="將申請綁定到已加入伺服器的成員")
    async def bind(
        self,
        interaction: discord.Interaction,
        application_id: str,
        member: discord.Member,
    ) -> None:
        if not await self._require_reviewer(interaction):
            return
        try:
            self.service.repo.bind_join_discord_member(application_id, member.id)
        except RuntimeError as exc:
            message = (
                "這個 Discord 成員已綁定另一筆申請；請先由系統管理員核對重複資料。"
                if str(exc) == "DISCORD_MEMBER_ALREADY_BOUND"
                else "找不到可綁定的申請，或申請已封存。"
            )
            await _reply(interaction, message)
            return
        await _reply(interaction, "已綁定 Discord 成員；請重新核對資料後再執行核准。")

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
        if interaction.guild is None:
            await _reply(interaction, "請在課程 Discord 伺服器內執行。")
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        prefix = (
            "Guest_Visitor"
            if row["applicant_type"] == "VISITOR"
            else f"Student_{row['class_code']}"
        )
        pattern = re.compile(rf"^{re.escape(prefix)}(\d{{3}})$")
        observed_max = 0
        try:
            async for member in interaction.guild.fetch_members(limit=None):
                match = pattern.fullmatch(member.nick or "")
                if match is not None:
                    observed_max = max(observed_max, int(match.group(1)))
        except discord.Forbidden:
            await _reply(interaction, "Bot 無法讀取完整成員名單；申請保持待審核。")
            return
        except discord.HTTPException:
            await _reply(interaction, "Discord 成員名單暫時不可用；請稍後再核准。")
            return
        try:
            nickname = self.service.repo.reserve_course_alias(
                application_id, observed_max=observed_max
            )
        except RuntimeError:
            await _reply(interaction, "無法安全配置唯一暱稱；申請保持待審核。")
            return
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

    @admin.command(name="set-role", description="設定 Course Manager 的 allowlisted Discord 角色")
    @app_commands.describe(
        role_key="課程／訪客／staff role key，或 class_role_01–16",
        role="要套用的 Discord 角色",
    )
    async def set_role(
        self, interaction: discord.Interaction, role_key: str, role: discord.Role
    ) -> None:
        if not await self._require_admin(interaction):
            return
        try:
            key = normalized_role_config_key(role_key)
        except ValueError as exc:
            await _reply(interaction, str(exc))
            return
        self.service.repo.set_config(key, role.id)
        await _reply(interaction, f"已更新 `{key}`；請用測試帳號驗證角色層級後再核准申請。")

    @admin.command(name="set-category", description="設定 Private Support 的受限頻道分類")
    async def set_category(
        self, interaction: discord.Interaction, category: discord.CategoryChannel
    ) -> None:
        if not await self._require_admin(interaction):
            return
        self.service.repo.set_config("private_support_category_id", category.id)
        await _reply(
            interaction, "已更新 Private Support 分類；正式使用前仍須完成 ACL regression。"
        )

    @admin.command(name="add-forum", description="加入 Course Assistant 管理的提問 Forum")
    async def add_forum(
        self, interaction: discord.Interaction, forum: discord.ForumChannel
    ) -> None:
        if not await self._require_admin(interaction):
            return
        forum_ids = self.service.configured_forum_ids()
        forum_ids.add(forum.id)
        self.service.repo.set_config("managed_forum_ids", json.dumps(sorted(forum_ids)))
        await _reply(interaction, "已加入提問 Forum；請用測試文章驗證草稿與成案流程。")

    @admin.command(name="remove-forum", description="停止管理指定的提問 Forum")
    async def remove_forum(
        self, interaction: discord.Interaction, forum: discord.ForumChannel
    ) -> None:
        if not await self._require_admin(interaction):
            return
        forum_ids = self.service.configured_forum_ids()
        forum_ids.discard(forum.id)
        self.service.repo.set_config("managed_forum_ids", json.dumps(sorted(forum_ids)))
        await _reply(interaction, "已停止管理該 Forum；既有案件與歷史資料不會刪除。")

    @admin.command(name="set-module", description="設定正式班別對應的 Module")
    async def set_module(
        self, interaction: discord.Interaction, class_code: str, module_code: str
    ) -> None:
        if not await self._require_admin(interaction):
            return
        try:
            normalized_class, normalized_module = normalized_class_module(class_code, module_code)
        except ValueError as exc:
            await _reply(interaction, str(exc))
            return
        self.service.repo.set_config(f"class_module_{normalized_class}", normalized_module)
        await _reply(
            interaction,
            f"已設定 C{normalized_class} → {normalized_module}；請再與 115-1 對照複核。",
        )

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
        except PrivateDumpPending:
            if not self.service.repo.defer_discord_lifecycle_job(
                claim.job_id, claim.claim_token, delay_seconds=10
            ):
                LOGGER.error("Private dump wait lost lifecycle claim")
            return
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
                                "Draft reminder DM failed for %s; no email fallback",
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
        for _ in range(20):
            claim = self.service.repo.claim_dm_message(self.lifecycle_worker_id)
            if claim is None:
                return
            row = self.service.repo.get_dm_message(claim.message_key)
            if row is None:
                LOGGER.error("Claimed DM row disappeared")
                return
            user = self.bot.get_user(int(row["recipient_id"]))
            if user is None:
                try:
                    user = await self.bot.fetch_user(int(row["recipient_id"]))
                except discord.NotFound:
                    self.service.repo.fail_dm_message(
                        claim.message_key,
                        claim.claim_token,
                        error_code="USER_NOT_FOUND",
                        retryable=False,
                    )
                    continue
                except discord.HTTPException:
                    self.service.repo.fail_dm_message(
                        claim.message_key,
                        claim.claim_token,
                        error_code="DM_LOOKUP_RETRY",
                        retryable=True,
                    )
                    continue
            try:
                await user.send(str(row["body"]))
            except discord.Forbidden:
                self.service.repo.fail_dm_message(
                    claim.message_key,
                    claim.claim_token,
                    error_code="DM_BLOCKED",
                    retryable=False,
                )
            except discord.HTTPException:
                self.service.repo.fail_dm_message(
                    claim.message_key,
                    claim.claim_token,
                    error_code="DM_SEND_RETRY",
                    retryable=True,
                )
            else:
                self.service.repo.complete_dm_message(claim.message_key, claim.claim_token)

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
