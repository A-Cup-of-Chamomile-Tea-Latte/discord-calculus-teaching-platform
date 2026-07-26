"""Issue opaque public case numbers without deriving tokens from student data."""

from __future__ import annotations

import re
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

TOKEN_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
TOKEN_LENGTH = 6
COURSE_TIMEZONE = ZoneInfo("Asia/Taipei")
CASE_NUMBER_PATTERN = re.compile(
    r"^C(?P<class_code>[0-9]{2})-"
    r"(?P<token>[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6})-"
    r"(?P<month>[0-9]{2})(?P<day>[0-9]{2})-"
    r"(?P<hour>[0-9]{2})(?P<minute>[0-9]{2})"
    r"(?P<private>-P)?$"
)


@dataclass(frozen=True, slots=True)
class CaseNumberParts:
    """Parsed public fields; none of them contains an internal or actor identifier."""

    class_code: str
    token: str
    month: int
    day: int
    hour: int
    minute: int
    private: bool = False


@dataclass(frozen=True, slots=True)
class CaseIdMapping:
    """Private storage mapping between a public label and an opaque internal UUID."""

    internal_case_id: uuid.UUID
    case_number: str
    created_at: datetime


class CaseIdMappingRepository(Protocol):
    def contains_case_number(self, case_number: str) -> bool: ...

    def contains_internal_case_id(self, internal_case_id: uuid.UUID) -> bool: ...

    def save(self, mapping: CaseIdMapping) -> None: ...

    def find_by_case_number(self, case_number: str) -> CaseIdMapping | None: ...

    def find_by_internal_case_id(self, internal_case_id: uuid.UUID) -> CaseIdMapping | None: ...


class CaseIdCollisionError(RuntimeError):
    """Raised when bounded retries cannot find a unique public token or UUID."""


class InMemoryCaseIdMappingRepository:
    """Fixture-only mapping store with uniqueness checks on both identifiers."""

    def __init__(self) -> None:
        self._by_case_number: dict[str, CaseIdMapping] = {}
        self._by_internal_case_id: dict[uuid.UUID, CaseIdMapping] = {}

    def contains_case_number(self, case_number: str) -> bool:
        return case_number in self._by_case_number

    def contains_internal_case_id(self, internal_case_id: uuid.UUID) -> bool:
        return internal_case_id in self._by_internal_case_id

    def save(self, mapping: CaseIdMapping) -> None:
        if self.contains_case_number(mapping.case_number):
            raise ValueError("case number already mapped")
        if self.contains_internal_case_id(mapping.internal_case_id):
            raise ValueError("internal case UUID already mapped")
        self._by_case_number[mapping.case_number] = mapping
        self._by_internal_case_id[mapping.internal_case_id] = mapping

    def find_by_case_number(self, case_number: str) -> CaseIdMapping | None:
        return self._by_case_number.get(case_number)

    def find_by_internal_case_id(self, internal_case_id: uuid.UUID) -> CaseIdMapping | None:
        return self._by_internal_case_id.get(internal_case_id)


def generate_random_token() -> str:
    """Return a cryptographically strong token from a non-ambiguous alphabet."""

    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH))


def _validate_parts(parts: CaseNumberParts) -> None:
    if not re.fullmatch(r"[0-9]{2}", parts.class_code):
        raise ValueError("class_code must be exactly two digits; use 99 for special identities")
    if not re.fullmatch(rf"[{TOKEN_ALPHABET}]{{{TOKEN_LENGTH}}}", parts.token):
        raise ValueError("token must contain six uppercase non-ambiguous characters")
    try:
        # Leap year 2000 validates every possible month/day fragment, including 0229.
        datetime(2000, parts.month, parts.day, parts.hour, parts.minute)
    except ValueError as error:
        raise ValueError("case number contains an invalid month/day/time fragment") from error


def format_case_number(parts: CaseNumberParts) -> str:
    """Format validated components into the canonical public representation."""

    _validate_parts(parts)
    suffix = "-P" if parts.private else ""
    return (
        f"C{parts.class_code}-{parts.token}-"
        f"{parts.month:02d}{parts.day:02d}-{parts.hour:02d}{parts.minute:02d}{suffix}"
    )


def parse_case_number(value: str) -> CaseNumberParts:
    """Strictly parse a canonical case number and validate calendar/time fields."""

    match = CASE_NUMBER_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("invalid case number format")
    parts = CaseNumberParts(
        class_code=match.group("class_code"),
        token=match.group("token"),
        month=int(match.group("month")),
        day=int(match.group("day")),
        hour=int(match.group("hour")),
        minute=int(match.group("minute")),
        private=match.group("private") is not None,
    )
    _validate_parts(parts)
    return parts


def validate_case_number(value: str) -> bool:
    """Return whether *value* is a canonical and calendar-valid case number."""

    try:
        parse_case_number(value)
    except (TypeError, ValueError):
        return False
    return True


def mask_case_number(value: str) -> str:
    """Mask four token characters while retaining class, time, and Private suffix."""

    parts = parse_case_number(value)
    suffix = "-P" if parts.private else ""
    return (
        f"C{parts.class_code}-{parts.token[:2]}****-"
        f"{parts.month:02d}{parts.day:02d}-{parts.hour:02d}{parts.minute:02d}{suffix}"
    )


class CaseIdIssuer:
    """Issue unique public IDs and atomically save their internal UUID mapping.

    The public-token generator receives no actor, email, student-number, name, or
    Discord fields. Production callers must supply a repository whose ``save``
    operation enforces the same uniqueness constraints transactionally.
    """

    def __init__(
        self,
        repository: CaseIdMappingRepository,
        *,
        token_factory: Callable[[], str] = generate_random_token,
        uuid_factory: Callable[[], uuid.UUID] = uuid.uuid4,
        course_timezone: ZoneInfo = COURSE_TIMEZONE,
        max_attempts: int = 8,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self._repository = repository
        self._token_factory = token_factory
        self._uuid_factory = uuid_factory
        self._course_timezone = course_timezone
        self._max_attempts = max_attempts

    def issue(
        self, *, class_code: str, created_at: datetime, private: bool = False
    ) -> CaseIdMapping:
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        local_time = created_at.astimezone(self._course_timezone)

        for _ in range(self._max_attempts):
            case_number = format_case_number(
                CaseNumberParts(
                    class_code=class_code,
                    token=self._token_factory(),
                    month=local_time.month,
                    day=local_time.day,
                    hour=local_time.hour,
                    minute=local_time.minute,
                    private=private,
                )
            )
            if self._repository.contains_case_number(case_number):
                continue

            internal_case_id = self._uuid_factory()
            if self._repository.contains_internal_case_id(internal_case_id):
                continue
            mapping = CaseIdMapping(internal_case_id, case_number, created_at)
            try:
                self._repository.save(mapping)
            except ValueError:
                # A production repository may observe a concurrent insert after
                # the optimistic checks. Retry with new randomness in that case.
                continue
            return mapping

        raise CaseIdCollisionError(
            f"could not issue a unique case ID after {self._max_attempts} attempts"
        )
