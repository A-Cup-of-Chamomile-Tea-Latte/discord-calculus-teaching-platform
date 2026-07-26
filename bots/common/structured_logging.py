"""Small JSON logger that redacts registered values and sensitive fields."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from io import TextIOBase

REDACTED = "<redacted>"
SENSITIVE_KEYS = {
    "authorization",
    "code",
    "cookie",
    "password",
    "plaintext_code",
    "secret",
    "token",
}


def _default_now() -> str:
    return datetime.now(UTC).isoformat()


class SecretRedactor:
    def __init__(self, secrets: Sequence[str] = ()) -> None:
        self._secrets = tuple(sorted((value for value in secrets if value), key=len, reverse=True))

    def redact(self, value: object, *, key: str | None = None) -> object:
        if key is not None:
            normalized_key = key.lower()
            if normalized_key in SENSITIVE_KEYS or normalized_key.endswith(
                ("_token", "_secret", "_password", "_api_key")
            ):
                return REDACTED
        if isinstance(value, str):
            result = value
            for secret in self._secrets:
                result = result.replace(secret, REDACTED)
            return result
        if isinstance(value, Mapping):
            return {
                str(item_key): self.redact(item_value, key=str(item_key))
                for item_key, item_value in value.items()
            }
        if isinstance(value, tuple | list):
            return [self.redact(item) for item in value]
        if value is None or isinstance(value, bool | int | float):
            return value
        return self.redact(str(value))


class StructuredLogger:
    def __init__(
        self,
        stream: TextIOBase,
        *,
        component: str,
        secrets: Sequence[str] = (),
        now: Callable[[], str] = _default_now,
    ) -> None:
        self._stream = stream
        self._component = component
        self._redactor = SecretRedactor(secrets)
        self._now = now

    def emit(self, level: str, event: str, **fields: object) -> None:
        payload: dict[str, object] = {
            "timestamp": self._now(),
            "level": level.upper(),
            "component": self._component,
            "event": event,
            **fields,
        }
        safe = self._redactor.redact(payload)
        self._stream.write(
            json.dumps(safe, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        )
        self._stream.flush()
