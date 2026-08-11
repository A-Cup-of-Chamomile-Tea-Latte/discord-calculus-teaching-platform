from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from discord_course_bots.data_lab.contracts import canonical_json, validate_common_envelope


@dataclass(frozen=True, slots=True)
class PreviewReceipt:
    status: str
    source_version: int
    checksum: str
    confirmation_nonce: str
    row_counts: dict[str, int]
    safe_result_code: str


@dataclass(frozen=True, slots=True)
class ApplyReceipt:
    status: str
    source_version: int
    checksum: str
    safe_result_code: str


@dataclass(frozen=True, slots=True)
class RemoteCommandClaim:
    envelope: dict[str, Any]
    claim_token: str
    lease_expires_at: str


class ProjectionTransport(Protocol):
    def preview(self, envelope: dict[str, Any]) -> PreviewReceipt: ...

    def apply(self, envelope: dict[str, Any], confirmation_nonce: str) -> ApplyReceipt: ...


def confirmation_nonce(envelope: dict[str, Any]) -> str:
    return hashlib.sha256(
        (canonical_json(envelope) + "\nPHASE2B_APPLY").encode("utf-8")
    ).hexdigest()[:24]


class FakeGasTransport:
    """Deterministic in-process replacement used because cloud Gate 1 is closed."""

    def __init__(self, expected_fingerprint: str) -> None:
        self.expected_fingerprint = expected_fingerprint
        self.views: dict[str, list[dict[str, Any]]] = {
            "Overview": [],
            "CaseBoard": [],
            "Operations": [],
            "History": [],
        }
        self.source_version = 0
        self.checksum: str | None = None
        self.mutation_count = 0
        self.commands: list[dict[str, Any]] = []

    def preview(self, envelope: dict[str, Any]) -> PreviewReceipt:
        validate_common_envelope(envelope, self.expected_fingerprint)
        version = int(envelope["sourceVersion"])
        checksum = str(envelope["checksum"])
        if version < self.source_version:
            raise RuntimeError("SYNC_STALE_VERSION")
        if version == self.source_version and self.checksum not in (None, checksum):
            raise RuntimeError("SYNC_VERSION_CHECKSUM_CONFLICT")
        code = (
            "SYNC_NOOP"
            if version == self.source_version and self.checksum == checksum
            else "SYNC_PREVIEW_READY"
        )
        return PreviewReceipt(
            "NO_OP" if code == "SYNC_NOOP" else "PREVIEW",
            version,
            checksum,
            confirmation_nonce(envelope),
            {key: int(value) for key, value in envelope["rowCounts"].items()},
            code,
        )

    def apply(self, envelope: dict[str, Any], confirmation: str) -> ApplyReceipt:
        preview = self.preview(envelope)
        if confirmation != preview.confirmation_nonce:
            raise RuntimeError("CONFIRMATION_NONCE_MISMATCH")
        if preview.status == "NO_OP":
            return ApplyReceipt("NO_OP", preview.source_version, preview.checksum, "SYNC_NOOP")
        for scope, rows in envelope["rows"].items():
            if scope == "History":
                existing = {str(row["eventRef"]) for row in self.views[scope]}
                self.views[scope].extend(
                    dict(row) for row in rows if str(row["eventRef"]) not in existing
                )
                continue
            primary_key = {
                "Overview": "metricKey",
                "CaseBoard": "caseNumber",
                "Operations": "operationKey",
            }[scope]
            by_key = {str(row[primary_key]): dict(row) for row in self.views[scope]}
            by_key.update({str(row[primary_key]): dict(row) for row in rows})
            self.views[scope] = list(by_key.values())
        self.source_version = preview.source_version
        self.checksum = preview.checksum
        self.mutation_count += 1
        return ApplyReceipt("APPLIED", preview.source_version, preview.checksum, "SYNC_APPLIED")

    def queue_command(self, envelope: dict[str, Any]) -> None:
        self.commands.append(
            {
                "envelope": dict(envelope),
                "status": "QUEUED",
                "claimToken": None,
                "claimedBy": None,
                "leaseExpiresAt": None,
                "safeResultCode": None,
            }
        )

    def preview_commands(self, limit: int = 1) -> list[dict[str, Any]]:
        if not 1 <= limit <= 50:
            raise ValueError("command batch must be between 1 and 50")
        return [
            dict(row["envelope"])
            for row in self.commands
            if row["status"] in {"QUEUED", "CLAIMED"}
        ][:limit]

    def claim_command(
        self,
        worker_id: str,
        *,
        now: datetime | None = None,
        lease_seconds: int = 300,
    ) -> RemoteCommandClaim | None:
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        for row in self.commands:
            expired = (
                row["status"] == "CLAIMED"
                and row["leaseExpiresAt"] is not None
                and datetime.fromisoformat(str(row["leaseExpiresAt"])) <= moment
            )
            if row["status"] != "QUEUED" and not expired:
                continue
            token = uuid.uuid4().hex
            lease = moment + timedelta(seconds=lease_seconds)
            row.update(
                {
                    "status": "CLAIMED",
                    "claimToken": token,
                    "claimedBy": worker_id,
                    "leaseExpiresAt": lease.isoformat(),
                }
            )
            return RemoteCommandClaim(dict(row["envelope"]), token, lease.isoformat())
        return None

    def ack_command(self, command_id: str, claim_token: str, result_code: str) -> bool:
        for row in self.commands:
            if row["envelope"]["commandId"] != command_id:
                continue
            if row["status"] != "CLAIMED" or row["claimToken"] != claim_token:
                return False
            row.update(
                {
                    "status": "COMPLETED",
                    "claimToken": None,
                    "claimedBy": None,
                    "leaseExpiresAt": None,
                    "safeResultCode": result_code,
                }
            )
            return True
        return False
