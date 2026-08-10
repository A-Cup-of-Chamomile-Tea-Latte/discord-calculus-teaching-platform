from __future__ import annotations

import re
import unicodedata


class KeywordValidationError(ValueError):
    pass


_FORBIDDEN_PATTERNS = (
    re.compile(r"@everyone", re.IGNORECASE),
    re.compile(r"@here", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"<@&?\d+>"),
    re.compile(r"<#\d+>"),
)


def _weighted_length(value: str) -> int:
    total = 0
    for char in value:
        if char.isspace():
            total += 1
        elif unicodedata.east_asian_width(char) in {"W", "F", "A"}:
            total += 3
        else:
            total += 1
    return total


def normalize_keyword(raw: str) -> str:
    keyword = " ".join(raw.strip().split())
    if not keyword:
        raise KeywordValidationError("關鍵字不得空白。")
    if any(unicodedata.category(char).startswith("C") for char in keyword):
        raise KeywordValidationError("關鍵字包含控制字元。")
    if any(pattern.search(keyword) for pattern in _FORBIDDEN_PATTERNS):
        raise KeywordValidationError("關鍵字不得包含提及或網址。")
    if any(char in keyword for char in "[]`\\\n\r"):
        raise KeywordValidationError("關鍵字包含會破壞標題格式的字元。")
    if _weighted_length(keyword) > 30:
        raise KeywordValidationError("關鍵字過長；中文約 10 字、英文約 30 字元。")
    return keyword
