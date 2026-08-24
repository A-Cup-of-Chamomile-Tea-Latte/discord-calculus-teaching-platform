from __future__ import annotations

import secrets
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TAIPEI_TIMEZONE = ZoneInfo("Asia/Taipei")


def generate_case_number(
    *, class_code: str | None = None, private_support: bool = False, now: datetime | None = None
) -> str:
    normalized_class = "99" if private_support else (class_code or "").strip().upper()
    if normalized_class.startswith("C"):
        normalized_class = normalized_class[1:]
    if not (
        normalized_class == "99"
        or (normalized_class.isdigit() and 1 <= int(normalized_class) <= 16)
    ):
        raise ValueError("公開案件必須提供 01 至 16 的正式班別。")
    normalized_class = f"{int(normalized_class):02d}"
    moment = (now or datetime.now(UTC)).astimezone(TAIPEI_TIMEZONE)
    token = "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(6))
    suffix = "-P" if private_support else ""
    return f"C{normalized_class}-{token}-{moment:%m%d-%H%M}{suffix}"
