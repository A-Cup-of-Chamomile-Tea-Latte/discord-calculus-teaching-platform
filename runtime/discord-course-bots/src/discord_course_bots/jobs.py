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


@dataclass(frozen=True, slots=True)
class DmClaim:
    message_key: str
    claim_token: str
    claimed_by: str
    attempt_count: int
    lease_expires_at: str


@dataclass(frozen=True, slots=True, repr=False)
class EmailDeliveryClaim:
    delivery_id: str
    challenge_id: str
    destination: str
    verification_code: str
    email_kind: str
    expires_at: str
    claim_token: str
    attempt_count: int
    lease_expires_at: str

    def __repr__(self) -> str:
        return (
            "EmailDeliveryClaim("
            f"delivery_id={self.delivery_id!r}, challenge_id={self.challenge_id!r}, "
            f"email_kind={self.email_kind!r}, expires_at={self.expires_at!r}, "
            f"attempt_count={self.attempt_count!r}, destination=<redacted>, "
            "verification_code=<redacted>)"
        )
