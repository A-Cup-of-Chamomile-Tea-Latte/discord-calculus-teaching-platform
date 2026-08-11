from __future__ import annotations

from datetime import UTC, datetime

import pytest

from discord_course_bots.data_lab.contracts import (
    EnvelopeValidationError,
    build_command_envelope,
    canonical_json,
    validate_command_envelope,
    with_checksum,
)
from discord_course_bots.data_lab.fixtures import FIXTURE_CATALOG, get_fixture

FINGERPRINT = "SYNTHETIC-SHEET-FINGERPRINT"


def command() -> dict[str, object]:
    return build_command_envelope(
        command_id="CMD-TST-001",
        command_type="CREATE_SYNTHETIC_CASE",
        payload_ref="fixture://public/basic-v1",
        target_case_ref=None,
        idempotency_key="fixture-create-001",
        source_version=1,
        requested_at=datetime(2026, 8, 11, tzinfo=UTC).isoformat(),
        source_fingerprint=FINGERPRINT,
    )


def test_command_envelope_is_canonical_and_verifiable() -> None:
    envelope = command()
    validate_command_envelope(envelope, FINGERPRINT)
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert envelope["requestedAt"] == "2026-08-11T00:00:00Z"
    assert len(str(envelope["checksum"])) == 64


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("sourceFingerprint", "wrong", "SYNC_WRONG_TARGET"),
        ("schemaVersion", "9.0.0", "SYNC_SCHEMA_VERSION_UNSUPPORTED"),
        ("environment", "PRODUCTION", "SYNC_WRONG_ENVIRONMENT"),
        ("syntheticOnly", False, "SYNC_NON_SYNTHETIC_REFUSED"),
        ("commandType", "DELETE_CASE", "COMMAND_TYPE_UNSUPPORTED"),
        ("payloadRef", "fixture://unknown", "FIXTURE_REF_UNSUPPORTED"),
    ],
)
def test_command_validation_fails_closed(field: str, value: object, code: str) -> None:
    envelope = command()
    envelope[field] = value
    if field in {"commandType", "payloadRef"}:
        envelope = with_checksum(envelope)
    with pytest.raises(EnvelopeValidationError, match=code):
        validate_command_envelope(envelope, FINGERPRINT)


def test_bad_checksum_and_floats_are_rejected() -> None:
    envelope = command()
    envelope["checksum"] = "0" * 64
    with pytest.raises(EnvelopeValidationError, match="SYNC_BAD_CHECKSUM"):
        validate_command_envelope(envelope, FINGERPRINT)
    with pytest.raises(EnvelopeValidationError, match="FLOAT_NOT_ALLOWED"):
        canonical_json({"bad": 1.5})


def test_fixture_catalog_is_synthetic_metadata_only() -> None:
    assert set(FIXTURE_CATALOG) == {
        "fixture://public/basic-v1",
        "fixture://public/close-reopen-v1",
        "fixture://failure/stale-version-v1",
        "fixture://failure/bad-checksum-v1",
    }
    serialized = canonical_json({"fixtures": list(FIXTURE_CATALOG.values())})
    for forbidden in ("email", "studentId", "discordId", "messageBody", "attachment", "filename"):
        assert forbidden not in serialized
    assert get_fixture("fixture://public/basic-v1")["analysisEligible"] is False
