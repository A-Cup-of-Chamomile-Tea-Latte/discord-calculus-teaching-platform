"""Deterministic fixture handoff reconciliation and export-manifest projection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from bots.archive_reader.models import ExportHandoff


@dataclass(frozen=True)
class ReconciliationReport:
    request_id: str
    message_count: int
    unique_message_count: int
    cursor_matches_tail: bool
    consistent: bool


def reconcile_handoff(handoff: ExportHandoff) -> ReconciliationReport:
    message_ids = [message.discord_message_id for message in handoff.messages]
    cursor_matches_tail = (
        not message_ids and handoff.last_exported_message_id == handoff.starting_after_message_id
    ) or (bool(message_ids) and handoff.last_exported_message_id == message_ids[-1])
    unique_count = len(set(message_ids))
    return ReconciliationReport(
        request_id=handoff.request_id,
        message_count=len(message_ids),
        unique_message_count=unique_count,
        cursor_matches_tail=cursor_matches_tail,
        consistent=unique_count == len(message_ids) and cursor_matches_tail,
    )


def build_export_manifest(
    handoff: ExportHandoff,
    *,
    initiated_by_user_id: str,
    completed_at: str,
) -> dict[str, Any]:
    payload = json.dumps(
        [message.to_contract() for message in handoff.messages],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    analysis_permission = (
        "EXCLUDED"
        if any(message.analysis_permission.value == "EXCLUDED" for message in handoff.messages)
        else "INCLUDED"
    )
    return {
        "schemaVersion": "1.0",
        "exportId": handoff.request_id.replace(":", "_"),
        "caseId": handoff.case_id,
        "caseType": "GENERAL",
        "initiatedByUserId": initiated_by_user_id,
        "mode": handoff.mode.value,
        "analysisPermission": analysis_permission,
        "messageCount": len(handoff.messages),
        "cursor": handoff.last_exported_message_id,
        "files": [
            {
                "path": f"{handoff.case_id}/messages.json",
                "mediaType": "application/json",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        ],
        "createdAt": handoff.created_at,
        "completedAt": completed_at,
    }
