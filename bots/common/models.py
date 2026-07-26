"""Framework-neutral values shared by bot services and fixture clients."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HealthStatus(StrEnum):
    STARTING = "STARTING"
    READY = "READY"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CaseThreadMapping:
    case_id: str
    guild_id: str
    parent_channel_id: str
    thread_id: str
    updated_at: str


@dataclass(frozen=True)
class DiscordAttachmentSnapshot:
    attachment_id: str
    filename: str
    content_type: str | None
    size_bytes: int
    url: str


@dataclass(frozen=True)
class DiscordMessageSnapshot:
    message_id: str
    thread_id: str
    author_id: str
    author_role_ids: tuple[str, ...]
    content: str
    created_at: str
    edited_at: str | None
    parent_message_id: str | None
    attachments: tuple[DiscordAttachmentSnapshot, ...]


@dataclass(frozen=True)
class ThreadSnapshot:
    thread_id: str
    messages: tuple[DiscordMessageSnapshot, ...]
    next_cursor: str | None
    fetched_at: str


@dataclass(frozen=True)
class CreatedThread:
    thread_id: str
    first_message_id: str


@dataclass(frozen=True)
class HealthInfo:
    component: str
    status: HealthStatus
    runtime_mode: str
    ready: bool
    network_enabled: bool
    guild_configured: bool
    allowed_channel_count: int
    checked_at: str
