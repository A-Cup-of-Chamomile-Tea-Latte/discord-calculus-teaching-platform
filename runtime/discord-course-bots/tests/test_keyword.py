import pytest

from discord_course_bots.domain.keyword import KeywordValidationError, normalize_keyword


def test_normalizes_whitespace() -> None:
    assert normalize_keyword("  隱函數   微分 ") == "隱函數 微分"


@pytest.mark.parametrize("value", ["", "@everyone", "https://example.com", "[M1]", "<@123>"])
def test_rejects_unsafe_keyword(value: str) -> None:
    with pytest.raises(KeywordValidationError):
        normalize_keyword(value)


def test_weighted_length() -> None:
    assert normalize_keyword("abcdefghij" * 3) == "abcdefghij" * 3
    with pytest.raises(KeywordValidationError):
        normalize_keyword("微" * 11)
