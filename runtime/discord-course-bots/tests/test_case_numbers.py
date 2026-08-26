import re
from datetime import UTC, datetime

import pytest

import discord_course_bots.repository as repository_module
from discord_course_bots.domain.case_numbers import generate_case_number
from discord_course_bots.repository import Repository


def test_public_and_private_case_number_formats() -> None:
    moment = datetime(2026, 7, 29, 2, 15, tzinfo=UTC)
    public_number = generate_case_number(class_code="01", now=moment)
    private_number = generate_case_number(private_support=True, now=moment)
    guest_number = generate_case_number(guest=True, now=moment)

    assert re.fullmatch(r"C01-[A-HJ-NP-Z2-9]{6}-0729-1015", public_number)
    assert re.fullmatch(r"C99-[A-HJ-NP-Z2-9]{6}-0729-1015-P", private_number)
    assert re.fullmatch(r"Guest-[A-HJ-NP-Z2-9]{6}-0729-1015", guest_number)


def test_public_case_number_collision_retries_with_a_new_number(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    numbers = iter(("C01-ABC234-0729-1015", "C01-ABC234-0729-1015", "C01-DEF456-0729-1015"))
    monkeypatch.setattr(
        repository_module, "generate_case_number", lambda *, class_code: next(numbers)
    )
    repo = Repository(tmp_path / "test.sqlite3")

    first = repo.create_case(
        case_id="case-1",
        thread_id=1,
        author_id=3,
        module_code="M1",
        keyword="test",
        ai_content_permission=False,
        canonical_title="[M1] [test] Question",
        initial_snapshot={"body": "hello"},
        class_code="01",
    )
    second = repo.create_case(
        case_id="case-2",
        thread_id=2,
        author_id=4,
        module_code="M1",
        keyword="test",
        ai_content_permission=False,
        canonical_title="[M1] [test] Another question",
        initial_snapshot={"body": "hello"},
        class_code="01",
    )

    assert first == "C01-ABC234-0729-1015"
    assert second == "C01-DEF456-0729-1015"


def test_private_case_number_collision_retries_with_a_new_number(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    numbers = iter(
        (
            "C99-ABC234-0729-1015-P",
            "C99-ABC234-0729-1015-P",
            "C99-DEF456-0729-1015-P",
        )
    )
    monkeypatch.setattr(
        repository_module,
        "generate_case_number",
        lambda *, private_support: next(numbers),
    )
    repo = Repository(tmp_path / "test.sqlite3")

    first = repo.create_private_support(1, 3, False)
    second = repo.create_private_support(2, 4, True)

    assert first == "C99-ABC234-0729-1015-P"
    assert second == "C99-DEF456-0729-1015-P"
