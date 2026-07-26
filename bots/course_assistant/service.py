"""Fixture-first Course Assistant application service."""

from __future__ import annotations

import re
from collections.abc import Callable

from bots.common.config import SNOWFLAKE_PATTERN, CourseAssistantConfig
from bots.common.errors import (
    AuthorizationError,
    ConflictError,
    NotConfiguredError,
    ResourceNotFoundError,
)
from bots.common.health import build_health
from bots.common.idempotency import IdempotencyStore, OperationState
from bots.common.models import CaseThreadMapping, HealthInfo, HealthStatus
from bots.common.ports import CaseThreadMappingRepository, DiscordCourseWriter
from bots.course_assistant.hooks import InteractionHookRegistry
from bots.course_assistant.models import (
    ActorContext,
    AnonymousReplyAuditRecord,
    AnonymousReplyCasePolicy,
    AnonymousReplyCommand,
    AnonymousReplyDisplayMode,
    AppliedMembership,
    ApplyMembershipCommand,
    CaseState,
    CaseStatus,
    CreateCasePostCommand,
    CreatedCasePost,
    HookResult,
    PrivateSupportRequest,
    PublishedAnonymousReply,
    UpdateCaseStatusCommand,
    UpdatedCaseStatus,
)
from bots.course_assistant.permissions import MembershipRolePolicy, StaffPermissionPolicy
from bots.course_assistant.repositories import (
    AnonymousReplyAuditSink,
    AnonymousReplyCaseRepository,
    CourseCaseRepository,
    JoiningOrderRepository,
    generate_course_alias,
)

RECORD_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
STATUS_TAG_PATTERN = re.compile(r"^[a-z0-9_-]{1,64}$")


class CourseAssistantService:
    def __init__(
        self,
        *,
        config: CourseAssistantConfig,
        writer: DiscordCourseWriter,
        mappings: CaseThreadMappingRepository,
        cases: CourseCaseRepository,
        joining_orders: JoiningOrderRepository,
        idempotency: IdempotencyStore,
        staff_policy: StaffPermissionPolicy,
        role_policy: MembershipRolePolicy,
        hooks: InteractionHookRegistry,
        case_parent_channel_id: str,
        now: Callable[[], str],
        anonymous_reply_cases: AnonymousReplyCaseRepository | None = None,
        anonymous_reply_audit: AnonymousReplyAuditSink | None = None,
    ) -> None:
        if config.guild_id is None:
            raise ValueError("Course Assistant service requires an explicit fixture/live guild ID")
        if case_parent_channel_id not in config.channel_ids:
            raise ValueError("case_parent_channel_id must be in the bot channel allowlist")
        required_roles = {
            role_policy.broad_membership_role_id,
            *role_policy.class_role_ids.values(),
        }
        if not required_roles.issubset(config.role_ids):
            raise ValueError("Membership role policy must use only configured role allowlist IDs")
        self._config = config
        self._writer = writer
        self._mappings = mappings
        self._cases = cases
        self._joining_orders = joining_orders
        self._idempotency = idempotency
        self._staff_policy = staff_policy
        self._role_policy = role_policy
        self._hooks = hooks
        self._case_parent_channel_id = case_parent_channel_id
        self._guild_id = config.guild_id
        self._now = now
        self._anonymous_reply_cases = anonymous_reply_cases
        self._anonymous_reply_audit = anonymous_reply_audit

    def health(self, status: HealthStatus, checked_at: str) -> HealthInfo:
        return build_health(self._config, status=status, checked_at=checked_at)

    async def create_case_post(
        self, actor: ActorContext, command: CreateCasePostCommand
    ) -> CreatedCasePost:
        self._validate_actor(actor)
        self._validate_record_id(command.case_id, "case_id")
        self._validate_operation(command.operation_id)
        title = command.title.strip()
        body = command.body.strip()
        if not 1 <= len(title) <= 100:
            raise ValueError("title must contain 1–100 characters")
        if not 1 <= len(body) <= 2000:
            raise ValueError("body must contain 1–2000 characters")

        decision = self._idempotency.begin("course_assistant:create_case", command.operation_id)
        if not decision.acquired:
            if decision.record.state is OperationState.COMPLETED:
                mapping = self._mappings.get_by_case_id(command.case_id)
                if mapping is None:
                    raise ConflictError("Completed operation is missing its case-thread mapping.")
                reference = decision.record.result_reference or ""
                thread_id, separator, message_id = reference.partition("|")
                if not separator or thread_id != mapping.thread_id or not message_id:
                    raise ConflictError("Completed operation has an invalid result reference.")
                return CreatedCasePost(command.case_id, thread_id, message_id, duplicate=True)
            raise ConflictError("The create-case operation is already in progress or failed.")
        if self._mappings.get_by_case_id(command.case_id) or self._cases.get(command.case_id):
            self._idempotency.fail("course_assistant:create_case", command.operation_id)
            raise ConflictError("The case already has a Discord mapping or state record.")

        try:
            created = await self._writer.create_case_thread(
                operation_id=command.operation_id,
                parent_channel_id=self._case_parent_channel_id,
                title=title,
                body=body,
            )
            self._mappings.upsert(
                CaseThreadMapping(
                    case_id=command.case_id,
                    guild_id=self._guild_id,
                    parent_channel_id=self._case_parent_channel_id,
                    thread_id=created.thread_id,
                    updated_at=self._now(),
                )
            )
            self._cases.insert(CaseState(command.case_id, CaseStatus.OPEN))
            self._idempotency.complete(
                "course_assistant:create_case",
                command.operation_id,
                f"{created.thread_id}|{created.first_message_id}",
            )
        except Exception:
            self._fail_if_in_progress("course_assistant:create_case", command.operation_id)
            raise
        return CreatedCasePost(
            command.case_id,
            created.thread_id,
            created.first_message_id,
            duplicate=False,
        )

    async def apply_membership(
        self, actor: ActorContext, command: ApplyMembershipCommand
    ) -> AppliedMembership:
        self._staff_policy.require_staff(actor)
        self._validate_actor(actor)
        self._validate_record_id(command.target_user_id, "target_user_id")
        if not SNOWFLAKE_PATTERN.fullmatch(command.target_discord_user_id):
            raise ValueError("target_discord_user_id must be a Discord ID string")
        self._validate_operation(command.operation_id)
        role_ids = self._role_policy.roles_for_class(command.class_code)
        decision = self._idempotency.begin("course_assistant:membership", command.operation_id)
        if not decision.acquired:
            if decision.record.state is not OperationState.COMPLETED:
                raise ConflictError("The membership operation is already in progress or failed.")
            order = self._joining_orders.allocate_next(
                command.course_id, command.class_code, command.target_user_id
            )
            return AppliedMembership(
                command.target_user_id,
                generate_course_alias(command.class_code, order),
                role_ids,
                duplicate=True,
            )

        try:
            order = self._joining_orders.allocate_next(
                command.course_id, command.class_code, command.target_user_id
            )
            alias = generate_course_alias(command.class_code, order)
            await self._writer.set_member_nickname(
                operation_id=command.operation_id,
                member_id=command.target_discord_user_id,
                nickname=alias,
            )
            for role_id in role_ids:
                await self._writer.add_member_role(
                    operation_id=command.operation_id,
                    member_id=command.target_discord_user_id,
                    role_id=role_id,
                )
            self._idempotency.complete("course_assistant:membership", command.operation_id, alias)
        except Exception:
            self._fail_if_in_progress("course_assistant:membership", command.operation_id)
            raise
        return AppliedMembership(command.target_user_id, alias, role_ids, duplicate=False)

    async def update_case_status(
        self, actor: ActorContext, command: UpdateCaseStatusCommand
    ) -> UpdatedCaseStatus:
        self._staff_policy.require_staff(actor)
        self._validate_actor(actor)
        self._validate_operation(command.operation_id)
        if command.tag is not None and not STATUS_TAG_PATTERN.fullmatch(command.tag):
            raise ValueError("tag must be a safe 1–64 character identifier")
        mapping = self._mappings.get_by_case_id(command.case_id)
        if mapping is None:
            raise ConflictError("The case has no Discord thread mapping.")
        decision = self._idempotency.begin("course_assistant:case_status", command.operation_id)
        if not decision.acquired:
            reference = decision.record.result_reference
            if decision.record.state is OperationState.COMPLETED and reference:
                try:
                    original_status = CaseStatus(reference)
                except ValueError as error:
                    raise ConflictError(
                        "Completed status operation has an invalid result reference."
                    ) from error
                return UpdatedCaseStatus(command.case_id, original_status, duplicate=True)
            raise ConflictError("The status operation is already in progress or failed.")
        try:
            updated = self._cases.compare_and_set_status(
                command.case_id, command.expected_status, command.new_status
            )
            await self._writer.update_thread_status(
                operation_id=command.operation_id,
                thread_id=mapping.thread_id,
                status=updated.status.value,
                tag=command.tag,
            )
            self._idempotency.complete(
                "course_assistant:case_status", command.operation_id, updated.status.value
            )
        except Exception:
            self._fail_if_in_progress("course_assistant:case_status", command.operation_id)
            raise
        return UpdatedCaseStatus(command.case_id, updated.status, duplicate=False)

    async def create_private_support(
        self, actor: ActorContext, operation_id: str, body: str
    ) -> HookResult:
        self._validate_actor(actor)
        self._validate_operation(operation_id)
        normalized = body.strip()
        if not 1 <= len(normalized) <= 2000:
            raise ValueError("Private Support body must contain 1–2000 characters")
        return await self._hooks.create_private_support(
            PrivateSupportRequest(operation_id, actor.user_id, normalized)
        )

    def authorize_anonymous_reply(
        self, actor: ActorContext, case_id: str
    ) -> AnonymousReplyCasePolicy:
        """Authorize before a button/command opens a private modal."""
        self._validate_actor(actor)
        self._validate_record_id(case_id, "case_id")
        if self._anonymous_reply_cases is None or self._anonymous_reply_audit is None:
            raise NotConfiguredError("Anonymous reply repositories are not configured.")
        policy = self._anonymous_reply_cases.get(case_id)
        if policy is None or not policy.replies_enabled:
            raise ResourceNotFoundError("The reply-enabled case was not found.")
        if policy.owner_user_id != actor.user_id:
            raise AuthorizationError("Only the case owner may use its anonymous reply modal.")
        if policy.display_mode is AnonymousReplyDisplayMode.COURSE_ALIAS:
            if policy.course_alias is None or not re.fullmatch(r"[0-9]{5}", policy.course_alias):
                raise ConflictError("The case has an invalid course-alias display policy.")
        elif policy.course_alias is not None:
            raise ConflictError("A fully anonymous case must not expose a course alias.")
        if self._mappings.get_by_case_id(case_id) is None:
            raise ResourceNotFoundError("The reply-enabled case has no Discord thread mapping.")
        return policy

    async def post_anonymous_reply(
        self, actor: ActorContext, command: AnonymousReplyCommand
    ) -> PublishedAnonymousReply:
        policy = self.authorize_anonymous_reply(actor, command.case_id)
        self._validate_operation(command.operation_id)
        body = command.body.strip()
        if not 1 <= len(body) <= 1800:
            raise ValueError("Anonymous reply body must contain 1–1800 characters")
        if command.parent_discord_message_id is not None and not SNOWFLAKE_PATTERN.fullmatch(
            command.parent_discord_message_id
        ):
            raise ValueError("parent_discord_message_id must be a Discord ID string")
        if self._anonymous_reply_audit is None:
            raise NotConfiguredError("Anonymous reply audit sink is not configured.")
        mapping = self._mappings.get_by_case_id(command.case_id)
        if mapping is None:
            raise ResourceNotFoundError("The reply-enabled case has no Discord thread mapping.")

        namespace = "course_assistant:anonymous_reply"
        decision = self._idempotency.begin(namespace, command.operation_id)
        if not decision.acquired:
            audit = self._anonymous_reply_audit.get_by_operation_id(command.operation_id)
            if (
                decision.record.state is not OperationState.COMPLETED
                or audit is None
                or decision.record.result_reference != audit.public_message_id
                or audit.case_id != command.case_id
                or audit.actor_user_id != actor.user_id
            ):
                raise ConflictError("The anonymous reply operation is in conflict or incomplete.")
            return PublishedAnonymousReply(
                command.case_id,
                audit.public_message_id,
                audit.display_mode,
                self._anonymous_confirmation(audit.display_mode),
                duplicate=True,
            )

        public_label = (
            policy.course_alias
            if policy.display_mode is AnonymousReplyDisplayMode.COURSE_ALIAS
            else "匿名同學"
        )
        public_body = f"**{public_label}**\n{body}"
        try:
            message_id = await self._writer.send_message(
                operation_id=command.operation_id,
                thread_id=mapping.thread_id,
                body=public_body,
                parent_message_id=command.parent_discord_message_id,
                suppress_mentions=True,
            )
            self._anonymous_reply_audit.append(
                AnonymousReplyAuditRecord(
                    operation_id=command.operation_id,
                    case_id=command.case_id,
                    actor_user_id=actor.user_id,
                    public_message_id=message_id,
                    display_mode=policy.display_mode,
                    occurred_at=self._now(),
                )
            )
            self._idempotency.complete(namespace, command.operation_id, message_id)
        except Exception:
            self._fail_if_in_progress(namespace, command.operation_id)
            raise
        return PublishedAnonymousReply(
            command.case_id,
            message_id,
            policy.display_mode,
            self._anonymous_confirmation(policy.display_mode),
            duplicate=False,
        )

    @staticmethod
    def _anonymous_confirmation(display_mode: AnonymousReplyDisplayMode) -> str:
        if display_mode is AnonymousReplyDisplayMode.COURSE_ALIAS:
            return "已以課程代號代為發布；只有你看得到此確認。"
        return "已以完全匿名方式代為發布；只有你看得到此確認。"

    def _fail_if_in_progress(self, namespace: str, operation_id: str) -> None:
        decision = self._idempotency.begin(namespace, operation_id)
        if decision.record.state is OperationState.IN_PROGRESS:
            self._idempotency.fail(namespace, operation_id)

    @staticmethod
    def _validate_record_id(value: str, field: str) -> None:
        if not RECORD_ID_PATTERN.fullmatch(value):
            raise ValueError(f"{field} is not a valid internal record ID")

    @classmethod
    def _validate_actor(cls, actor: ActorContext) -> None:
        cls._validate_record_id(actor.user_id, "actor.user_id")

    @staticmethod
    def _validate_operation(operation_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", operation_id):
            raise ValueError("operation_id must be a safe 8–128 character identifier")
