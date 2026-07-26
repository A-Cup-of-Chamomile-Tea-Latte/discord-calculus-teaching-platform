"""Typed commands and handoff values for explicit archive reads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from bots.common.models import CaseThreadMapping


class ArchiveCaseType(StrEnum):
    GENERAL = "GENERAL"
    PRIVATE_SUPPORT = "PRIVATE_SUPPORT"


class ExportMode(StrEnum):
    DUMP = "DUMP"
    FOLLOW = "FOLLOW"


class AuthorRole(StrEnum):
    STUDENT = "STUDENT"
    TA = "TA"
    INSTRUCTOR = "INSTRUCTOR"
    BOT = "BOT"


class AuthorDisplayMode(StrEnum):
    REAL_NAME = "REAL_NAME"
    COURSE_ALIAS = "COURSE_ALIAS"
    ANONYMOUS = "ANONYMOUS"


class AnalysisDecision(StrEnum):
    INHERIT = "INHERIT"
    INCLUDED = "INCLUDED"
    EXCLUDED = "EXCLUDED"


@dataclass(frozen=True)
class ArchiveCaseRecord:
    case_id: str
    case_number: str | None
    case_type: ArchiveCaseType
    mapping: CaseThreadMapping | None


@dataclass(frozen=True)
class ManagerContext:
    user_id: str
    role_ids: tuple[str, ...]


@dataclass(frozen=True)
class MessageIdentityPolicy:
    author_user_id: str
    author_role: AuthorRole
    author_display_mode: AuthorDisplayMode
    analysis_permission: AnalysisDecision


@dataclass(frozen=True)
class ArchiveAttachmentMetadata:
    attachment_id: str
    filename: str
    media_type: str
    size_bytes: int

    def to_contract(self) -> dict[str, object]:
        return {
            "attachmentId": self.attachment_id,
            "filename": self.filename,
            "mediaType": self.media_type,
            "sizeBytes": self.size_bytes,
        }


@dataclass(frozen=True)
class ArchiveMessageRecord:
    message_id: str
    case_id: str
    author_user_id: str
    author_role: AuthorRole
    author_display_mode: AuthorDisplayMode
    body: str
    analysis_permission: AnalysisDecision
    parent_message_id: str | None
    discord_message_id: str
    edited_at: str | None
    attachments: tuple[ArchiveAttachmentMetadata, ...]
    created_at: str

    def to_contract(self) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "messageId": self.message_id,
            "caseId": self.case_id,
            "authorUserId": self.author_user_id,
            "authorRole": self.author_role.value,
            "authorDisplayMode": self.author_display_mode.value,
            "body": self.body,
            "source": "DISCORD",
            "analysisPermission": self.analysis_permission.value,
            "parentMessageId": self.parent_message_id,
            "discordMessageId": self.discord_message_id,
            "editedAt": self.edited_at,
            "attachments": [attachment.to_contract() for attachment in self.attachments],
            "createdAt": self.created_at,
        }


@dataclass(frozen=True)
class ExportCommand:
    request_id: str
    case_number: str
    page_size: int = 100


@dataclass(frozen=True)
class FollowCheckpoint:
    case_id: str
    last_exported_message_id: str
    updated_at: str


@dataclass(frozen=True)
class ExportHandoff:
    request_id: str
    mode: ExportMode
    case_id: str
    case_number: str
    thread_id: str
    messages: tuple[ArchiveMessageRecord, ...]
    starting_after_message_id: str | None
    last_exported_message_id: str | None
    page_count: int
    created_at: str
    duplicate: bool = False

    def as_duplicate(self) -> ExportHandoff:
        return ExportHandoff(
            request_id=self.request_id,
            mode=self.mode,
            case_id=self.case_id,
            case_number=self.case_number,
            thread_id=self.thread_id,
            messages=self.messages,
            starting_after_message_id=self.starting_after_message_id,
            last_exported_message_id=self.last_exported_message_id,
            page_count=self.page_count,
            created_at=self.created_at,
            duplicate=True,
        )
