"""Pure alias allocation and fixture repositories."""

from __future__ import annotations

import re
from typing import Protocol

from bots.common.errors import ConflictError, ResourceNotFoundError
from bots.course_assistant.models import (
    AnonymousReplyAuditRecord,
    AnonymousReplyCasePolicy,
    AnonymousReplyDisplayMode,
    CaseState,
    CaseStatus,
)

CLASS_CODE_PATTERN = re.compile(r"^[0-9]{2}$")


def generate_course_alias(class_code: str, joining_order: int) -> str:
    if not CLASS_CODE_PATTERN.fullmatch(class_code):
        raise ValueError("class_code must contain exactly two digits")
    if isinstance(joining_order, bool) or not isinstance(joining_order, int):
        raise ValueError("joining_order must be an integer from 1 to 999")
    if not 1 <= joining_order <= 999:
        raise ValueError("joining_order must be an integer from 1 to 999")
    return f"{class_code}{joining_order:03d}"


class JoiningOrderRepository(Protocol):
    def allocate_next(self, course_id: str, class_code: str, user_id: str) -> int: ...


class CourseCaseRepository(Protocol):
    def get(self, case_id: str) -> CaseState | None: ...

    def insert(self, state: CaseState) -> None: ...

    def compare_and_set_status(
        self, case_id: str, expected: CaseStatus, new: CaseStatus
    ) -> CaseState: ...


class AnonymousReplyCaseRepository(Protocol):
    def get(self, case_id: str) -> AnonymousReplyCasePolicy | None: ...


class AnonymousReplyAuditSink(Protocol):
    def get_by_operation_id(self, operation_id: str) -> AnonymousReplyAuditRecord | None: ...

    def append(self, record: AnonymousReplyAuditRecord) -> None: ...


class InMemoryJoiningOrderRepository:
    def __init__(self) -> None:
        self._allocations: dict[tuple[str, str, str], int] = {}

    def allocate_next(self, course_id: str, class_code: str, user_id: str) -> int:
        generate_course_alias(class_code, 1)
        if not course_id or not user_id:
            raise ValueError("course_id and user_id are required")
        key = (course_id, class_code, user_id)
        existing = self._allocations.get(key)
        if existing is not None:
            return existing
        orders = [
            order
            for (candidate_course, candidate_class, _), order in self._allocations.items()
            if candidate_course == course_id and candidate_class == class_code
        ]
        next_order = max(orders, default=0) + 1
        if next_order > 999:
            raise ConflictError("The class joining-order range is exhausted.")
        self._allocations[key] = next_order
        return next_order


class InMemoryCourseCaseRepository:
    def __init__(self, seed: tuple[CaseState, ...] = ()) -> None:
        self._states = {state.case_id: state for state in seed}

    def get(self, case_id: str) -> CaseState | None:
        return self._states.get(case_id)

    def insert(self, state: CaseState) -> None:
        if state.case_id in self._states:
            raise ConflictError("The case already exists.")
        self._states[state.case_id] = state

    def compare_and_set_status(
        self, case_id: str, expected: CaseStatus, new: CaseStatus
    ) -> CaseState:
        current = self._states.get(case_id)
        if current is None:
            raise ResourceNotFoundError("The case was not found.")
        if current.status is not expected:
            raise ConflictError("The case status changed before this operation.")
        updated = CaseState(case_id, new)
        self._states[case_id] = updated
        return updated


class InMemoryAnonymousReplyCaseRepository:
    def __init__(self, seed: tuple[AnonymousReplyCasePolicy, ...] = ()) -> None:
        self._policies: dict[str, AnonymousReplyCasePolicy] = {}
        for policy in seed:
            if policy.case_id in self._policies:
                raise ConflictError("Anonymous reply case policy already exists.")
            if policy.display_mode is AnonymousReplyDisplayMode.COURSE_ALIAS:
                if policy.course_alias is None or not re.fullmatch(
                    r"[0-9]{5}", policy.course_alias
                ):
                    raise ValueError("Course-alias reply policy requires a five-digit alias")
            elif policy.course_alias is not None:
                raise ValueError("Fully anonymous reply policy must not carry a course alias")
            self._policies[policy.case_id] = policy

    def get(self, case_id: str) -> AnonymousReplyCasePolicy | None:
        return self._policies.get(case_id)


class InMemoryAnonymousReplyAuditSink:
    """Private metadata-only fixture sink; raw reply text is intentionally absent."""

    def __init__(self) -> None:
        self._records: dict[str, AnonymousReplyAuditRecord] = {}

    @property
    def records(self) -> tuple[AnonymousReplyAuditRecord, ...]:
        return tuple(self._records.values())

    def get_by_operation_id(self, operation_id: str) -> AnonymousReplyAuditRecord | None:
        return self._records.get(operation_id)

    def append(self, record: AnonymousReplyAuditRecord) -> None:
        existing = self._records.get(record.operation_id)
        if existing is not None and existing != record:
            raise ConflictError("Anonymous reply operation already has another audit record.")
        self._records[record.operation_id] = record
