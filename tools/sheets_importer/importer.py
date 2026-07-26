from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bots.common.contracts import ContractRegistry
from bots.common.errors import ContractValidationError, ProviderUnavailableError
from tools.sheets_importer.models import (
    BatchDestination,
    DestinationMap,
    ImportFailure,
    ImportReport,
    ImportRow,
)


class BatchImporter:
    def __init__(
        self,
        destination: BatchDestination,
        contracts: ContractRegistry,
        *,
        destination_map: DestinationMap | None = None,
        batch_size: int = 50,
        max_retries: int = 2,
    ) -> None:
        if batch_size < 1 or batch_size > 500:
            raise ValueError("batch_size must be between 1 and 500")
        if max_retries < 0 or max_retries > 5:
            raise ValueError("max_retries must be between 0 and 5")
        self._destination = destination
        self._contracts = contracts
        self._map = destination_map or DestinationMap()
        self._batch_size = batch_size
        self._max_retries = max_retries

    def import_package(
        self,
        raw_metadata_path: Path,
        sanitized_thread_path: Path,
        *,
        summaries_path: Path | None = None,
    ) -> ImportReport:
        metadata = _load_object(raw_metadata_path)
        sanitized = _load_object(sanitized_thread_path)
        self._contracts.validate("export-manifest.schema.json", metadata)
        self._contracts.validate("sanitized-thread.schema.json", sanitized)
        if metadata["caseType"] != "GENERAL" or metadata["analysisPermission"] != "INCLUDED":
            raise ContractValidationError("Only included GENERAL exports may be batch imported.")
        thread_digest = _manifest_thread_digest(metadata)
        if (
            sanitized["sourceExportId"] != metadata["exportId"]
            or sanitized["sourceThreadSha256"] != thread_digest
        ):
            raise ContractValidationError(
                "Sanitized package is not bound to the selected raw export manifest."
            )
        rows = self._rows(metadata, sanitized, summaries_path)
        return self._execute(rows)

    def _rows(
        self,
        metadata: dict[str, Any],
        sanitized: dict[str, Any],
        summaries_path: Path | None,
    ) -> tuple[ImportRow, ...]:
        export_id = str(metadata["exportId"])
        rows: list[ImportRow] = [
            ImportRow(
                self._map.exports,
                f"export:{export_id}",
                {
                    "schemaVersion": metadata["schemaVersion"],
                    "exportId": export_id,
                    "caseId": metadata["caseId"],
                    "caseType": metadata["caseType"],
                    "initiatedByUserId": metadata["initiatedByUserId"],
                    "mode": metadata["mode"],
                    "analysisPermission": metadata["analysisPermission"],
                    "messageCount": metadata["messageCount"],
                    "cursor": metadata["cursor"],
                    "filesJson": json.dumps(metadata["files"], separators=(",", ":")),
                    "createdAt": metadata["createdAt"],
                    "completedAt": metadata["completedAt"],
                },
            )
        ]
        messages = sanitized["messages"]
        if not isinstance(messages, list):
            raise ContractValidationError("Sanitized messages must be a list.")
        for item in messages:
            if not isinstance(item, dict):
                raise ContractValidationError("Sanitized message must be an object.")
            message_ref = str(item["messageRef"])
            rows.append(
                ImportRow(
                    self._map.messages,
                    f"message:{export_id}:{message_ref}",
                    {
                        "schemaVersion": "1.0",
                        "exportId": export_id,
                        "caseNumber": sanitized["caseNumber"],
                        "messageRef": message_ref,
                        "parentRef": item["parentRef"],
                        "authorPseudonym": item["authorPseudonym"],
                        "authorRole": item["authorRole"],
                        "contentStatus": item["contentStatus"],
                        "body": item["body"],
                        "source": item["source"],
                        "attachmentCount": len(item["attachments"]),
                        "createdAt": item["createdAt"],
                        "editedAt": item["editedAt"],
                    },
                )
            )
        if summaries_path is not None:
            rows.extend(self._summary_rows(export_id, sanitized, summaries_path))
        return tuple(rows)

    def _summary_rows(
        self, export_id: str, sanitized: dict[str, Any], path: Path
    ) -> list[ImportRow]:
        value = _load_array(path)
        rows: list[ImportRow] = []
        for item in value:
            required = {"summaryId", "summaryType", "body", "createdAt"}
            if set(item) != required or not all(isinstance(item[key], str) for key in required):
                raise ContractValidationError("Summary fixture has an invalid shape.")
            summary_id = str(item["summaryId"])
            if not summary_id or len(str(item["body"])) > 8000:
                raise ContractValidationError("Summary fixture values are invalid.")
            rows.append(
                ImportRow(
                    self._map.summaries,
                    f"summary:{export_id}:{summary_id}",
                    {
                        "schemaVersion": "1.0",
                        "exportId": export_id,
                        "caseNumber": sanitized["caseNumber"],
                        **item,
                    },
                )
            )
        return rows

    def _execute(self, rows: tuple[ImportRow, ...]) -> ImportReport:
        succeeded = 0
        skipped = 0
        failures: list[ImportFailure] = []
        retries = 0
        batches = 0
        for sheet, sheet_rows in _group_by_sheet(rows).items():
            for offset in range(0, len(sheet_rows), self._batch_size):
                pending = tuple(sheet_rows[offset : offset + self._batch_size])
                attempts = {row.idempotency_key: 0 for row in pending}
                while pending:
                    batches += 1
                    outcomes = self._destination.write_batch(sheet, pending)
                    if {item.idempotency_key for item in outcomes} != {
                        item.idempotency_key for item in pending
                    }:
                        raise ProviderUnavailableError(
                            "Destination returned an invalid batch outcome."
                        )
                    retry_rows: list[ImportRow] = []
                    by_key = {row.idempotency_key: row for row in pending}
                    for outcome in outcomes:
                        attempts[outcome.idempotency_key] += 1
                        if outcome.status == "SUCCEEDED":
                            succeeded += 1
                        elif outcome.status == "SKIPPED":
                            skipped += 1
                        elif (
                            outcome.retryable
                            and attempts[outcome.idempotency_key] <= self._max_retries
                        ):
                            retries += 1
                            retry_rows.append(by_key[outcome.idempotency_key])
                        else:
                            failures.append(
                                ImportFailure(
                                    outcome.idempotency_key,
                                    sheet,
                                    outcome.reason or "destination rejected row",
                                    attempts[outcome.idempotency_key],
                                )
                            )
                    pending = tuple(retry_rows)
        return ImportReport(len(rows), succeeded, skipped, tuple(failures), batches, retries, rows)


def _group_by_sheet(rows: tuple[ImportRow, ...]) -> dict[str, list[ImportRow]]:
    grouped: dict[str, list[ImportRow]] = {}
    for row in rows:
        grouped.setdefault(row.sheet, []).append(row)
    return grouped


def _load_object(path: Path) -> dict[str, Any]:
    value = _load_json(path)
    if not isinstance(value, dict):
        raise ContractValidationError("Importer JSON input must be an object.")
    return value


def _load_array(path: Path) -> list[dict[str, Any]]:
    value = _load_json(path)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ContractValidationError("Importer summary input must be an array of objects.")
    return value


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError("Importer JSON input is unreadable.") from error


def _manifest_thread_digest(metadata: dict[str, Any]) -> str:
    files = metadata.get("files")
    if not isinstance(files, list):
        raise ContractValidationError("Export manifest files must be a list.")
    matches = [
        str(item["sha256"])
        for item in files
        if isinstance(item, dict) and item.get("path") == "thread.json"
    ]
    if len(matches) != 1:
        raise ContractValidationError("Export manifest must identify one thread.json digest.")
    return matches[0]
