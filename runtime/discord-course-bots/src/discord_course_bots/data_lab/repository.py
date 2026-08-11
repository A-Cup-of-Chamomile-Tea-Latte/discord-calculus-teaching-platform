from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from discord_course_bots.data_lab.contracts import checksum_for
from discord_course_bots.queue_engine import (
    QueueClaim,
    QueueFailure,
    ReliableQueueSpec,
    claim_next,
    complete_claim,
    fail_claim,
)
from discord_course_bots.repository import Repository
from discord_course_bots.repository_time import utc_now_iso

PROJECTION_QUEUE = ReliableQueueSpec(
    table="projection_outbox",
    key_column="projection_id",
    retry_column="next_attempt_at",
    error_column="last_error_code",
    order_column="created_at",
    retry_status="RETRYABLE_FAILURE",
    terminal_failure_status="PERMANENT_FAILURE",
    reset_columns_on_claim=("last_error_code",),
)


class DataLabConflict(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class TransitionResult:
    case_ref: str
    previous_status: str | None
    new_status: str
    source_version: int
    correlation_id: str
    outbox_count: int
    no_op: bool = False


def _synthetic_thread_id(case_ref: str) -> int:
    digest = hashlib.sha256(case_ref.encode("utf-8")).digest()
    return -(int.from_bytes(digest[:7], "big") + 1)


def _event_type(previous: str | None, requested: str) -> str:
    if previous is None:
        return "OPEN"
    if previous == "OPEN" and requested == "CLOSED":
        return "CLOSE"
    if previous == "CLOSED" and requested == "OPEN":
        return "REOPEN"
    raise DataLabConflict("SYNTHETIC_TRANSITION_INVALID")


class DataLabRepository(Repository):
    """Repository extension limited to the ignored Phase 2B staging carrier."""

    def case_by_ref(self, case_ref: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM cases WHERE case_number = ?", (case_ref,)
        ).fetchone()

    def command_by_id(self, command_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM inbound_commands WHERE command_id = ?", (command_id,)
        ).fetchone()

    def command_by_idempotency_key(self, key: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM inbound_commands WHERE idempotency_key = ?", (key,)
        ).fetchone()

    def sync_row(self, stream_name: str) -> sqlite3.Row:
        row = self._connection.execute(
            "SELECT * FROM sync_state WHERE stream_name = ?", (stream_name,)
        ).fetchone()
        if row is None:
            raise RuntimeError("SYNC_STREAM_MISSING")
        return row

    def _next_local_version(self, db: sqlite3.Connection, now: str) -> int:
        row = db.execute(
            "SELECT last_local_projection_version FROM sync_state "
            "WHERE stream_name = 'local-sheet-projection'"
        ).fetchone()
        if row is None:
            raise RuntimeError("SYNC_STREAM_MISSING")
        version = int(row[0]) + 1
        db.execute(
            "UPDATE sync_state SET last_local_projection_version = ?, updated_at = ? "
            "WHERE stream_name = 'local-sheet-projection'",
            (version, now),
        )
        return version

    def _write_transition(
        self,
        db: sqlite3.Connection,
        *,
        fixture: dict[str, Any],
        requested_status: str,
        source_kind: str,
        correlation_id: str,
        now: str,
    ) -> TransitionResult:
        case_ref = str(fixture["caseRef"])
        if not case_ref.startswith("TST-") or fixture.get("analysisEligible") is not False:
            raise DataLabConflict("SYNTHETIC_FIXTURE_INVALID")
        row = db.execute("SELECT * FROM cases WHERE case_number = ?", (case_ref,)).fetchone()
        previous = None if row is None else str(row["status"])
        event_type = _event_type(previous, requested_status)
        case_id = f"synthetic:{case_ref}"
        if row is None:
            snapshot = {
                "synthetic": True,
                "fixtureRef": fixture.get("fixtureRef"),
                "actorRef": fixture["actorRef"],
                "taAction": fixture["taAction"],
                "deadline": fixture["deadline"],
                "analysisEligible": False,
            }
            db.execute(
                """
                INSERT INTO cases(
                    case_id, case_number, thread_id, author_id, module_code, keyword,
                    ai_content_permission, canonical_title, base_title, status,
                    reopen_count, created_at, closed_at, initial_snapshot_json
                ) VALUES (?, ?, ?, -1, ?, ?, 0, ?, ?, 'OPEN', 0, ?, NULL, ?)
                """,
                (
                    case_id,
                    case_ref,
                    _synthetic_thread_id(case_ref),
                    fixture["module"],
                    fixture["keyword"],
                    f"Synthetic {fixture['module']} case",
                    f"Synthetic {fixture['module']} case",
                    now,
                    json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                ),
            )
        else:
            reopen_increment = 1 if event_type == "REOPEN" else 0
            closed_at = now if requested_status == "CLOSED" else None
            db.execute(
                """
                UPDATE cases
                SET status = ?, closed_at = ?, reopen_count = reopen_count + ?
                WHERE case_number = ?
                """,
                (requested_status, closed_at, reopen_increment, case_ref),
            )

        version = self._next_local_version(db, now)
        event_id = f"evt-{uuid.uuid4().hex}"
        db.execute(
            """
            INSERT INTO case_lifecycle_events(
                event_id, case_id, case_ref, event_type, previous_status, new_status,
                source_kind, correlation_id, occurred_at, synthetic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                event_id,
                case_id,
                case_ref,
                event_type,
                previous,
                requested_status,
                source_kind,
                correlation_id,
                now,
            ),
        )
        works = (
            ("PUBLIC_CASE", case_ref, "UPSERT_CURRENT_STATE", "CASEBOARD"),
            ("PUBLIC_CASE", case_ref, "APPEND_HISTORY", "HISTORY"),
            ("OPERATIONS", "global", "UPDATE_OPERATIONS", "OVERVIEW"),
            ("OPERATIONS", "global", "UPDATE_OPERATIONS", "OPERATIONS"),
        )
        for aggregate_type, aggregate_ref, outbox_event, scope in works:
            projection_id = (
                f"prj-{event_id}-history" if scope == "HISTORY" else f"prj-{uuid.uuid4().hex}"
            )
            db.execute(
                """
                INSERT INTO projection_outbox(
                    projection_id, aggregate_type, aggregate_ref, event_type,
                    projection_scope, source_version, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
                """,
                (
                    projection_id,
                    aggregate_type,
                    aggregate_ref,
                    outbox_event,
                    scope,
                    version,
                    now,
                    now,
                ),
            )
        return TransitionResult(
            case_ref, previous, requested_status, version, correlation_id, len(works)
        )

    def apply_fixture(
        self,
        fixture: dict[str, Any],
        *,
        requested_status: str | None = None,
        correlation_id: str | None = None,
    ) -> TransitionResult:
        status = requested_status or str(fixture["lifecycleStatus"])
        correlation = correlation_id or f"run-{uuid.uuid4().hex}"
        now = str(fixture.get("occurredAt") or utc_now_iso())
        with self.immediate_transaction() as db:
            return self._write_transition(
                db,
                fixture=fixture,
                requested_status=status,
                source_kind="LOCAL_FIXTURE",
                correlation_id=correlation,
                now=now,
            )

    def apply_command(self, envelope: dict[str, Any], fixture: dict[str, Any]) -> TransitionResult:
        checksum = checksum_for(envelope)
        existing_id = self.command_by_id(str(envelope["commandId"]))
        existing_key = self.command_by_idempotency_key(str(envelope["idempotencyKey"]))
        existing = existing_id or existing_key
        if existing is not None:
            if (
                str(existing["command_id"]) == envelope["commandId"]
                and str(existing["idempotency_key"]) == envelope["idempotencyKey"]
                and str(existing["payload_ref"]) == envelope["payloadRef"]
                and str(existing["envelope_sha256"]) == checksum
                and str(existing["status"]) == "APPLIED"
            ):
                row = self.case_by_ref(str(existing["target_case_ref"] or fixture["caseRef"]))
                return TransitionResult(
                    str(existing["target_case_ref"] or fixture["caseRef"]),
                    None,
                    "UNKNOWN" if row is None else str(row["status"]),
                    int(existing["source_version"]),
                    str(existing["command_id"]),
                    0,
                    True,
                )
            raise DataLabConflict("COMMAND_IDEMPOTENCY_CONFLICT")

        stream = self.sync_row("cloud-command-inbox")
        source_version = int(envelope["sourceVersion"])
        if source_version <= int(stream["last_remote_source_version"]):
            raise DataLabConflict("SYNC_STALE_VERSION")
        command_type = str(envelope["commandType"])
        target_ref = envelope.get("targetCaseRef") or fixture["caseRef"]
        target_fixture = dict(fixture)
        target_fixture["caseRef"] = target_ref
        requested_status = {
            "CREATE_SYNTHETIC_CASE": "OPEN",
            "CLOSE_SYNTHETIC_CASE": "CLOSED",
            "REOPEN_SYNTHETIC_CASE": "OPEN",
            "REPLAY_LAST_SYNTHETIC_COMMAND": "OPEN",
        }[command_type]
        now = utc_now_iso()
        with self.immediate_transaction() as db:
            db.execute(
                """
                INSERT INTO inbound_commands(
                    command_id, idempotency_key, command_type, payload_ref, target_case_ref,
                    source_version, envelope_sha256, source_fingerprint, status,
                    fetched_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'FETCHED', ?, ?)
                """,
                (
                    envelope["commandId"],
                    envelope["idempotencyKey"],
                    command_type,
                    envelope["payloadRef"],
                    target_ref,
                    source_version,
                    checksum,
                    envelope["sourceFingerprint"],
                    now,
                    now,
                ),
            )
            db.execute(
                "UPDATE inbound_commands SET status = 'VALIDATED', validated_at = ?, "
                "updated_at = ? WHERE command_id = ?",
                (now, now, envelope["commandId"]),
            )
            result = self._write_transition(
                db,
                fixture=target_fixture,
                requested_status=requested_status,
                source_kind="CLOUD_COMMAND",
                correlation_id=str(envelope["commandId"]),
                now=now,
            )
            db.execute(
                "UPDATE inbound_commands SET status = 'APPLIED', applied_at = ?, "
                "result_code = 'APPLIED', updated_at = ? WHERE command_id = ?",
                (now, now, envelope["commandId"]),
            )
            db.execute(
                """
                UPDATE sync_state
                SET last_remote_source_version = ?, last_remote_checksum = ?,
                    last_success_at = ?, receipt_ref = ?, updated_at = ?
                WHERE stream_name = 'cloud-command-inbox'
                """,
                (source_version, checksum, now, envelope["commandId"], now),
            )
            return result

    def claim_projection(
        self, *, worker_id: str, now: datetime | None = None, lease_seconds: int = 300
    ) -> QueueClaim | None:
        with self.immediate_transaction() as db:
            return claim_next(
                db,
                PROJECTION_QUEUE,
                worker_id=worker_id,
                now=now,
                lease_seconds=lease_seconds,
            )

    def complete_projection(
        self, projection_id: str, claim_token: str, payload_sha256: str
    ) -> bool:
        now = utc_now_iso()
        with self.transaction() as db:
            return complete_claim(
                db,
                PROJECTION_QUEUE,
                key=projection_id,
                claim_token=claim_token,
                final_status="COMPLETED",
                values={
                    "payload_sha256": payload_sha256,
                    "completed_at": now,
                    "updated_at": now,
                },
            )

    def fail_projection(
        self,
        projection_id: str,
        claim_token: str,
        error_code: str,
        *,
        retryable: bool,
        now: datetime | None = None,
    ) -> QueueFailure | None:
        with self.immediate_transaction() as db:
            return fail_claim(
                db,
                PROJECTION_QUEUE,
                key=projection_id,
                claim_token=claim_token,
                error_code=error_code,
                retryable=retryable,
                now=now,
            )

    def pending_projection_rows(self, limit: int = 50) -> list[sqlite3.Row]:
        if not 1 <= limit <= 50:
            raise ValueError("projection batch must be between 1 and 50")
        return list(
            self._connection.execute(
                """
                SELECT * FROM projection_outbox
                WHERE status IN ('PENDING', 'RETRYABLE_FAILURE')
                ORDER BY source_version, created_at LIMIT ?
                """,
                (limit,),
            ).fetchall()
        )

    def counts(self) -> dict[str, int]:
        names = ("cases", "case_lifecycle_events", "inbound_commands", "projection_outbox")
        return {
            name: int(self._connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
            for name in names
        }
