from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

SCHEMA_VERSION = "2.0.0"
ENVIRONMENT = "STAGING"
COMMAND_TYPES = frozenset(
    {
        "CREATE_SYNTHETIC_CASE",
        "CLOSE_SYNTHETIC_CASE",
        "REOPEN_SYNTHETIC_CASE",
        "REPLAY_LAST_SYNTHETIC_COMMAND",
    }
)
FIXTURE_REFS = frozenset(
    {
        "fixture://public/basic-v1",
        "fixture://public/close-reopen-v1",
        "fixture://failure/stale-version-v1",
        "fixture://failure/bad-checksum-v1",
    }
)


class EnvelopeValidationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def utc_z(value: str | datetime) -> str:
    moment = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(value.replace("Z", "+00:00"))
    )
    if moment.tzinfo is None:
        raise EnvelopeValidationError("TIMESTAMP_TIMEZONE_REQUIRED")
    return moment.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _reject_floats(value: Any) -> None:
    if isinstance(value, float):
        raise EnvelopeValidationError("FLOAT_NOT_ALLOWED")
    if isinstance(value, dict):
        for item in value.values():
            _reject_floats(item)
    elif isinstance(value, list):
        for item in value:
            _reject_floats(item)


def canonical_json(value: dict[str, Any], *, exclude_checksum: bool = False) -> str:
    payload = dict(value)
    if exclude_checksum:
        payload.pop("checksum", None)
    _reject_floats(payload)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def checksum_for(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value, exclude_checksum=True).encode("utf-8")).hexdigest()


def with_checksum(value: dict[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    payload["checksum"] = checksum_for(payload)
    return payload


def abbreviated_checksum(value: str | None) -> str | None:
    return None if value is None else value[:12]


def validate_common_envelope(envelope: dict[str, Any], expected_fingerprint: str) -> None:
    if envelope.get("sourceFingerprint") != expected_fingerprint:
        raise EnvelopeValidationError("SYNC_WRONG_TARGET")
    if envelope.get("schemaVersion") != SCHEMA_VERSION:
        raise EnvelopeValidationError("SYNC_SCHEMA_VERSION_UNSUPPORTED")
    if envelope.get("environment") != ENVIRONMENT:
        raise EnvelopeValidationError("SYNC_WRONG_ENVIRONMENT")
    if envelope.get("syntheticOnly") is not True:
        raise EnvelopeValidationError("SYNC_NON_SYNTHETIC_REFUSED")
    checksum = envelope.get("checksum")
    if not isinstance(checksum, str) or checksum != checksum_for(envelope):
        raise EnvelopeValidationError("SYNC_BAD_CHECKSUM")


def validate_command_envelope(envelope: dict[str, Any], expected_fingerprint: str) -> None:
    validate_common_envelope(envelope, expected_fingerprint)
    command_id = envelope.get("commandId")
    if not isinstance(command_id, str) or not command_id.startswith("CMD-TST-"):
        raise EnvelopeValidationError("COMMAND_ID_INVALID")
    command_type = envelope.get("commandType")
    if command_type not in COMMAND_TYPES:
        raise EnvelopeValidationError("COMMAND_TYPE_UNSUPPORTED")
    if envelope.get("payloadRef") not in FIXTURE_REFS:
        raise EnvelopeValidationError("FIXTURE_REF_UNSUPPORTED")
    target = envelope.get("targetCaseRef")
    if target is not None and (not isinstance(target, str) or not target.startswith("TST-")):
        raise EnvelopeValidationError("TARGET_CASE_REF_INVALID")
    if not isinstance(envelope.get("sourceVersion"), int) or envelope["sourceVersion"] <= 0:
        raise EnvelopeValidationError("SOURCE_VERSION_INVALID")
    if not isinstance(envelope.get("idempotencyKey"), str) or not envelope["idempotencyKey"]:
        raise EnvelopeValidationError("IDEMPOTENCY_KEY_REQUIRED")
    if not isinstance(envelope.get("requestedAt"), str):
        raise EnvelopeValidationError("REQUESTED_AT_REQUIRED")
    utc_z(envelope["requestedAt"])


def build_command_envelope(
    *,
    command_id: str,
    command_type: str,
    payload_ref: str,
    target_case_ref: str | None,
    idempotency_key: str,
    source_version: int,
    requested_at: str,
    source_fingerprint: str,
) -> dict[str, Any]:
    return with_checksum(
        {
            "schemaVersion": SCHEMA_VERSION,
            "environment": ENVIRONMENT,
            "syntheticOnly": True,
            "commandId": command_id,
            "commandType": command_type,
            "payloadRef": payload_ref,
            "targetCaseRef": target_case_ref,
            "idempotencyKey": idempotency_key,
            "sourceVersion": source_version,
            "requestedAt": utc_z(requested_at),
            "sourceFingerprint": source_fingerprint,
        }
    )


def build_projection_envelope(
    *,
    source_version: int,
    generated_at: str,
    source_fingerprint: str,
    rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    scopes = ["Overview", "CaseBoard", "Operations", "History"]
    return with_checksum(
        {
            "schemaVersion": SCHEMA_VERSION,
            "environment": ENVIRONMENT,
            "syntheticOnly": True,
            "sourceVersion": source_version,
            "generatedAt": utc_z(generated_at),
            "sourceFingerprint": source_fingerprint,
            "scopes": scopes,
            "rowCounts": {scope: len(rows.get(scope, [])) for scope in scopes},
            "rows": {scope: rows.get(scope, []) for scope in scopes},
        }
    )
