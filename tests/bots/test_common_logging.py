from __future__ import annotations

import json
from io import StringIO
from typing import Any

from bots.common.structured_logging import REDACTED, StructuredLogger


def test_structured_logger_redacts_registered_values_and_sensitive_fields() -> None:
    stream = StringIO()
    secret = "fixture-secret-value-never-output"
    logger = StructuredLogger(
        stream,
        component="fixture_bot",
        secrets=(secret,),
        now=lambda: "2026-07-19T10:00:00+00:00",
    )
    logger.emit(
        "info",
        "provider_result",
        message=f"provider rejected {secret}",
        token="another-value",
        discord_token="third-value",
        nested={"authorization": "Bearer hidden", "safe": "ok"},
    )
    text = stream.getvalue()
    assert secret not in text
    assert "another-value" not in text
    assert "Bearer hidden" not in text
    assert "third-value" not in text
    payload: dict[str, Any] = json.loads(text)
    assert payload["level"] == "INFO"
    assert payload["component"] == "fixture_bot"
    assert payload["token"] == REDACTED
    assert payload["discord_token"] == REDACTED
    assert payload["nested"] == {"authorization": REDACTED, "safe": "ok"}


def test_logger_emits_one_compact_json_object_per_event() -> None:
    stream = StringIO()
    logger = StructuredLogger(stream, component="fixture", now=lambda: "fixed")
    logger.emit("warning", "one", outcome="SAFE")
    logger.emit("error", "two", error=RuntimeError("fixture failure"))
    lines = stream.getvalue().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["event"] for line in lines] == ["one", "two"]
