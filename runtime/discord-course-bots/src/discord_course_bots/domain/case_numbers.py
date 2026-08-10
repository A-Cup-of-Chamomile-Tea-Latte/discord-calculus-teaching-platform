from __future__ import annotations

import secrets
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

TOKEN_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
TAIPEI_TIMEZONE = ZoneInfo("Asia/Taipei")


def generate_case_number(*, private_support: bool = False, now: datetime | None = None) -> str:
    moment = (now or datetime.now(UTC)).astimezone(TAIPEI_TIMEZONE)
    token = "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(6))
    suffix = "-P" if private_support else ""
    return f"C00-{token}-{moment:%m%d-%H%M}{suffix}"
