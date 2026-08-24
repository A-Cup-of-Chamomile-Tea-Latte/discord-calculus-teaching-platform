from discord_course_bots.domain.titles import (
    canonical_title,
    closed_title,
    cycle_title,
)


def test_first_cycle_title() -> None:
    assert canonical_title("M1", "01", "隱函數微分", "還有其他解法嗎？") == (
        "[M1 | C01][隱函數微分] 還有其他解法嗎？"
    )


def test_restores_prefix_without_duplication() -> None:
    assert (
        canonical_title("M1", "01", "隱函數微分", "[M1 | C01][隱函數微分] 還有其他解法嗎？")
        == "[M1 | C01][隱函數微分] 還有其他解法嗎？"
    )


def test_reopen_titles_always_derive_from_base_title() -> None:
    base_title = canonical_title("M1", "01", "隱函數微分", "還有其他解法嗎？")
    assert cycle_title(base_title, 1) == "[M1 | C01][隱函數微分] 還有其他解法嗎？ 2"
    assert cycle_title(base_title, 2) == "[M1 | C01][隱函數微分] 還有其他解法嗎？ 3"
    assert cycle_title(base_title, 3) == "[M1 | C01][隱函數微分] 還有其他解法嗎？ 4"


def test_number_at_end_of_original_title_is_not_removed() -> None:
    base_title = canonical_title("M1", "01", "極限", "第 7 題的第 2 小題")
    assert base_title == "[M1 | C01][極限] 第 7 題的第 2 小題"
    assert cycle_title(base_title, 1) == "[M1 | C01][極限] 第 7 題的第 2 小題 2"


def test_manual_and_automatic_close_titles_use_distinct_prefixes() -> None:
    base_title = "[M1] [極限] 第 7 題"
    assert closed_title(base_title, automatic=False) == "✅ [M1] [極限] 第 7 題"
    assert closed_title(base_title, automatic=True) == "(„• ֊ •„) [M1] [極限] 第 7 題"


def test_close_prefix_is_replaced_instead_of_stacked() -> None:
    title = "✅ („• ֊ •„) [M1] [極限] 第 7 題"
    assert closed_title(title, automatic=True) == "(„• ֊ •„) [M1] [極限] 第 7 題"
    assert cycle_title(title, 1) == "[M1] [極限] 第 7 題 2"
