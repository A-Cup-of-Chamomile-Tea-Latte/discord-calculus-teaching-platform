"""Private Support policy model and restricted-provider fixture service."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from bots.common.errors import AuthorizationError, ConflictError, ResourceNotFoundError
from bots.common.idempotency import IdempotencyStore, OperationState
from bots.course_assistant.models import ActorContext, CaseStatus
from bots.course_assistant.permissions import StaffPermissionPolicy

RECORD_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
OPERATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class PrivateSupportSource(StrEnum):
    PORTAL = "PORTAL"
    BOT = "BOT"


class RestrictedRepresentationKind(StrEnum):
    BACKEND_ONLY = "BACKEND_ONLY"
    PRIVATE_THREAD = "PRIVATE_THREAD"
    RESTRICTED_CHANNEL = "RESTRICTED_CHANNEL"


class PrivateParticipantRole(StrEnum):
    OWNER = "OWNER"
    TEACHING_TEAM = "TEACHING_TEAM"


class PrivateSupportEventType(StrEnum):
    CREATED = "CREATED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class EscalationReason(StrEnum):
    ACADEMIC = "ACADEMIC"
    ACCESS = "ACCESS"
    WELLBEING = "WELLBEING"
    OTHER = "OTHER"


@dataclass(frozen=True)
class PrivateSupportParticipant:
    user_id: str
    role: PrivateParticipantRole


@dataclass(frozen=True)
class RestrictedRepresentation:
    kind: RestrictedRepresentationKind
    reference_id: str


@dataclass(frozen=True)
class PrivateSupportCaseRecord:
    case_id: str
    owner_user_id: str
    source: PrivateSupportSource
    status: CaseStatus
    participants: tuple[PrivateSupportParticipant, ...]
    assigned_staff_user_id: str | None
    representation: RestrictedRepresentation
    analysis_permission: str
    visibility: str
    retention_review_at: str
    created_at: str
    updated_at: str
    closed_at: str | None


@dataclass(frozen=True)
class CreatePrivateSupportCommand:
    operation_id: str
    case_id: str
    source: PrivateSupportSource
    title: str
    body: str


@dataclass(frozen=True)
class EscalatePrivateSupportCommand:
    operation_id: str
    case_id: str
    assigned_staff_user_id: str
    reason: EscalationReason


@dataclass(frozen=True)
class ClosePrivateSupportCommand:
    operation_id: str
    case_id: str


@dataclass(frozen=True)
class PrivateSupportResult:
    case_id: str
    status: CaseStatus
    representation_kind: RestrictedRepresentationKind
    duplicate: bool


@dataclass(frozen=True)
class PrivateSupportAuditRecord:
    operation_id: str
    case_id: str
    actor_user_id: str
    event_type: PrivateSupportEventType
    status: CaseStatus
    reason: EscalationReason | None
    occurred_at: str


@dataclass(frozen=True)
class PrivateProviderCall:
    operation: str
    operation_id: str
    case_id: str
    participant_user_ids: tuple[str, ...]
    title: str | None = None
    body: str | None = None


class PrivateSupportRepository(Protocol):
    def get(self, case_id: str) -> PrivateSupportCaseRecord | None: ...

    def insert(self, record: PrivateSupportCaseRecord) -> None: ...

    def replace(self, record: PrivateSupportCaseRecord) -> None: ...


class RestrictedPrivateSupportProvider(Protocol):
    @property
    def kind(self) -> RestrictedRepresentationKind: ...

    def create(
        self,
        *,
        operation_id: str,
        case_id: str,
        title: str,
        body: str,
        participant_user_ids: tuple[str, ...],
    ) -> RestrictedRepresentation: ...

    def grant_participant(
        self,
        *,
        operation_id: str,
        case_id: str,
        participant_user_id: str,
    ) -> None: ...

    def close(self, *, operation_id: str, case_id: str) -> None: ...


class PrivateSupportAuditSink(Protocol):
    def get(self, operation_id: str) -> PrivateSupportAuditRecord | None: ...

    def append(self, record: PrivateSupportAuditRecord) -> None: ...


class RetentionHook(Protocol):
    def scheduled(self, record: PrivateSupportCaseRecord) -> None: ...


class ClosureHook(Protocol):
    def closed(self, record: PrivateSupportCaseRecord) -> None: ...


class InMemoryPrivateSupportRepository:
    def __init__(self) -> None:
        self._records: dict[str, PrivateSupportCaseRecord] = {}

    @property
    def records(self) -> tuple[PrivateSupportCaseRecord, ...]:
        return tuple(self._records.values())

    def get(self, case_id: str) -> PrivateSupportCaseRecord | None:
        return self._records.get(case_id)

    def insert(self, record: PrivateSupportCaseRecord) -> None:
        if record.case_id in self._records:
            raise ConflictError("Private Support case already exists.")
        self._records[record.case_id] = record

    def replace(self, record: PrivateSupportCaseRecord) -> None:
        if record.case_id not in self._records:
            raise ResourceNotFoundError("Private Support case was not found.")
        self._records[record.case_id] = record


class InMemoryRestrictedPrivateSupportProvider:
    """Local representation double; even Discord-shaped modes create no channel."""

    def __init__(
        self,
        kind: RestrictedRepresentationKind = RestrictedRepresentationKind.BACKEND_ONLY,
    ) -> None:
        self._kind = kind
        self.calls: list[PrivateProviderCall] = []
        self._counter = 0

    @property
    def kind(self) -> RestrictedRepresentationKind:
        return self._kind

    def create(
        self,
        *,
        operation_id: str,
        case_id: str,
        title: str,
        body: str,
        participant_user_ids: tuple[str, ...],
    ) -> RestrictedRepresentation:
        self._counter += 1
        self.calls.append(
            PrivateProviderCall(
                "create",
                operation_id,
                case_id,
                participant_user_ids,
                title,
                body,
            )
        )
        return RestrictedRepresentation(
            self.kind,
            f"private_fixture_{self._counter:06d}",
        )

    def grant_participant(
        self,
        *,
        operation_id: str,
        case_id: str,
        participant_user_id: str,
    ) -> None:
        self.calls.append(
            PrivateProviderCall(
                "grant_participant",
                operation_id,
                case_id,
                (participant_user_id,),
            )
        )

    def close(self, *, operation_id: str, case_id: str) -> None:
        self.calls.append(PrivateProviderCall("close", operation_id, case_id, ()))


class InMemoryPrivateSupportAuditSink:
    def __init__(self) -> None:
        self._records: dict[str, PrivateSupportAuditRecord] = {}

    @property
    def records(self) -> tuple[PrivateSupportAuditRecord, ...]:
        return tuple(self._records.values())

    def get(self, operation_id: str) -> PrivateSupportAuditRecord | None:
        return self._records.get(operation_id)

    def append(self, record: PrivateSupportAuditRecord) -> None:
        existing = self._records.get(record.operation_id)
        if existing is not None and existing != record:
            raise ConflictError("Private Support operation has another audit record.")
        self._records[record.operation_id] = record


class InMemoryPrivateSupportLifecycleHooks:
    def __init__(self) -> None:
        self.retention_scheduled: list[PrivateSupportCaseRecord] = []
        self.closure_completed: list[PrivateSupportCaseRecord] = []

    def scheduled(self, record: PrivateSupportCaseRecord) -> None:
        self.retention_scheduled.append(record)

    def closed(self, record: PrivateSupportCaseRecord) -> None:
        self.closure_completed.append(record)


class PrivateSupportDataPolicy:
    """Central deny rules used by lookup/export/anonymization adapters."""

    @staticmethod
    def public_case_number(record: PrivateSupportCaseRecord) -> None:
        return None

    @staticmethod
    def include_in_analysis(record: PrivateSupportCaseRecord) -> bool:
        return False

    @staticmethod
    def allow_content_export(record: PrivateSupportCaseRecord) -> bool:
        return False


class PrivateSupportService:
    def __init__(
        self,
        *,
        repository: PrivateSupportRepository,
        provider: RestrictedPrivateSupportProvider,
        audit: PrivateSupportAuditSink,
        idempotency: IdempotencyStore,
        staff_policy: StaffPermissionPolicy,
        teaching_team_user_ids: frozenset[str],
        retention_days: int,
        retention_hook: RetentionHook,
        closure_hook: ClosureHook,
        now: Callable[[], str],
    ) -> None:
        if not teaching_team_user_ids:
            raise ValueError("Private Support requires an explicit teaching-team allowlist")
        if any(not RECORD_ID_PATTERN.fullmatch(item) for item in teaching_team_user_ids):
            raise ValueError("Teaching-team allowlist contains an invalid internal user ID")
        if not 1 <= retention_days <= 3650:
            raise ValueError("retention_days must be between 1 and 3650")
        self._repository = repository
        self._provider = provider
        self._audit = audit
        self._idempotency = idempotency
        self._staff_policy = staff_policy
        self._teaching_team = teaching_team_user_ids
        self._retention_days = retention_days
        self._retention_hook = retention_hook
        self._closure_hook = closure_hook
        self._now = now

    def get_for_participant(self, actor: ActorContext, case_id: str) -> PrivateSupportCaseRecord:
        record = self._require_case(case_id)
        if actor.user_id not in {item.user_id for item in record.participants}:
            raise AuthorizationError("Private Support access requires an explicit participant.")
        return record

    async def create(
        self, actor: ActorContext, command: CreatePrivateSupportCommand
    ) -> PrivateSupportResult:
        self._validate_actor(actor)
        self._validate_operation(command.operation_id)
        self._validate_record_id(command.case_id, "case_id")
        title = command.title.strip()
        body = command.body.strip()
        if not 1 <= len(title) <= 160:
            raise ValueError("Private Support title must contain 1–160 characters")
        if not 1 <= len(body) <= 1800:
            raise ValueError("Private Support body must contain 1–1800 characters")
        namespace = "course_assistant:private_support:create"
        decision = self._idempotency.begin(namespace, command.operation_id)
        if not decision.acquired:
            return self._replay(command.operation_id, command.case_id, namespace)
        if self._repository.get(command.case_id) is not None:
            self._idempotency.fail(namespace, command.operation_id)
            raise ConflictError("Private Support case already exists.")

        participant_ids = tuple(dict.fromkeys((actor.user_id, *sorted(self._teaching_team))))
        participants = (
            PrivateSupportParticipant(actor.user_id, PrivateParticipantRole.OWNER),
            *(
                PrivateSupportParticipant(item, PrivateParticipantRole.TEACHING_TEAM)
                for item in sorted(self._teaching_team)
                if item != actor.user_id
            ),
        )
        created_at = self._now()
        try:
            representation = self._provider.create(
                operation_id=command.operation_id,
                case_id=command.case_id,
                title=title,
                body=body,
                participant_user_ids=participant_ids,
            )
            if representation.kind is not self._provider.kind:
                raise ConflictError("Private provider returned the wrong representation kind.")
            record = PrivateSupportCaseRecord(
                case_id=command.case_id,
                owner_user_id=actor.user_id,
                source=command.source,
                status=CaseStatus.OPEN,
                participants=participants,
                assigned_staff_user_id=None,
                representation=representation,
                analysis_permission="EXCLUDED",
                visibility="TEACHING_STAFF",
                retention_review_at=self._retention_review_at(created_at),
                created_at=created_at,
                updated_at=created_at,
                closed_at=None,
            )
            self._repository.insert(record)
            self._retention_hook.scheduled(record)
            self._audit.append(
                PrivateSupportAuditRecord(
                    command.operation_id,
                    command.case_id,
                    actor.user_id,
                    PrivateSupportEventType.CREATED,
                    CaseStatus.OPEN,
                    None,
                    created_at,
                )
            )
            self._idempotency.complete(namespace, command.operation_id, command.case_id)
        except Exception:
            self._fail_if_in_progress(namespace, command.operation_id)
            raise
        return PrivateSupportResult(command.case_id, record.status, representation.kind, False)

    async def escalate(
        self, actor: ActorContext, command: EscalatePrivateSupportCommand
    ) -> PrivateSupportResult:
        self._validate_actor(actor)
        self._validate_operation(command.operation_id)
        record = self._require_case(command.case_id)
        self._require_owner_or_staff(actor, record)
        if command.assigned_staff_user_id not in self._teaching_team:
            raise AuthorizationError("Escalation target is not in the teaching-team allowlist.")
        namespace = "course_assistant:private_support:escalate"
        decision = self._idempotency.begin(namespace, command.operation_id)
        if not decision.acquired:
            return self._replay(command.operation_id, command.case_id, namespace)
        if record.status is CaseStatus.CLOSED or record.assigned_staff_user_id is not None:
            self._idempotency.fail(namespace, command.operation_id)
            raise ConflictError("Private Support case cannot be escalated from its current state.")
        updated_at = self._now()
        try:
            self._provider.grant_participant(
                operation_id=command.operation_id,
                case_id=command.case_id,
                participant_user_id=command.assigned_staff_user_id,
            )
            updated = replace(
                record,
                status=CaseStatus.ESCALATED,
                assigned_staff_user_id=command.assigned_staff_user_id,
                updated_at=updated_at,
            )
            self._repository.replace(updated)
            self._audit.append(
                PrivateSupportAuditRecord(
                    command.operation_id,
                    command.case_id,
                    actor.user_id,
                    PrivateSupportEventType.ESCALATED,
                    updated.status,
                    command.reason,
                    updated_at,
                )
            )
            self._idempotency.complete(namespace, command.operation_id, command.case_id)
        except Exception:
            self._fail_if_in_progress(namespace, command.operation_id)
            raise
        return PrivateSupportResult(
            command.case_id, updated.status, updated.representation.kind, False
        )

    async def close(
        self, actor: ActorContext, command: ClosePrivateSupportCommand
    ) -> PrivateSupportResult:
        self._validate_actor(actor)
        self._validate_operation(command.operation_id)
        record = self._require_case(command.case_id)
        self._require_owner_or_staff(actor, record)
        namespace = "course_assistant:private_support:close"
        decision = self._idempotency.begin(namespace, command.operation_id)
        if not decision.acquired:
            return self._replay(command.operation_id, command.case_id, namespace)
        if record.status is CaseStatus.CLOSED:
            self._idempotency.fail(namespace, command.operation_id)
            raise ConflictError("Private Support case is already closed.")
        closed_at = self._now()
        try:
            self._provider.close(operation_id=command.operation_id, case_id=command.case_id)
            updated = replace(
                record,
                status=CaseStatus.CLOSED,
                updated_at=closed_at,
                closed_at=closed_at,
            )
            self._repository.replace(updated)
            self._closure_hook.closed(updated)
            self._audit.append(
                PrivateSupportAuditRecord(
                    command.operation_id,
                    command.case_id,
                    actor.user_id,
                    PrivateSupportEventType.CLOSED,
                    updated.status,
                    None,
                    closed_at,
                )
            )
            self._idempotency.complete(namespace, command.operation_id, command.case_id)
        except Exception:
            self._fail_if_in_progress(namespace, command.operation_id)
            raise
        return PrivateSupportResult(
            command.case_id, updated.status, updated.representation.kind, False
        )

    def _replay(self, operation_id: str, case_id: str, namespace: str) -> PrivateSupportResult:
        decision = self._idempotency.begin(namespace, operation_id)
        audit = self._audit.get(operation_id)
        record = self._repository.get(case_id)
        if (
            decision.record.state is not OperationState.COMPLETED
            or decision.record.result_reference != case_id
            or audit is None
            or audit.case_id != case_id
            or record is None
        ):
            raise ConflictError("Private Support operation is in conflict or incomplete.")
        return PrivateSupportResult(case_id, record.status, record.representation.kind, True)

    def _require_case(self, case_id: str) -> PrivateSupportCaseRecord:
        self._validate_record_id(case_id, "case_id")
        record = self._repository.get(case_id)
        if record is None:
            raise ResourceNotFoundError("Private Support case was not found.")
        return record

    def _require_owner_or_staff(
        self, actor: ActorContext, record: PrivateSupportCaseRecord
    ) -> None:
        if actor.user_id == record.owner_user_id:
            return
        self._staff_policy.require_staff(actor)
        if actor.user_id not in self._teaching_team:
            raise AuthorizationError("Staff actor is outside the Private Support allowlist.")

    def _retention_review_at(self, created_at: str) -> str:
        try:
            value = datetime.fromisoformat(created_at)
        except ValueError as error:
            raise ValueError("Private Support clock must return an ISO timestamp") from error
        if value.tzinfo is None:
            raise ValueError("Private Support clock timestamp must include a timezone")
        return (value + timedelta(days=self._retention_days)).isoformat()

    def _fail_if_in_progress(self, namespace: str, operation_id: str) -> None:
        decision = self._idempotency.begin(namespace, operation_id)
        if decision.record.state is OperationState.IN_PROGRESS:
            self._idempotency.fail(namespace, operation_id)

    @staticmethod
    def _validate_actor(actor: ActorContext) -> None:
        if not RECORD_ID_PATTERN.fullmatch(actor.user_id):
            raise ValueError("actor.user_id is not a valid internal record ID")

    @staticmethod
    def _validate_operation(operation_id: str) -> None:
        if not OPERATION_ID_PATTERN.fullmatch(operation_id):
            raise ValueError("operation_id must be a safe 8–128 character identifier")

    @staticmethod
    def _validate_record_id(value: str, field: str) -> None:
        if not RECORD_ID_PATTERN.fullmatch(value):
            raise ValueError(f"{field} is not a valid internal record ID")
