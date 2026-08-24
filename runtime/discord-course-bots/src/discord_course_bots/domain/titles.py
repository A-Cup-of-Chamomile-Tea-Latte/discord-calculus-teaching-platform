from __future__ import annotations

import re

_PREFIX_RE = re.compile(r"^\[[^\]]+\]\s*\[[^\]]+\]\s+")
_CLOSE_PREFIX_RE = re.compile(r"^(?:(?:✅|\(„• ֊ •„\))\s*)+")

MANUAL_CLOSE_PREFIX = "✅"
AUTOMATIC_CLOSE_PREFIX = "(„• ֊ •„)"


def strip_close_prefix(title: str) -> str:
    return _CLOSE_PREFIX_RE.sub("", title).strip()


def strip_system_prefix(title: str) -> str:
    return _PREFIX_RE.sub("", strip_close_prefix(title)).strip()


def canonical_title(module_code: str, class_code: str, keyword: str, body: str) -> str:
    clean_body = strip_system_prefix(body) or "未命名問題"
    return f"[{module_code} | C{class_code}][{keyword}] {clean_body}"[:100]


def cycle_title(base_title: str, reopen_count: int) -> str:
    """Return the title for a reopen cycle from its immutable initial title."""
    base_title = strip_close_prefix(base_title)
    if reopen_count <= 0:
        return base_title[:100]
    suffix = f" {reopen_count + 1}"
    return f"{base_title[: 100 - len(suffix)].rstrip()}{suffix}"


def closed_title(base_title: str, *, automatic: bool) -> str:
    """Prefix a closed case title without stacking old closure markers."""
    prefix = AUTOMATIC_CLOSE_PREFIX if automatic else MANUAL_CLOSE_PREFIX
    clean_title = strip_close_prefix(base_title)
    return f"{prefix} {clean_title[: 99 - len(prefix)].rstrip()}"
