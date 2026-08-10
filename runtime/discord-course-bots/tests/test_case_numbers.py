from datetime import datetime, timezone
import re

import pytest

import discord_course_bots.repository as repository_module
from discord_course_bots.domain.case_numbers import generate_case_number
from discord_course_bots.repository import Repository


def test_public_and_private_case_number_formats() -> None:
    moment = datetime(2026, 7, 29, 2, 15, tzinfo=timezone.utc)
    public_number = generate_case_number(now=moment)
    private_number = generate_case_number(private_support=True, now=moment)

    assert re.fullmatch(r"C00-[A-Z0-9]{6}-0729-1015", public_number)
    assert re.fullmatch(r"C00-[A-Z0-9]{6}-0729-1015-P", private_number)


def test_public_case_number_collision_retries_with_a_new_number(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    numbers = iter(("C00-ABC123-0729-1015", "C00-ABC123-0729-1015", "C00-DEF456-0729-1015"))
    monkeypatch.setattr(repository_module, "generate_case_number", lambda: next(numbers))
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
    )

    assert first == "C00-ABC123-0729-1015"
    assert second == "C00-DEF456-0729-1015"


def test_private_case_number_collision_retries_with_a_new_number(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    numbers = iter(
        (
            "C00-ABC123-0729-1015-P",
            "C00-ABC123-0729-1015-P",
            "C00-DEF456-0729-1015-P",
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

    assert first == "C00-ABC123-0729-1015-P"
    assert second == "C00-DEF456-0729-1015-P"
