"""Deterministic, resumable local file export with metadata-last atomic replaces."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from bots.common.contracts import ContractRegistry
from bots.common.errors import ConflictError, ContractValidationError, ProviderUnavailableError
from tools.discord_export.adapters import DISCORD_ID_PATTERN
from tools.discord_export.models import ExportCase, ExportResult, ThreadExportAdapter

OUTPUT_FILENAMES = ("thread.json", "thread.md", "attachments.json", "metadata.json")
CONTENT_MEDIA_TYPES = {
    "thread.json": "application/json",
    "thread.md": "text/markdown",
    "attachments.json": "application/json",
}


class DiscordExportPipeline:
    def __init__(
        self,
        adapter: ThreadExportAdapter,
        contracts: ContractRegistry,
        *,
        now: Callable[[], str],
        max_pages: int = 100,
    ) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        self._adapter = adapter
        self._contracts = contracts
        self._now = now
        self._max_pages = max_pages

    def export(
        self,
        case_number_or_thread_id: str,
        output_root: Path,
        *,
        initiated_by_user_id: str,
        after_message_id: str | None = None,
        page_size: int = 100,
    ) -> ExportResult:
        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        if after_message_id is not None and not DISCORD_ID_PATTERN.fullmatch(after_message_id):
            raise ValueError("after_message_id must be a 17–20 digit Discord message ID")
        case = self._adapter.resolve_case(case_number_or_thread_id)
        if case.record["analysisPermission"] not in {"INCLUDED", "EXCLUDED"}:
            raise ContractValidationError("Case analysis permission is unresolved.")
        target = output_root.resolve() / case.case_number
        existing_thread, existing_metadata = self._load_existing(target, case)
        if existing_metadata is not None:
            if existing_metadata["initiatedByUserId"] != initiated_by_user_id:
                raise ConflictError("Existing export belongs to a different initiating user.")
            existing_cursor = existing_metadata["cursor"]
            if after_message_id is not None and existing_cursor != after_message_id:
                raise ConflictError("Incremental checkpoint does not match existing metadata.")

        incoming, page_count = self._fetch(case, after_message_id, page_size)
        projected = [self._project_message(item) for item in incoming]
        self._require_unique_messages(projected)
        previous_messages = existing_thread["messages"] if existing_thread is not None else []
        if not isinstance(previous_messages, list):
            raise ContractValidationError("Existing thread messages are invalid.")

        if after_message_id is None:
            messages = projected
        else:
            messages = self._merge_incremental(previous_messages, projected)
        messages = sorted(messages, key=_message_order_key)
        self._validate_reply_graph(messages)

        previous_ids = {str(item["messageId"]) for item in previous_messages}
        added_messages = sum(str(item["messageId"]) not in previous_ids for item in projected)
        checkpoint = self._checkpoint(messages, after_message_id)
        export_id = _export_id(case.case_id)
        thread_document = {
            "schemaVersion": "1.0",
            "exportId": export_id,
            "caseId": case.case_id,
            "caseNumber": case.case_number,
            "threadId": case.thread_id,
            "caseSource": case.record["source"],
            "caseAnalysisPermission": case.record["analysisPermission"],
            "checkpoint": checkpoint,
            "messages": messages,
        }
        attachments_document = self._attachment_index(case, export_id, checkpoint, messages)
        self._contracts.validate("thread-export.schema.json", thread_document)
        self._contracts.validate("attachment-index.schema.json", attachments_document)

        if existing_thread == thread_document and existing_metadata is not None:
            self._verify_existing_integrity(target, existing_metadata)
            return ExportResult(
                target,
                len(messages),
                0,
                page_count,
                checkpoint,
                unchanged=True,
            )

        timestamp = self._validated_timestamp(self._now())
        created_at = (
            str(existing_metadata["createdAt"]) if existing_metadata is not None else timestamp
        )
        thread_bytes = _json_bytes(thread_document)
        markdown_bytes = self._render_markdown(thread_document).encode("utf-8")
        attachment_bytes = _json_bytes(attachments_document)
        payloads = {
            "thread.json": thread_bytes,
            "thread.md": markdown_bytes,
            "attachments.json": attachment_bytes,
        }
        files = [
            {
                "path": filename,
                "mediaType": CONTENT_MEDIA_TYPES[filename],
                "sha256": _sha256(content),
            }
            for filename, content in payloads.items()
        ]
        metadata = {
            "schemaVersion": "1.0",
            "exportId": export_id,
            "caseId": case.case_id,
            "caseType": "GENERAL",
            "initiatedByUserId": initiated_by_user_id,
            "mode": "FOLLOW" if after_message_id is not None else "DUMP",
            "analysisPermission": case.record["analysisPermission"],
            "messageCount": len(messages),
            "cursor": checkpoint,
            "files": files,
            "createdAt": created_at,
            "completedAt": timestamp,
        }
        self._contracts.validate("export-manifest.schema.json", metadata)
        payloads["metadata.json"] = _json_bytes(metadata)
        self._write_atomic_set(target, payloads)
        return ExportResult(
            target,
            len(messages),
            added_messages,
            page_count,
            checkpoint,
            unchanged=False,
        )

    def _fetch(
        self,
        case: ExportCase,
        after_message_id: str | None,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        cursor = after_message_id
        observed_cursors: set[str] = set()
        observed_messages: set[str] = set()
        messages: list[dict[str, Any]] = []
        for page_count in range(1, self._max_pages + 1):
            page = self._adapter.fetch_page(case, after_message_id=cursor, limit=page_size)
            for message in page.messages:
                message_id = str(message["messageId"])
                if message["caseId"] != case.case_id or message_id in observed_messages:
                    raise ProviderUnavailableError(
                        "Export adapter returned a wrong-case or duplicate message."
                    )
                observed_messages.add(message_id)
                messages.append(message)
            if page.next_cursor is None:
                return messages, page_count
            if (
                not page.messages
                or page.next_cursor != page.messages[-1]["discordMessageId"]
                or page.next_cursor == cursor
                or page.next_cursor in observed_cursors
            ):
                raise ProviderUnavailableError("Export adapter returned an invalid page cursor.")
            observed_cursors.add(page.next_cursor)
            cursor = page.next_cursor
        raise ProviderUnavailableError("Export exceeded the bounded page limit.")

    def _project_message(self, message: dict[str, Any]) -> dict[str, Any]:
        user_id = str(message["authorUserId"])
        user = self._adapter.user_record(user_id)
        display_mode = str(message["authorDisplayMode"])
        role = str(message["authorRole"])
        raw_permission = str(message["analysisPermission"])
        if raw_permission == "INHERIT":
            permission = str(user["analysisPermissionDefault"])
            permission_source = "ACCOUNT_DEFAULT"
        else:
            permission = raw_permission
            permission_source = "MESSAGE_OVERRIDE"
        return {
            "messageId": message["messageId"],
            "authorUserId": user_id,
            "authorLabel": self._author_label(user_id, role, display_mode),
            "authorRole": role,
            "authorDisplayMode": display_mode,
            "body": message["body"],
            "source": message["source"],
            "analysisPermission": permission,
            "analysisPermissionSource": permission_source,
            "parentMessageId": message["parentMessageId"],
            "discordMessageId": message["discordMessageId"],
            "editedAt": message["editedAt"],
            "attachments": message["attachments"],
            "createdAt": message["createdAt"],
        }

    def _author_label(self, user_id: str, role: str, display_mode: str) -> str:
        if display_mode == "COURSE_ALIAS":
            alias = self._adapter.course_alias(user_id)
            if alias is None:
                raise ContractValidationError("Course-alias author has no active membership alias.")
            return alias
        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8]
        if display_mode == "ANONYMOUS":
            return f"anonymous-{digest}"
        if role == "BOT":
            return f"course-assistant-{digest}"
        return f"{role.lower()}-{digest}"

    @staticmethod
    def _merge_incremental(
        previous: list[dict[str, Any]], incoming: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        merged = {str(item["messageId"]): item for item in previous}
        for item in incoming:
            message_id = str(item["messageId"])
            if message_id in merged:
                raise ConflictError("Incremental adapter returned an already exported message.")
            merged[message_id] = item
        return list(merged.values())

    @staticmethod
    def _require_unique_messages(messages: list[dict[str, Any]]) -> None:
        identifiers = [str(item["messageId"]) for item in messages]
        discord_ids = [str(item["discordMessageId"]) for item in messages]
        if len(identifiers) != len(set(identifiers)) or len(discord_ids) != len(set(discord_ids)):
            raise ContractValidationError("Export contains duplicate message IDs.")

    @staticmethod
    def _validate_reply_graph(messages: list[dict[str, Any]]) -> None:
        positions = {str(item["messageId"]): index for index, item in enumerate(messages)}
        for index, item in enumerate(messages):
            parent = item["parentMessageId"]
            if parent is not None and parent in positions and positions[str(parent)] >= index:
                raise ContractValidationError("Reply parent must precede its child message.")

    @staticmethod
    def _checkpoint(messages: list[dict[str, Any]], fallback: str | None) -> str | None:
        if not messages:
            return fallback
        value = messages[-1]["discordMessageId"]
        if not isinstance(value, str):
            raise ContractValidationError("Export checkpoint requires a Discord message ID.")
        return value

    @staticmethod
    def _attachment_index(
        case: ExportCase,
        export_id: str,
        checkpoint: str | None,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        attachments: list[dict[str, Any]] = []
        for message in messages:
            raw_attachments = message["attachments"]
            if not isinstance(raw_attachments, list):
                raise ContractValidationError("Message attachments must be a list.")
            for attachment in raw_attachments:
                if not isinstance(attachment, dict):
                    raise ContractValidationError("Attachment metadata must be an object.")
                attachments.append({"messageId": message["messageId"], **attachment})
        return {
            "schemaVersion": "1.0",
            "exportId": export_id,
            "caseId": case.case_id,
            "caseNumber": case.case_number,
            "checkpoint": checkpoint,
            "attachments": attachments,
        }

    def _load_existing(
        self, target: Path, case: ExportCase
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        existing = [
            target / filename for filename in OUTPUT_FILENAMES if (target / filename).exists()
        ]
        if not existing:
            return None, None
        if len(existing) != len(OUTPUT_FILENAMES):
            raise ConflictError("Export directory contains a partial output set.")
        thread = _load_json_object(target / "thread.json")
        metadata = _load_json_object(target / "metadata.json")
        attachments = _load_json_object(target / "attachments.json")
        self._contracts.validate("thread-export.schema.json", thread)
        self._contracts.validate("export-manifest.schema.json", metadata)
        self._contracts.validate("attachment-index.schema.json", attachments)
        expected = (_export_id(case.case_id), case.case_id, case.case_number, case.thread_id)
        actual = (
            thread["exportId"],
            thread["caseId"],
            thread["caseNumber"],
            thread["threadId"],
        )
        if actual != expected or metadata["exportId"] != expected[0]:
            raise ConflictError("Existing output does not belong to the selected case/thread.")
        return thread, metadata

    @staticmethod
    def _verify_existing_integrity(target: Path, metadata: dict[str, Any]) -> None:
        files = metadata.get("files")
        if not isinstance(files, list) or len(files) != len(CONTENT_MEDIA_TYPES):
            raise ConflictError("Existing export manifest has an unexpected file set.")
        expected = {
            str(item["path"]): str(item["sha256"])
            for item in files
            if isinstance(item, dict) and "path" in item and "sha256" in item
        }
        if set(expected) != set(CONTENT_MEDIA_TYPES):
            raise ConflictError("Existing export manifest file paths are invalid.")
        for filename, digest in expected.items():
            if _sha256((target / filename).read_bytes()) != digest:
                raise ConflictError("Existing export file checksum does not match metadata.")

    @staticmethod
    def _render_markdown(thread: dict[str, Any]) -> str:
        messages = thread["messages"]
        if not isinstance(messages, list):
            raise ContractValidationError("Thread messages must be a list.")
        by_id = {str(item["messageId"]): item for item in messages}
        lines = [
            f"# {thread['caseNumber']} Discord thread export",
            "",
            f"- Thread ID: `{thread['threadId']}`",
            f"- Checkpoint: `{thread['checkpoint'] or 'none'}`",
            f"- Case source: `{thread['caseSource']}`",
            f"- Case analysis permission: `{thread['caseAnalysisPermission']}`",
            "",
        ]
        if not messages:
            lines.extend(["_No messages in this export._", ""])
            return "\n".join(lines)
        for item in messages:
            edited = f"; edited {item['editedAt']}" if item["editedAt"] else ""
            lines.extend(
                [
                    f"## {item['createdAt']} — {item['authorLabel']} ({item['authorRole']})",
                    "",
                    f"- Message: `{item['messageId']}`{edited}",
                    f"- Source: `{item['source']}`",
                    (
                        f"- Analysis: `{item['analysisPermission']}` "
                        f"(`{item['analysisPermissionSource']}`)"
                    ),
                ]
            )
            parent_id = item["parentMessageId"]
            if parent_id is not None:
                parent = by_id.get(str(parent_id))
                if parent is None:
                    context = "parent is outside this partial export"
                else:
                    summary = " ".join(str(parent["body"]).split())[:120]
                    context = f"{parent['authorLabel']}: {summary}"
                lines.append(f"- Reply to: `{parent_id}` — {context}")
            lines.append("")
            for body_line in str(item["body"]).splitlines() or [""]:
                lines.append(f"> {body_line}")
            raw_attachments = item["attachments"]
            if isinstance(raw_attachments, list) and raw_attachments:
                lines.extend(["", "Attachments:"])
                for attachment in raw_attachments:
                    if isinstance(attachment, dict):
                        lines.append(
                            f"- `{attachment['filename']}` ({attachment['mediaType']}, "
                            f"{attachment['sizeBytes']} bytes; ID `{attachment['attachmentId']}`)"
                        )
            lines.extend(["", "---", ""])
        return "\n".join(lines)

    @staticmethod
    def _write_atomic_set(target: Path, payloads: dict[str, bytes]) -> None:
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary: dict[str, Path] = {}
        try:
            for filename in OUTPUT_FILENAMES:
                content = payloads[filename]
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=target, prefix=f".{filename}.", delete=False
                ) as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                    temporary[filename] = Path(handle.name)
                os.chmod(temporary[filename], 0o600)
            for filename in OUTPUT_FILENAMES:
                os.replace(temporary[filename], target / filename)
        finally:
            for path in temporary.values():
                path.unlink(missing_ok=True)

    @staticmethod
    def _validated_timestamp(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ContractValidationError("Export clock returned an invalid timestamp.") from error
        if parsed.tzinfo is None:
            raise ContractValidationError("Export clock timestamp must include a timezone.")
        return value


def _message_order_key(item: dict[str, Any]) -> tuple[datetime, str]:
    parsed = datetime.fromisoformat(str(item["createdAt"]).replace("Z", "+00:00"))
    return parsed, str(item["messageId"])


def _export_id(case_id: str) -> str:
    value = f"export_{case_id}_thread"
    if len(value) > 64:
        digest = hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:16]
        value = f"export_case_{digest}_thread"
    return value


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError("Existing export JSON is unreadable.") from error
    if not isinstance(value, dict):
        raise ContractValidationError("Existing export JSON must be an object.")
    return value
