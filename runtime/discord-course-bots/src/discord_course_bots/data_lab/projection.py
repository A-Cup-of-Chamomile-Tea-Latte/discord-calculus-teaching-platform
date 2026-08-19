from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from discord_course_bots.data_lab.carrier import (
    LabPaths,
    ensure_staging_carrier,
    load_staging_config,
    open_staging_repository,
)
from discord_course_bots.data_lab.contracts import build_projection_envelope
from discord_course_bots.data_lab.repository import DataLabRepository
from discord_course_bots.data_lab.transport import ProjectionTransport
from discord_course_bots.repository_time import utc_now_iso


def _coalesced(rows: list[Any]) -> list[Any]:
    latest: dict[tuple[str, str], Any] = {}
    history: list[Any] = []
    for row in rows:
        if row["projection_scope"] == "HISTORY":
            history.append(row)
            continue
        key = (str(row["aggregate_ref"]), str(row["projection_scope"]))
        current = latest.get(key)
        if current is None or int(row["source_version"]) > int(current["source_version"]):
            latest[key] = row
    return [*latest.values(), *history]


def _caseboard_row(
    repository: DataLabRepository,
    case_ref: str,
    version: int,
    *,
    synthetic_only: bool,
) -> dict[str, Any]:
    row = repository.case_by_ref(case_ref)
    if row is None:
        raise RuntimeError("PROJECTION_CASE_MISSING")
    return {
        "schemaVersion": "2.0.0",
        "caseNumber": case_ref,
        "moduleCode": str(row["module_code"]),
        "status": str(row["status"]),
        "assignedAlias": "SYN-LAB-TA" if synthetic_only else None,
        "actionNeeded": "NONE" if row["status"] == "CLOSED" else "REVIEW",
        "lastStudentAt": None,
        "lastStaffAt": None,
        "nextDeadlineAt": None,
        "analysisEligible": False if synthetic_only else bool(row["ai_content_permission"]),
        "updatedAt": str(row["closed_at"] or row["created_at"]),
        "sourceVersion": version,
        "sourceChecksum": f"pending-v{version}",
    }


def _overview_rows(
    repository: DataLabRepository,
    now: str,
    *,
    environment: str,
    synthetic_only: bool,
) -> list[dict[str, Any]]:
    condition = "case_number LIKE 'TST-%'" if synthetic_only else "case_number NOT LIKE 'TST-%'"
    counts = repository._connection.execute(  # noqa: SLF001
        f"SELECT status, COUNT(*) AS count FROM cases WHERE {condition} GROUP BY status"
    ).fetchall()
    values = {str(row["status"]): int(row["count"]) for row in counts}
    return [
        {
            "metricKey": "cases.open",
            "metricValue": str(values.get("OPEN", 0) + values.get("TRACKED", 0)),
            "status": environment,
            "description": "目前待處理案件",
            "asOf": now,
            "sourceReceipt": f"{environment}-SQLITE",
        },
        {
            "metricKey": "cases.closed",
            "metricValue": str(values.get("CLOSED", 0)),
            "status": environment,
            "description": "目前已結案件",
            "asOf": now,
            "sourceReceipt": f"{environment}-SQLITE",
        },
    ]


def _operations_rows(
    repository: DataLabRepository,
    now: str,
    *,
    environment: str,
    synthetic_only: bool,
) -> list[dict[str, Any]]:
    depth = repository._connection.execute(  # noqa: SLF001
        "SELECT COUNT(*) FROM projection_outbox WHERE status != 'COMPLETED'"
    ).fetchone()[0]
    health_rows = repository._connection.execute(  # noqa: SLF001
        "SELECT * FROM service_health ORDER BY service_key"
    ).fetchall()
    if not health_rows:
        return [
            {
                "schemaVersion": "2.0.0",
                "operationKey": "data-bridge",
                "service": "calculus-data-bridge",
                "component": "projection-outbox",
                "status": "HEALTHY",
                "mode": "SYNTHETIC_ONLY" if synthetic_only else "PRODUCTION",
                "version": "phase-2c",
                "lastHeartbeatAt": now,
                "queueDepth": int(depth),
                "lastSuccessAt": None,
                "safeErrorCode": None,
                "nextAction": "none",
                "checkedAt": now,
            }
        ]
    return [
        {
            "schemaVersion": "2.0.0",
            "operationKey": str(health["service_key"]),
            "service": str(health["service"]),
            "component": str(health["component"]),
            "status": str(health["status"]),
            "mode": str(health["mode"]),
            "version": health["version"],
            "lastHeartbeatAt": health["last_heartbeat_at"],
            "queueDepth": int(depth) if health["service_key"] == "data-bridge" else 0,
            "lastSuccessAt": health["last_success_at"],
            "safeErrorCode": health["safe_error_code"],
            "nextAction": health["next_action"],
            "checkedAt": str(health["checked_at"]),
        }
        for health in health_rows
    ]


def _history_row(repository: DataLabRepository, outbox: Any) -> dict[str, Any]:
    projection_id = str(outbox["projection_id"])
    if not projection_id.startswith("prj-evt-") or not projection_id.endswith("-history"):
        raise RuntimeError("PROJECTION_EVENT_REF_INVALID")
    event_id = projection_id[len("prj-") : -len("-history")]
    event = repository._connection.execute(  # noqa: SLF001
        """
        SELECT * FROM case_lifecycle_events
        WHERE event_id = ?
        """,
        (event_id,),
    ).fetchone()
    if event is None:
        raise RuntimeError("PROJECTION_EVENT_MISSING")
    return {
        "schemaVersion": "2.0.0",
        "eventRef": str(event["event_id"]),
        "eventType": str(event["event_type"]),
        "subjectType": "PUBLIC_CASE",
        "subjectRef": str(event["case_ref"]),
        "summaryCode": (
            f"SYNTHETIC_CASE_{event['event_type']}"
            if int(event["synthetic"]) == 1
            else f"PUBLIC_CASE_{event['event_type']}"
        ),
        "fromState": event["previous_status"],
        "toState": str(event["new_status"]),
        "occurredAt": str(event["occurred_at"]),
        "source": str(event["source_kind"]),
        "sourceReceipt": str(event["correlation_id"]),
    }


def build_pending_envelope(
    repository: DataLabRepository,
    fingerprint: str,
    *,
    environment: str = "STAGING",
    synthetic_only: bool = True,
) -> tuple[dict[str, Any] | None, list[str]]:
    pending = repository.pending_projection_rows(50)
    if not pending:
        return None, []
    selected = _coalesced(pending)
    now = utc_now_iso()
    version = max(int(row["source_version"]) for row in selected)
    rows: dict[str, list[dict[str, Any]]] = {
        "Overview": [],
        "CaseBoard": [],
        "Operations": [],
        "History": [],
    }
    for row in selected:
        scope = str(row["projection_scope"])
        if scope == "CASEBOARD":
            rows["CaseBoard"].append(
                _caseboard_row(
                    repository,
                    str(row["aggregate_ref"]),
                    int(row["source_version"]),
                    synthetic_only=synthetic_only,
                )
            )
        elif scope == "HISTORY":
            rows["History"].append(_history_row(repository, row))
        elif scope == "OVERVIEW":
            rows["Overview"] = _overview_rows(
                repository,
                now,
                environment=environment,
                synthetic_only=synthetic_only,
            )
        elif scope == "OPERATIONS":
            rows["Operations"] = _operations_rows(
                repository,
                now,
                environment=environment,
                synthetic_only=synthetic_only,
            )
    envelope = build_projection_envelope(
        source_version=version,
        generated_at=now,
        source_fingerprint=fingerprint,
        rows=rows,
        environment=environment,
        synthetic_only=synthetic_only,
    )
    return envelope, [str(row["projection_id"]) for row in pending]


def project_once(
    root: Any,
    transport: ProjectionTransport,
    *,
    apply: bool,
    confirmation_nonce: str | None = None,
) -> dict[str, Any]:
    paths: LabPaths = ensure_staging_carrier(root)
    config = load_staging_config(paths)
    repository = open_staging_repository(paths)
    try:
        bundle_path = (
            paths.projection_bundles / f"preview-{confirmation_nonce}.json"
            if apply and confirmation_nonce
            else None
        )
        if bundle_path is not None and bundle_path.exists():
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            envelope = bundle["envelope"]
            pending_ids = [str(value) for value in bundle["pendingIds"]]
        else:
            envelope, pending_ids = build_pending_envelope(
                repository, str(config["expectedSourceFingerprint"])
            )
        if envelope is None:
            return {"status": "NO_WORK", "safeResultCode": "PROJECTION_QUEUE_EMPTY"}
        preview = transport.preview(envelope)
        result = {
            **asdict(preview),
            "pendingWorkCount": len(pending_ids),
            "dryRun": not apply,
            "cloudMutation": False,
            "transport": getattr(transport, "transport_name", "UNKNOWN"),
        }
        if not apply:
            stored_bundle = paths.projection_bundles / (
                f"preview-{preview.confirmation_nonce}.json"
            )
            stored_bundle.write_text(
                json.dumps(
                    {"envelope": envelope, "pendingIds": pending_ids},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            result["bundle"] = str(stored_bundle)
            return result
        if confirmation_nonce != preview.confirmation_nonce:
            raise RuntimeError("CONFIRMATION_NONCE_MISMATCH")
        claims = []
        for _ in pending_ids:
            claim = repository.claim_projection(worker_id="phase2b-operator")
            if claim is None:
                raise RuntimeError("PROJECTION_CLAIM_INCOMPLETE")
            claims.append(claim)
        receipt = transport.apply(envelope, confirmation_nonce)
        for claim in claims:
            if not repository.complete_projection(
                str(claim.key), claim.claim_token, str(envelope["checksum"])
            ):
                raise RuntimeError("PROJECTION_COMPLETION_FAILED")
        now = utc_now_iso()
        with repository.transaction() as db:
            db.execute(
                """
                UPDATE sync_state SET last_local_projection_checksum = ?, last_success_at = ?,
                    receipt_ref = ?, updated_at = ?
                WHERE stream_name = 'local-sheet-projection'
                """,
                (envelope["checksum"], now, f"projection-v{envelope['sourceVersion']}", now),
            )
        return {
            **asdict(receipt),
            "completedWorkCount": len(claims),
            "dryRun": False,
            "cloudMutation": bool(getattr(transport, "is_cloud", True)),
            "transport": getattr(transport, "transport_name", "UNKNOWN"),
        }
    finally:
        repository.close()


def projection_status(root: Any) -> dict[str, Any]:
    paths = ensure_staging_carrier(root)
    repository = open_staging_repository(paths)
    try:
        rows = repository._connection.execute(  # noqa: SLF001
            "SELECT status, COUNT(*) AS count FROM projection_outbox GROUP BY status"
        ).fetchall()
        return {
            "environment": "STAGING",
            "syntheticOnly": True,
            "counts": {str(row["status"]): int(row["count"]) for row in rows},
        }
    finally:
        repository.close()
