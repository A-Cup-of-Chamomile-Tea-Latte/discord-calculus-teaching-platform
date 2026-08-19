from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from discord_course_bots.data_lab.carrier import (
    ensure_staging_carrier,
    load_staging_config,
    open_staging_repository,
)
from discord_course_bots.data_lab.contracts import (
    EnvelopeValidationError,
    canonical_json,
    validate_command_envelope,
)
from discord_course_bots.data_lab.fixtures import get_fixture
from discord_course_bots.data_lab.transport import FakeGasTransport


def _command_nonce(envelope: dict[str, Any]) -> str:
    return hashlib.sha256(
        (canonical_json(envelope) + "\nPHASE2B_COMMAND_APPLY").encode("utf-8")
    ).hexdigest()[:24]


def _validate_ordered(envelope: dict[str, Any], fingerprint: str, last_version: int) -> None:
    if envelope.get("sourceFingerprint") != fingerprint:
        raise EnvelopeValidationError("SYNC_WRONG_TARGET")
    if envelope.get("schemaVersion") != "2.0.0":
        raise EnvelopeValidationError("SYNC_SCHEMA_VERSION_UNSUPPORTED")
    if envelope.get("environment") != "STAGING":
        raise EnvelopeValidationError("SYNC_WRONG_ENVIRONMENT")
    if envelope.get("syntheticOnly") is not True:
        raise EnvelopeValidationError("SYNC_NON_SYNTHETIC_REFUSED")
    version = envelope.get("sourceVersion")
    if not isinstance(version, int) or version <= last_version:
        raise EnvelopeValidationError("SYNC_STALE_VERSION")
    validate_command_envelope(envelope, fingerprint)


def _read_validation_state(database: Path, command_id: str) -> tuple[int, dict[str, str] | None]:
    if not database.exists():
        return 0, None
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        sync = connection.execute(
            "SELECT last_remote_source_version FROM sync_state "
            "WHERE stream_name = 'cloud-command-inbox'"
        ).fetchone()
        existing = connection.execute(
            "SELECT envelope_sha256, status FROM inbound_commands WHERE command_id = ?",
            (command_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return 0, None
    finally:
        connection.close()
    return (
        0 if sync is None else int(sync[0]),
        None
        if existing is None
        else {
            "envelope_sha256": str(existing["envelope_sha256"]),
            "status": str(existing["status"]),
        },
    )


def fetch_once(
    root: Path,
    transport: FakeGasTransport,
    *,
    apply: bool,
    confirmation_nonce: str | None = None,
    simulate_ack_failure: bool = False,
) -> dict[str, Any]:
    paths = ensure_staging_carrier(root)
    config = load_staging_config(paths)
    preview = transport.preview_commands(1)
    if not preview:
        return {"status": "NO_WORK", "safeResultCode": "COMMAND_QUEUE_EMPTY"}
    envelope = preview[0]
    last_version, existing = _read_validation_state(
        paths.database, str(envelope.get("commandId", ""))
    )
    exact_replay = (
        existing is not None
        and existing["envelope_sha256"] == str(envelope.get("checksum"))
        and existing["status"] == "APPLIED"
    )
    validation_floor = (
        min(last_version, int(envelope.get("sourceVersion", 0)) - 1)
        if exact_replay
        else last_version
    )
    try:
        _validate_ordered(
            envelope,
            str(config["expectedSourceFingerprint"]),
            validation_floor,
        )
    except EnvelopeValidationError as error:
        return {
            "status": "REJECTED",
            "safeResultCode": error.code,
            "localMutation": False,
            "cloudMutation": False,
        }
    nonce = _command_nonce(envelope)
    if not apply:
        return {
            "status": "PREVIEW",
            "commandId": envelope["commandId"],
            "commandType": envelope["commandType"],
            "sourceVersion": envelope["sourceVersion"],
            "checksum": str(envelope["checksum"])[:12],
            "confirmationNonce": nonce,
            "localMutation": False,
            "cloudMutation": False,
            "nextExpectedAction": "fetch --once --apply --confirm <nonce>",
        }
    if confirmation_nonce != nonce:
        raise RuntimeError("CONFIRMATION_NONCE_MISMATCH")
    claim = transport.claim_command("phase2b-local-fetch")
    if claim is None or claim.envelope["commandId"] != envelope["commandId"]:
        raise RuntimeError("REMOTE_COMMAND_CLAIM_FAILED")
    fixture = get_fixture(str(envelope["payloadRef"]))
    repository = open_staging_repository(paths)
    try:
        result = repository.apply_command(envelope, fixture)
        if simulate_ack_failure:
            return {
                "status": "LOCAL_APPLIED_REMOTE_ACK_PENDING",
                "commandId": envelope["commandId"],
                "safeResultCode": "REMOTE_ACK_FAILED",
                "localMutation": not result.no_op,
                "cloudMutation": False,
            }
        remote_code = "NO_OP" if result.no_op else "APPLIED"
        if not transport.ack_command(str(envelope["commandId"]), claim.claim_token, remote_code):
            raise RuntimeError("REMOTE_ACK_FAILED")
        return {
            "status": "NO_OP" if result.no_op else "APPLIED",
            "commandId": envelope["commandId"],
            "caseRef": result.case_ref,
            "sourceVersion": result.source_version,
            "safeResultCode": "COMMAND_NOOP" if result.no_op else "COMMAND_APPLIED",
            "localMutation": not result.no_op,
            "cloudMutation": bool(getattr(transport, "is_cloud", True)),
            "transportMutation": True,
            "transport": getattr(transport, "transport_name", "UNKNOWN"),
        }
    finally:
        repository.close()


def command_status(root: Path, command_id: str) -> dict[str, Any]:
    paths = ensure_staging_carrier(root)
    repository = open_staging_repository(paths)
    try:
        row = repository.command_by_id(command_id)
        if row is None:
            return {"commandId": command_id, "status": "NOT_FOUND"}
        return {
            "commandId": command_id,
            "status": str(row["status"]),
            "sourceVersion": int(row["source_version"]),
            "checksum": str(row["envelope_sha256"])[:12],
            "safeResultCode": row["result_code"],
            "timestamp": str(row["updated_at"]),
            "nextExpectedAction": "project" if row["status"] == "APPLIED" else "fetch",
        }
    finally:
        repository.close()
