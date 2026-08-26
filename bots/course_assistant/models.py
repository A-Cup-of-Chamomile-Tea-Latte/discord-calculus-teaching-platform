"""Course Assistant commands and fixture-domain results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    TRACKED = "TRACKED"
    IDLE = "IDLE"
    CLOSED = "CLOSED"
    AUTO_CLOSED = "AUTO_CLOSED"


class AnonymousReplyDisplayMode(StrEnum):
    COURSE_ALIAS = "COURSE_ALIAS"
    ANONYMOUS = "ANONYMOUS"


@dataclass(frozen=True)
class ActorContext:
    user_id: str
    role_ids: tuple[str, ...]


@dataclass(frozen=True)
class CreateCasePostCommand:
    operation_id: str
    case_id: str
    title: str
    body: str


@dataclass(frozen=True)
class CreatedCasePost:
    case_id: str
    thread_id: str
    first_message_id: str
    duplicate: bool


@dataclass(frozen=True)
class ApplyMembershipCommand:
    operation_id: str
    target_user_id: str
    target_discord_user_id: str
    course_id: str
    class_code: str


@dataclass(frozen=True)
class AppliedMembership:
    target_user_id: str
    course_alias: str
    role_ids: tuple[str, str]
    duplicate: bool


@dataclass(frozen=True)
class UpdateCaseStatusCommand:
    operation_id: str
    case_id: str
    expected_status: CaseStatus
    new_status: CaseStatus
    tag: str | None


@dataclass(frozen=True)
class UpdatedCaseStatus:
    case_id: str
    status: CaseStatus
    duplicate: bool


@dataclass(frozen=True)
class CaseState:
    case_id: str
    status: CaseStatus


@dataclass(frozen=True)
class PrivateSupportRequest:
    operation_id: str
    requested_by_user_id: str
    body: str


@dataclass(frozen=True)
class HookResult:
    outcome: str
    reference_id: str | None


@dataclass(frozen=True)
class AnonymousReplyCasePolicy:
    case_id: str
    owner_user_id: str
    display_mode: AnonymousReplyDisplayMode
    course_alias: str | None
    replies_enabled: bool = True


@dataclass(frozen=True)
class AnonymousReplyCommand:
    operation_id: str
    case_id: str
    body: str
    parent_discord_message_id: str | None = None


@dataclass(frozen=True)
class AnonymousReplyAuditRecord:
    operation_id: str
    case_id: str
    actor_user_id: str
    public_message_id: str
    display_mode: AnonymousReplyDisplayMode
    occurred_at: str


@dataclass(frozen=True)
class PublishedAnonymousReply:
    case_id: str
    public_message_id: str
    display_mode: AnonymousReplyDisplayMode
    ephemeral_confirmation: str
    duplicate: bool
