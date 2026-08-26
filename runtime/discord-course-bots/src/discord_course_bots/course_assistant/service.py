from __future__ import annotations

import asyncio
import json
import logging
import uuid

import discord

from discord_course_bots.domain.keyword import normalize_keyword
from discord_course_bots.domain.titles import canonical_title, closed_title, cycle_title
from discord_course_bots.jobs import CourseRoleClaim, DiscordLifecycleClaim, PrivateOpenClaim
from discord_course_bots.repository import Repository
from discord_course_bots.settings import CourseAssistantSettings

from .interaction_throttle import InteractionThrottle

LOGGER = logging.getLogger(__name__)


class PrivateDumpPending(RuntimeError):
    """The private export prerequisite is still progressing normally."""


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
        if (
            member.id in self.settings.owner_ids
            or self.repo.reviewer_level(member.id) == "SYSTEM_ADMIN"
        ):
            return True
        system_admin_role_id = self.repo.get_config_int("system_admin_role_id")
        return system_admin_role_id is not None and any(
            role.id == system_admin_role_id for role in member.roles
        )

    def is_staff(self, member: discord.Member) -> bool:
        if self.is_allowed_operator(member) or self.repo.reviewer_level(member.id) == "REVIEWER":
            return True
        staff_ids = {
            value
            for key in ("ta_role_id", "professor_role_id")
            if (value := self.repo.get_config_int(key)) is not None
        }
        return any(role.id in staff_ids for role in member.roles)

    def is_reviewer(self, member: discord.Member) -> bool:
        return self.is_staff(member)

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

    def class_context_for_member(self, member: discord.Member) -> tuple[str, str]:
        member_role_ids = {role.id for role in member.roles}
        matches = [
            class_code
            for class_code in (f"{number:02d}" for number in range(1, 17))
            if (role_id := self.repo.get_config_int(f"class_role_{class_code}")) is not None
            and role_id in member_role_ids
        ]
        if len(matches) != 1:
            raise RuntimeError("無法確認唯一班別；請先請 Course Manager 檢查班級角色。")
        class_code = matches[0]
        module_code = self.repo.get_config(f"class_module_{class_code}")
        if module_code not in {"M1", "M2", "M3", "M4"}:
            raise RuntimeError("班別與 Module 對照尚未同步；請先請系統管理員更新設定。")
        return class_code, module_code

    def public_case_context_for_member(
        self, member: discord.Member
    ) -> tuple[str | None, str, bool]:
        """Resolve exactly one public identity without treating Guest as C00."""
        member_role_ids = {role.id for role in member.roles}
        guest_role_id = self.repo.get_config_int("visitor_role_id")
        is_guest = guest_role_id is not None and guest_role_id in member_role_ids
        class_matches = [
            class_code
            for class_code in (f"{number:02d}" for number in range(1, 17))
            if (role_id := self.repo.get_config_int(f"class_role_{class_code}")) is not None
            and role_id in member_role_ids
        ]
        if is_guest and class_matches:
            raise RuntimeError("Guest 與正式班級角色同時存在；請先請 Course Manager 修正角色。")
        if is_guest:
            return None, self.settings.module_code, True
        if len(class_matches) != 1:
            raise RuntimeError("無法確認唯一班別；請先請 Course Manager 檢查班級角色。")
        class_code = class_matches[0]
        module_code = self.repo.get_config(f"class_module_{class_code}")
        if module_code not in {"M1", "M2", "M3", "M4"}:
            raise RuntimeError("班別與 Module 對照尚未同步；請先請系統管理員更新設定。")
        return class_code, module_code, False

    def private_module_for_member(self, member: discord.Member) -> str:
        """Resolve Private Support metadata without weakening its channel ACL."""
        try:
            return self.class_context_for_member(member)[1]
        except RuntimeError:
            LOGGER.info(
                "Private Support requester %s has no unique class/module mapping; "
                "using the configured private metadata fallback",
                member.id,
            )
            return self.settings.module_code

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
            "🤖 **微積分課程助理**\n\n"
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

        if not isinstance(interaction.user, discord.Member):
            raise RuntimeError("無法讀取伺服器成員資料；請稍後再試。")
        class_code, module_code, is_guest = self.public_case_context_for_member(interaction.user)
        keyword = normalize_keyword(keyword_raw)
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            raise RuntimeError("這個操作只能在 Forum 文章內執行。")
        starter_id = int(draft["starter_message_id"])
        starter = await channel.fetch_message(starter_id)
        title = canonical_title(
            module_code,
            class_code,
            keyword,
            str(draft["original_title"]),
            guest=is_guest,
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
            module_code=module_code,
            keyword=keyword,
            ai_content_permission=ai_permission,
            canonical_title=title,
            initial_snapshot=snapshot,
            class_code=class_code,
            guest=is_guest,
        )

        setup_message_id = draft["setup_message_id"]
        if setup_message_id:
            try:
                setup_message = await channel.fetch_message(int(setup_message_id))
                await setup_message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                LOGGER.warning("Could not delete setup message in thread %s", channel.id)

        case = self.repo.get_case_by_thread(channel.id)
        self.repo.enqueue_case_dm(
            case_id=str(case["case_id"]),
            recipient_id=interaction.user.id,
            case_number=case_number,
            jump_url=channel.jump_url,
        )
        await channel.send("✅ 您的貼文已成立。案號與直達連結將透過 Discord 私訊寄送。")
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

    async def close_case(
        self, thread: discord.Thread | discord.TextChannel, actor: discord.Member
    ) -> None:
        case = self.repo.get_case_by_thread(thread.id)
        if case is None:
            raise RuntimeError("這個討論串尚未成案。")
        if str(case["status"]) not in {"TRACKED", "IDLE"}:
            raise RuntimeError("案件不是進行中狀態。")
        assigned = case["assigned_staff_id"]
        if assigned is None:
            claimed = self.repo.claim_case(thread.id, actor.id)
            if claimed is None:
                raise RuntimeError("請先接手案件，再進行結案。")
        elif int(assigned) != actor.id and not self.is_allowed_operator(actor):
            raise PermissionError("只有案件負責人或系統管理員可以結案。")
        if self.repo.has_unfinished_discord_lifecycle_job(str(case["case_id"])):
            raise RuntimeError("上一個案件操作仍在處理中，請稍後再試。")
        if self.repo.close_case(thread.id) is None:
            raise RuntimeError("案件目前無法結案，請稍後再試。")
        if str(case["visibility"]) == "PRIVATE":
            self.repo.close_private_support(thread.id)

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
            if current is not None and str(current["status"]) in {"OPEN", "TRACKED", "IDLE"}:
                raise CaseAlreadyOpenError(
                    "案件目前已經開啟；請先繼續提問，待再次結案後才能重新開啟下一輪。"
                )
            raise RuntimeError("案件無法重新開啟。")
        return updated

    async def apply_private_open_request(self, claim: PrivateOpenClaim) -> None:
        row = self.repo.get_private_open_request(claim.interaction_id)
        if row is None:
            raise RuntimeError("PRIVATE_REQUEST_MISSING")
        guild = self.bot.get_guild(int(row["guild_id"]))
        if guild is None:
            raise RuntimeError("PRIVATE_GUILD_UNAVAILABLE")
        requester = guild.get_member(int(row["requester_id"]))
        if requester is None:
            requester = await guild.fetch_member(int(row["requester_id"]))
        category_id = self.repo.get_config_int("private_support_category_id")
        category = guild.get_channel(category_id) if category_id else None
        if not isinstance(category, discord.CategoryChannel):
            raise RuntimeError("PRIVATE_CATEGORY_UNAVAILABLE")
        channel = guild.get_channel(int(row["channel_id"])) if row["channel_id"] else None
        if channel is None:
            me = guild.me
            if me is None:
                raise RuntimeError("PRIVATE_BOT_MEMBER_UNAVAILABLE")
            overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                ),
                requester: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                ),
            }
            for key in ("ta_role_id", "professor_role_id", "system_admin_role_id"):
                role_id = self.repo.get_config_int(key)
                role = guild.get_role(role_id) if role_id else None
                if role is not None:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True,
                    )
            direct_admin_ids = set(self.settings.owner_ids)
            direct_admin_ids.update(self.repo.active_system_admin_ids())
            direct_admin_ids.discard(requester.id)
            direct_admin_ids.discard(me.id)
            if len(direct_admin_ids) > 80:
                raise RuntimeError("PRIVATE_ADMIN_ACL_TOO_LARGE")
            for admin_id in sorted(direct_admin_ids):
                admin = guild.get_member(admin_id)
                if admin is None:
                    try:
                        admin = await guild.fetch_member(admin_id)
                    except discord.NotFound:
                        continue
                overwrites[admin] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                )
            channel = await guild.create_text_channel(
                name=f"private-{claim.interaction_id[-6:]}",
                category=category,
                overwrites=overwrites,
                reason="Private Support request",
            )
            if not self.repo.mark_private_channel_created(
                claim.interaction_id,
                claim.claim_token,
                channel_id=channel.id,
                jump_url=channel.jump_url,
            ):
                raise RuntimeError("PRIVATE_CLAIM_LOST")
        if not isinstance(channel, discord.TextChannel):
            raise RuntimeError("PRIVATE_CHANNEL_INVALID")
        completed = self.repo.complete_private_open_request(
            interaction_id=claim.interaction_id,
            channel_id=channel.id,
            jump_url=channel.jump_url,
            requester_id=int(row["requester_id"]),
            ai_content_permission=bool(row["ai_content_permission"]),
        )
        await channel.send(
            f"隱密支援案件已建立。案號：`{completed['case_number']}`\n"
            f"提出者：{requester.mention}\n"
            f"允許 AI 分析文字內容：**{'是' if row['ai_content_permission'] else '否'}**\n\n"
            "請直接在這裡貼上問題與圖片；只有您與授權教學團隊可見。",
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )

    async def apply_course_role_job(self, claim: CourseRoleClaim) -> None:
        job = self.repo.get_course_role_job(claim.job_id)
        if job is None:
            raise RuntimeError("COURSE_ROLE_JOB_MISSING")
        guild = self.bot.get_guild(self.settings.test_guild_id)
        if guild is None:
            raise RuntimeError("COURSE_GUILD_UNAVAILABLE")
        member = guild.get_member(int(job["discord_user_id"]))
        if member is None:
            member = await guild.fetch_member(int(job["discord_user_id"]))
        role_ids = [int(value) for value in json.loads(str(job["desired_roles_json"]))]
        roles = [guild.get_role(role_id) for role_id in role_ids]
        if any(role is None for role in roles):
            raise RuntimeError("COURSE_ROLE_CONFIG_INVALID")
        await member.add_roles(*roles, reason="Course Manager approval")
        nickname = job["desired_nickname"]
        if nickname:
            await member.edit(nick=str(nickname), reason="Course Manager approval")
        summary = str(nickname or "訪客")
        if not self.repo.complete_course_role_job(claim.job_id, claim.claim_token, summary):
            raise RuntimeError("COURSE_ROLE_CLAIM_LOST")

    async def apply_discord_lifecycle_job(self, claim: DiscordLifecycleClaim) -> None:
        job = self.repo.get_discord_lifecycle_job(claim.job_id)
        if job is None:
            raise RuntimeError("LIFECYCLE_JOB_MISSING")
        case = self.repo.get_case_by_thread(int(job["thread_id"]))
        is_private_auto_close = (
            case is not None
            and str(case["visibility"]) == "PRIVATE"
            and str(job["transition"]) == "AUTO_CLOSE"
        )
        if is_private_auto_close:
            dump = self.repo.get_private_dump_job(int(job["thread_id"]))
            if dump is None:
                try:
                    channel = self.bot.get_channel(int(job["thread_id"]))
                    if channel is None:
                        channel = await self.bot.fetch_channel(int(job["thread_id"]))
                except discord.NotFound:
                    channel = None
                if not isinstance(channel, discord.TextChannel):
                    raise RuntimeError("LIFECYCLE_THREAD_INVALID")
                if str(job["stage"]) == "PENDING":
                    support = self.repo.get_private_support(channel.id)
                    if support is None:
                        raise RuntimeError("PRIVATE_SUPPORT_RECORD_MISSING")
                    member = channel.guild.get_member(int(support["requester_id"]))
                    if member is None:
                        try:
                            member = await channel.guild.fetch_member(int(support["requester_id"]))
                        except discord.NotFound:
                            member = None
                    if member is not None:
                        overwrite = channel.overwrites_for(member)
                        overwrite.send_messages = False
                        await channel.set_permissions(
                            member,
                            overwrite=overwrite,
                            reason="Private Support retention expiry freeze",
                        )
                    notice = await channel.send(
                        "⏳ **隱密案件保存期限已到。**\n\n"
                        "系統正在建立經驗證的內容輸出；完成後會刪除此受限頻道。"
                    )
                    if not self.repo.mark_discord_lifecycle_stage(
                        claim.job_id,
                        claim.claim_token,
                        "NOTICE_SENT",
                        control_message_id=notice.id,
                    ):
                        raise RuntimeError("LIFECYCLE_CLAIM_LOST")
                if not self.repo.queue_private_dump(channel.id, requested_by=0):
                    raise RuntimeError("PRIVATE_DUMP_QUEUE_FAILED")
                raise PrivateDumpPending("WAITING_FOR_PRIVATE_DUMP")
            if str(dump["status"]) in {"PENDING", "CLAIMED"}:
                raise PrivateDumpPending("WAITING_FOR_PRIVATE_DUMP")
            if str(dump["status"]) == "FAILED":
                raise RuntimeError("PRIVATE_DUMP_FAILED")
            if str(dump["status"]) not in {"VERIFIED", "DELETED"}:
                raise RuntimeError("PRIVATE_DUMP_STATE_INVALID")
            try:
                channel = self.bot.get_channel(int(job["thread_id"]))
                if channel is None:
                    channel = await self.bot.fetch_channel(int(job["thread_id"]))
            except discord.NotFound:
                channel = None
            if channel is not None:
                if not isinstance(channel, discord.TextChannel):
                    raise RuntimeError("LIFECYCLE_THREAD_INVALID")
                await channel.delete(reason="Verified Private Support retention expiry")
            if not self.repo.mark_private_deleted(int(job["thread_id"])):
                raise RuntimeError("PRIVATE_DELETE_NOT_VERIFIED")
            if not self.repo.mark_discord_lifecycle_stage(
                claim.job_id, claim.claim_token, "DISCORD_APPLIED"
            ):
                raise RuntimeError("LIFECYCLE_CLAIM_LOST")
            return
        channel = self.bot.get_channel(int(job["thread_id"]))
        if channel is None:
            channel = await self.bot.fetch_channel(int(job["thread_id"]))
        if not isinstance(channel, (discord.Thread, discord.TextChannel)):
            raise RuntimeError("LIFECYCLE_THREAD_INVALID")
        is_thread = isinstance(channel, discord.Thread)

        transition = str(job["transition"])
        stage = str(job["stage"])
        cycle_number = int(job["cycle_number"])
        desired_title = str(job["desired_title"])
        if transition in {"CLOSE", "AUTO_CLOSE"}:
            if stage == "PENDING":
                from .views import ReopenView

                heading = (
                    f"(„• ֊ •„) **第 {cycle_number} 次提問已自動結束。**"
                    if transition == "AUTO_CLOSE"
                    else f"✅ **第 {cycle_number} 次提問已結束。**"
                )
                notice = await channel.send(
                    f"{heading}\n\n還想繼續詢問嗎？",
                    view=ReopenView(self),
                )
                if not self.repo.mark_discord_lifecycle_stage(
                    claim.job_id,
                    claim.claim_token,
                    "NOTICE_SENT",
                    control_message_id=notice.id,
                ):
                    raise RuntimeError("LIFECYCLE_CLAIM_LOST")
            if is_thread:
                await channel.edit(
                    name=desired_title,
                    archived=True,
                    locked=False,
                    reason="Course case closed",
                )
            else:
                await channel.edit(name=desired_title, reason="Private case closed")
        elif transition == "IDLE":
            if stage == "PENDING":
                notice = await channel.send(
                    "⏳ **這個案件正在等待您的回覆。**\n\n"
                    "如果仍需要協助，請在 48 小時內繼續回覆；否則系統會自動結案。"
                )
                if not self.repo.mark_discord_lifecycle_stage(
                    claim.job_id,
                    claim.claim_token,
                    "NOTICE_SENT",
                    control_message_id=notice.id,
                ):
                    raise RuntimeError("LIFECYCLE_CLAIM_LOST")
        elif transition == "REOPEN":
            if stage == "PENDING":
                if is_thread:
                    await channel.edit(
                        archived=False,
                        locked=False,
                        name=desired_title,
                        reason="Course case reopened",
                    )
                else:
                    await channel.edit(name=desired_title, reason="Private case reopened")
                if not self.repo.mark_discord_lifecycle_stage(
                    claim.job_id, claim.claim_token, "DISCORD_APPLIED"
                ):
                    raise RuntimeError("LIFECYCLE_CLAIM_LOST")
            self.repo.enqueue_case_reopen_dm(case_id=str(job["case_id"]), cycle_number=cycle_number)
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
            "PRIVATE_DUMP_FAILED",
            "PRIVATE_DUMP_STATE_INVALID",
            "PRIVATE_DELETE_NOT_VERIFIED",
            "PRIVATE_SUPPORT_RECORD_MISSING",
            "PRIVATE_DUMP_QUEUE_FAILED",
        }:
            return (code, False)
        if code == "LIFECYCLE_CLAIM_LOST":
            return (code, True)
    return ("UNEXPECTED_ERROR", True)
