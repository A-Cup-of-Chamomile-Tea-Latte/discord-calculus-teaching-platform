from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from tools.case_id import (
    CaseIdCollisionError,
    CaseIdIssuer,
    CaseIdMapping,
    CaseNumberParts,
    InMemoryCaseIdMappingRepository,
    format_case_number,
    mask_case_number,
    parse_case_number,
    validate_case_number,
)


def values(*items: str) -> Iterator[str]:
    yield from items


def test_normal_case_parse_validate_format_and_mask() -> None:
    case_number = "C12-7K4M2Q-0907-2007"
    parts = parse_case_number(case_number)
    assert parts == CaseNumberParts("12", "7K4M2Q", 9, 7, 20, 7)
    assert format_case_number(parts) == case_number
    assert validate_case_number(case_number)
    assert mask_case_number(case_number) == "C12-7K****-0907-2007"


def test_private_case_preserves_suffix_when_formatted_and_masked() -> None:
    case_number = "C12-7K4M2Q-0907-2007-P"
    assert parse_case_number(case_number).private is True
    assert mask_case_number(case_number) == "C12-7K****-0907-2007-P"


def test_c99_special_identity_is_supported() -> None:
    case_number = "C99-R8N6WX-0907-2007"
    assert parse_case_number(case_number).class_code == "99"
    assert validate_case_number(case_number)


@pytest.mark.parametrize(
    "value",
    [
        "C1-7K4M2Q-0907-2007",
        "C12-7K4MIQ-0907-2007",
        "C12-7K4M2Q-0230-2007",
        "C12-7K4M2Q-0907-2460",
        "c12-7K4M2Q-0907-2007",
        "C12-7K4M2Q-0907-2007-p",
    ],
)
def test_invalid_or_noncanonical_values_are_rejected(value: str) -> None:
    assert validate_case_number(value) is False
    with pytest.raises(ValueError):
        parse_case_number(value)


def test_issue_converts_cross_timezone_time_to_course_wall_clock_and_maps_uuid() -> None:
    repository = InMemoryCaseIdMappingRepository()
    expected_uuid = uuid.UUID("12345678-1234-4abc-8def-1234567890ab")
    issuer = CaseIdIssuer(
        repository,
        token_factory=lambda: "7K4M2Q",
        uuid_factory=lambda: expected_uuid,
    )

    mapping = issuer.issue(
        class_code="12",
        created_at=datetime(2026, 9, 7, 12, 7, tzinfo=UTC),
    )

    assert mapping.case_number == "C12-7K4M2Q-0907-2007"
    assert mapping.internal_case_id == expected_uuid
    assert repository.find_by_case_number(mapping.case_number) == mapping
    assert repository.find_by_internal_case_id(expected_uuid) == mapping
    assert str(expected_uuid) not in mapping.case_number


def test_collision_retries_with_fresh_random_token() -> None:
    repository = InMemoryCaseIdMappingRepository()
    created_at = datetime(2026, 9, 7, 12, 7, tzinfo=UTC)
    existing = CaseIdMapping(
        uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        "C12-7K4M2Q-0907-2007",
        created_at,
    )
    repository.save(existing)
    tokens = values("7K4M2Q", "R8N6WX")
    issuer = CaseIdIssuer(
        repository,
        token_factory=lambda: next(tokens),
        uuid_factory=lambda: uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
    )

    issued = issuer.issue(class_code="12", created_at=created_at)

    assert issued.case_number == "C12-R8N6WX-0907-2007"


def test_collision_retry_is_bounded_and_naive_time_is_rejected() -> None:
    repository = InMemoryCaseIdMappingRepository()
    created_at = datetime(2026, 9, 7, 20, 7, tzinfo=UTC)
    repository.save(
        CaseIdMapping(
            uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            "C12-7K4M2Q-0908-0407",
            created_at,
        )
    )
    issuer = CaseIdIssuer(repository, token_factory=lambda: "7K4M2Q", max_attempts=2)

    with pytest.raises(CaseIdCollisionError):
        issuer.issue(class_code="12", created_at=created_at)
    with pytest.raises(ValueError, match="timezone-aware"):
        issuer.issue(class_code="12", created_at=datetime(2026, 9, 7, 20, 7))
