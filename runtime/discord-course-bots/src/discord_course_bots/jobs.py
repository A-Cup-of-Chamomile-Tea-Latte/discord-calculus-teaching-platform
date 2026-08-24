from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PrivateDumpClaim:
    channel_id: int
    case_number: str
    claim_token: str
    claimed_by: str
    attempt_count: int
    lease_expires_at: str


@dataclass(frozen=True, slots=True)
class PrivateDumpFailureResult:
    channel_id: int
    status: str
    attempt_count: int
    failure_kind: str
    retry_at: str | None


@dataclass(frozen=True, slots=True)
class DiscordLifecycleClaim:
    job_id: str
    claim_token: str
    claimed_by: str
    attempt_count: int
    lease_expires_at: str


@dataclass(frozen=True, slots=True)
class PrivateOpenClaim:
    interaction_id: str
    claim_token: str
    claimed_by: str
    attempt_count: int
    lease_expires_at: str


@dataclass(frozen=True, slots=True)
class CourseRoleClaim:
    job_id: str
    claim_token: str
    claimed_by: str
    attempt_count: int
    lease_expires_at: str
