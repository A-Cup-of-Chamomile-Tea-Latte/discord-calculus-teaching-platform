from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from discord_course_bots.data_lab.carrier import (
    LabPaths,
    ensure_staging_carrier,
    load_staging_config,
    open_staging_repository,
)
from discord_course_bots.data_lab.contracts import canonical_json
from discord_course_bots.data_lab.fixtures import get_fixture
from discord_course_bots.repository_time import utc_now_iso


class ConfirmationError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    if not path.exists():
        return "ABSENT"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_case_status(paths: LabPaths, case_ref: str) -> str | None:
    if not paths.database.exists():
        return None
    import sqlite3

    connection = sqlite3.connect(f"file:{paths.database}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT status FROM cases WHERE case_number = ?", (case_ref,)
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        connection.close()
    return None if row is None else str(row[0])


def plan_ingest(paths: LabPaths, fixture_ref: str) -> dict[str, Any]:
    fixture = get_fixture(fixture_ref)
    fixture["fixtureRef"] = fixture_ref
    current = _read_case_status(paths, str(fixture["caseRef"]))
    planned = {
        "operation": "INGEST_SYNTHETIC_FIXTURE",
        "environment": "STAGING",
        "syntheticOnly": True,
        "liveDiscordEnabled": False,
        "fixtureRef": fixture_ref,
        "caseRef": fixture["caseRef"],
        "previousStatus": current,
        "newStatus": fixture["lifecycleStatus"],
        "outboxScopes": ["CASEBOARD", "HISTORY", "OVERVIEW", "OPERATIONS"],
        "databaseSha256": file_sha256(paths.database),
    }
    plan_hash = hashlib.sha256(canonical_json(planned).encode("utf-8")).hexdigest()
    planned["runId"] = f"run-{plan_hash[:12]}"
    planned["confirmationNonce"] = plan_hash[:24]
    return planned


def dry_run_ingest(root: Path, fixture_ref: str) -> dict[str, Any]:
    paths = ensure_staging_carrier(root)
    before = file_sha256(paths.database)
    plan = plan_ingest(paths, fixture_ref)
    after = file_sha256(paths.database)
    if before != after:
        raise RuntimeError("DRY_RUN_DATABASE_CHANGED")
    return {**plan, "dryRun": True, "databaseUnchanged": True}


def apply_ingest(root: Path, fixture_ref: str, confirmation_nonce: str) -> dict[str, Any]:
    paths = ensure_staging_carrier(root)
    plan = plan_ingest(paths, fixture_ref)
    if confirmation_nonce != plan["confirmationNonce"]:
        raise ConfirmationError("CONFIRMATION_NONCE_MISMATCH")
    fixture = get_fixture(fixture_ref)
    fixture["fixtureRef"] = fixture_ref
    repository = open_staging_repository(paths)
    try:
        result = repository.apply_fixture(
            fixture,
            correlation_id=str(plan["runId"]),
        )
    finally:
        repository.close()
    receipt = {
        "runId": plan["runId"],
        "status": "APPLIED",
        "environment": "STAGING",
        "syntheticOnly": True,
        "caseRef": result.case_ref,
        "previousStatus": result.previous_status,
        "newStatus": result.new_status,
        "sourceVersion": result.source_version,
        "outboxCount": result.outbox_count,
        "safeResultCode": "SYNTHETIC_FIXTURE_APPLIED",
        "timestamp": utc_now_iso(),
    }
    receipt_path = paths.receipts / f"{plan['runId']}.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {**receipt, "receipt": str(receipt_path)}


def case_status(root: Path, case_ref: str) -> dict[str, Any]:
    paths = ensure_staging_carrier(root)
    repository = open_staging_repository(paths)
    try:
        row = repository.case_by_ref(case_ref)
        if row is None:
            return {"caseRef": case_ref, "status": "NOT_FOUND", "environment": "STAGING"}
        return {
            "caseRef": case_ref,
            "status": str(row["status"]),
            "module": str(row["module_code"]),
            "keyword": str(row["keyword"]),
            "reopenCount": int(row["reopen_count"]),
            "analysisEligible": False,
            "environment": "STAGING",
        }
    finally:
        repository.close()


def inspect_run(root: Path, run_id: str) -> dict[str, Any]:
    paths = ensure_staging_carrier(root)
    receipt_path = paths.receipts / f"{run_id}.json"
    receipt = (
        json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt_path.exists()
        else {"runId": run_id, "status": "NOT_FOUND", "safeResultCode": "RUN_NOT_FOUND"}
    )
    repository = open_staging_repository(paths)
    try:
        case_ref = receipt.get("caseRef")
        case = None if not case_ref else repository.case_by_ref(str(case_ref))
        outbox = list(
            repository._connection.execute(  # noqa: SLF001 - observer is repository-local
                "SELECT status, source_version, payload_sha256, updated_at, last_error_code "
                "FROM projection_outbox ORDER BY created_at"
            ).fetchall()
        )
    finally:
        repository.close()
    return {
        "runId": run_id,
        "cloudCommand": {"status": "NOT_APPLICABLE", "nextExpectedAction": "none"},
        "localFetchValidation": {"status": "LOCAL_ORIGIN", "nextExpectedAction": "none"},
        "localInboundLedger": {"status": "NOT_APPLICABLE", "nextExpectedAction": "none"},
        "syntheticCaseState": {
            "status": "NOT_FOUND" if case is None else str(case["status"]),
            "sourceVersion": receipt.get("sourceVersion"),
            "timestamp": receipt.get("timestamp"),
            "safeResultCode": receipt.get("safeResultCode"),
            "nextExpectedAction": "project" if case is not None else "inspect run id",
        },
        "projectionOutbox": [
            {
                "status": str(row["status"]),
                "sourceVersion": int(row["source_version"]),
                "checksum": None
                if row["payload_sha256"] is None
                else str(row["payload_sha256"])[:12],
                "timestamp": str(row["updated_at"]),
                "safeResultCode": row["last_error_code"],
                "nextExpectedAction": "project" if row["status"] != "COMPLETED" else "none",
            }
            for row in outbox
        ],
        "cloudProjectionReceipt": {
            "status": "NOT_RUN",
            "nextExpectedAction": "project --once --dry-run",
        },
        "finalHumanViewState": {
            "status": "NOT_PROJECTED",
            "nextExpectedAction": "project --once --dry-run",
        },
    }


def staging_summary(root: Path) -> dict[str, Any]:
    paths = ensure_staging_carrier(root)
    config = load_staging_config(paths)
    repository = open_staging_repository(paths)
    try:
        return {
            "environment": config["environment"],
            "syntheticOnly": config["syntheticOnly"],
            "liveDiscordEnabled": config["liveDiscordEnabled"],
            "schemaVersion": repository.schema_version,
            "counts": repository.counts(),
            "migrations": [dict(row) for row in repository.migration_history()],
        }
    finally:
        repository.close()
