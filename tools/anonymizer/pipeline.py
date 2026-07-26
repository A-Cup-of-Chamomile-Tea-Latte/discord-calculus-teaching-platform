"""Conservative consent filtering and reversible local PII replacement."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bots.common.contracts import ContractRegistry
from bots.common.errors import AuthorizationError, ConflictError, ContractValidationError

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
DISCORD_MENTION_PATTERN = re.compile(r"<@!?[0-9]{17,20}>")
STUDENT_ID_PATTERN = re.compile(r"\b[A-Za-z][0-9]{7,10}\b")
LONG_NUMBER_PATTERN = re.compile(r"\b[0-9]{7,20}\b")
HANDLE_PATTERN = re.compile(r"(?<!\w)@[A-Za-z0-9_.-]{2,32}")
PLACEHOLDER = "[Content excluded by consent.]"
OUTPUT_FILENAMES = (
    "sanitized-thread.json",
    "sanitized-thread.md",
    "redaction-log.json",
    "consent-summary.json",
    "review-checklist.md",
)


@dataclass(frozen=True)
class AnonymizationResult:
    output_directory: Path
    included_messages: int
    placeholder_messages: int
    redaction_events: int
    review_flags: int


class AnonymizerPipeline:
    def __init__(
        self,
        fixture_root: Path,
        contracts: ContractRegistry,
        *,
        now: str,
    ) -> None:
        self._root = fixture_root.resolve()
        self._contracts = contracts
        self._now = now
        self._consents = self._load_consents()
        users = contracts.load_records("user.schema.json", self._root / "users/users.json")
        emails = contracts.load_records(
            "verified-email.schema.json", self._root / "users/verified-emails.json"
        )
        self._known_names = tuple(
            sorted((str(item["displayLabel"]) for item in users), key=len, reverse=True)
        )
        self._known_emails = tuple(
            sorted((str(item["email"]) for item in emails), key=len, reverse=True)
        )

    def sanitize(self, raw_case_directory: Path, output_root: Path) -> AnonymizationResult:
        raw_directory = raw_case_directory.resolve()
        metadata = _load_object(raw_directory / "metadata.json")
        self._contracts.validate("export-manifest.schema.json", metadata)
        if metadata["caseType"] != "GENERAL" or metadata["analysisPermission"] != "INCLUDED":
            raise AuthorizationError("Private or analysis-excluded exports cannot be sanitized.")
        source_thread_sha256 = self._verify_manifest_files(raw_directory, metadata)
        thread = _load_object(raw_directory / "thread.json")
        self._contracts.validate("thread-export.schema.json", thread)
        if thread["caseId"] != metadata["caseId"] or thread["exportId"] != metadata["exportId"]:
            raise ConflictError("Raw thread and metadata identify different exports.")
        case_number = str(thread["caseNumber"])
        target = output_root.resolve() / case_number
        if _overlaps(raw_directory, target):
            raise ValueError("Raw and sanitized directories must be separate.")

        raw_messages = thread["messages"]
        if not isinstance(raw_messages, list):
            raise ContractValidationError("Raw thread messages must be a list.")
        message_refs = {
            str(item["messageId"]): f"m{index:03d}"
            for index, item in enumerate(raw_messages, start=1)
        }
        pseudonyms = self._pseudonyms(raw_messages)
        sanitized: list[dict[str, Any]] = []
        redactions: list[dict[str, Any]] = []
        review_flags: list[dict[str, str]] = []
        consent_counts = {"INCLUDED": 0, "PLACEHOLDER": 0}
        for index, item in enumerate(raw_messages, start=1):
            message_ref = f"m{index:03d}"
            user_id = str(item["authorUserId"])
            allowed, consent_source = self._allowed(user_id, str(item["messageId"]), item)
            parent_id = item["parentMessageId"]
            parent_ref = message_refs.get(str(parent_id)) if parent_id is not None else None
            if allowed:
                body, events = self._redact_text(str(item["body"]), message_ref)
                attachments = self._sanitize_attachments(item["attachments"], message_ref)
                redactions.extend(events)
                status = "INCLUDED"
                review_flags.extend(self._residual_flags(body, message_ref))
            else:
                body = PLACEHOLDER
                attachments = []
                status = "PLACEHOLDER"
                redactions.append(
                    {
                        "messageRef": message_ref,
                        "category": "CONSENT_EXCLUSION",
                        "action": "REPLACED_WITH_STRUCTURAL_PLACEHOLDER",
                        "count": 1,
                    }
                )
            consent_counts[status] += 1
            sanitized.append(
                {
                    "messageRef": message_ref,
                    "parentRef": parent_ref,
                    "createdAt": item["createdAt"],
                    "editedAt": item["editedAt"],
                    "authorPseudonym": pseudonyms[user_id],
                    "authorRole": item["authorRole"],
                    "contentStatus": status,
                    "body": body,
                    "source": item["source"],
                    "attachments": attachments,
                }
            )
            redactions.append(
                {
                    "messageRef": message_ref,
                    "category": "IDENTIFIER_REPLACEMENT",
                    "action": f"REMOVED_RAW_IDS_AND_USED_{consent_source}",
                    "count": 1,
                }
            )

        document = {
            "schemaVersion": "1.0",
            "sourceExportId": metadata["exportId"],
            "sourceThreadSha256": source_thread_sha256,
            "caseNumber": case_number,
            "generatedAt": self._now,
            "messages": sanitized,
        }
        self._contracts.validate("sanitized-thread.schema.json", document)
        redaction_log = {
            "schemaVersion": "1.0",
            "caseNumber": case_number,
            "generatedAt": self._now,
            "entries": redactions,
        }
        consent_summary = {
            "schemaVersion": "1.0",
            "caseNumber": case_number,
            "generatedAt": self._now,
            "totalMessages": len(sanitized),
            "includedMessages": consent_counts["INCLUDED"],
            "placeholderMessages": consent_counts["PLACEHOLDER"],
            "policy": "RAW_AND_CURRENT_CONSENT_MUST_BOTH_INCLUDE",
        }
        payloads = {
            "sanitized-thread.json": _json_bytes(document),
            "sanitized-thread.md": self._markdown(document).encode("utf-8"),
            "redaction-log.json": _json_bytes(redaction_log),
            "consent-summary.json": _json_bytes(consent_summary),
            "review-checklist.md": self._review(case_number, review_flags).encode("utf-8"),
        }
        self._write_atomic(target, payloads)
        return AnonymizationResult(
            target,
            consent_counts["INCLUDED"],
            consent_counts["PLACEHOLDER"],
            len(redactions),
            len(review_flags),
        )

    @staticmethod
    def _verify_manifest_files(raw_directory: Path, metadata: dict[str, Any]) -> str:
        files = metadata.get("files")
        if not isinstance(files, list):
            raise ContractValidationError("Raw export manifest files must be a list.")
        thread_digest: str | None = None
        for item in files:
            if not isinstance(item, dict):
                raise ContractValidationError("Raw export manifest file must be an object.")
            relative = Path(str(item["path"]))
            path = (raw_directory / relative).resolve()
            if raw_directory not in path.parents:
                raise ContractValidationError("Raw export manifest path escapes its directory.")
            try:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as error:
                raise ContractValidationError("Raw export manifest file is unreadable.") from error
            expected = str(item["sha256"])
            if actual != expected:
                raise ConflictError("Raw export file checksum does not match its manifest.")
            if relative.as_posix() == "thread.json":
                thread_digest = actual
        if thread_digest is None:
            raise ContractValidationError("Raw export manifest is missing thread.json.")
        return thread_digest

    def _load_consents(self) -> dict[str, dict[str, Any]]:
        records = self._contracts.load_records(
            "consent.schema.json", self._root / "users/consents.json"
        )
        return {str(item["userId"]): item for item in records}

    def _allowed(
        self, user_id: str, message_id: str, raw_message: dict[str, Any]
    ) -> tuple[bool, str]:
        if raw_message["analysisPermission"] == "EXCLUDED":
            return False, "RAW_MESSAGE_EXCLUSION"
        consent = self._consents.get(user_id)
        if consent is None:
            return False, "MISSING_CONSENT"
        overrides = consent["perPostOverrides"]
        if isinstance(overrides, list):
            for override in overrides:
                if isinstance(override, dict) and override.get("messageId") == message_id:
                    return override.get("permission") == "INCLUDED", "CURRENT_POST_OVERRIDE"
        return consent["accountDefault"] == "INCLUDED", "CURRENT_ACCOUNT_DEFAULT"

    @staticmethod
    def _pseudonyms(messages: list[dict[str, Any]]) -> dict[str, str]:
        counters: dict[str, int] = {}
        result: dict[str, str] = {}
        for item in messages:
            user_id = str(item["authorUserId"])
            if user_id in result:
                continue
            role = str(item["authorRole"]).lower()
            counters[role] = counters.get(role, 0) + 1
            result[user_id] = f"{role}-{counters[role]:02d}"
        return result

    def _redact_text(self, body: str, message_ref: str) -> tuple[str, list[dict[str, Any]]]:
        events: list[dict[str, Any]] = []
        value = body
        replacements: list[tuple[str, re.Pattern[str], str]] = [
            ("EMAIL", EMAIL_PATTERN, "[EMAIL]"),
            ("URL", URL_PATTERN, "[URL]"),
            ("DISCORD_MENTION", DISCORD_MENTION_PATTERN, "[DISCORD_USER]"),
            ("STUDENT_ID", STUDENT_ID_PATTERN, "[STUDENT_ID]"),
        ]
        for email in self._known_emails:
            value, count = re.subn(re.escape(email), "[EMAIL]", value, flags=re.IGNORECASE)
            if count:
                events.append(_event(message_ref, "KNOWN_EMAIL", count))
        for name in self._known_names:
            value, count = re.subn(re.escape(name), "[NAME]", value, flags=re.IGNORECASE)
            if count:
                events.append(_event(message_ref, "KNOWN_NAME", count))
        for category, pattern, replacement in replacements:
            value, count = pattern.subn(replacement, value)
            if count:
                events.append(_event(message_ref, category, count))
        return value, events

    @staticmethod
    def _sanitize_attachments(value: object, message_ref: str) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise ContractValidationError("Raw attachments must be a list.")
        result: list[dict[str, Any]] = []
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                raise ContractValidationError("Raw attachment must be an object.")
            filename = str(item["filename"])
            suffix = Path(filename).suffix.lower()
            extension = suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ""
            sanitized = {
                "attachmentLabel": f"attachment-{index:02d}{extension}",
                "mediaType": item["mediaType"],
                "sizeBytes": item["sizeBytes"],
            }
            if "sha256" in item:
                sanitized["sha256"] = item["sha256"]
            result.append(sanitized)
        del message_ref
        return result

    @staticmethod
    def _residual_flags(body: str, message_ref: str) -> list[dict[str, str]]:
        flags: list[dict[str, str]] = []
        if LONG_NUMBER_PATTERN.search(body):
            flags.append({"messageRef": message_ref, "category": "LONG_NUMBER"})
        if HANDLE_PATTERN.search(body):
            flags.append({"messageRef": message_ref, "category": "HANDLE_LIKE_TEXT"})
        return flags

    @staticmethod
    def _markdown(document: dict[str, Any]) -> str:
        lines = [f"# {document['caseNumber']} sanitized analysis thread", ""]
        messages = document["messages"]
        if isinstance(messages, list):
            by_ref = {str(item["messageRef"]): item for item in messages}
            for item in messages:
                lines.extend(
                    [
                        (
                            f"## {item['messageRef']} — {item['authorPseudonym']} "
                            f"({item['authorRole']})"
                        ),
                        "",
                        f"- Time: {item['createdAt']}",
                        f"- Content: `{item['contentStatus']}`",
                    ]
                )
                parent_ref = item["parentRef"]
                if parent_ref is not None:
                    parent = by_ref.get(str(parent_ref))
                    context = parent["authorPseudonym"] if parent else "unavailable parent"
                    lines.append(f"- Reply to: `{parent_ref}` — {context}")
                lines.extend(["", f"> {item['body']}", "", "---", ""])
        return "\n".join(lines)

    @staticmethod
    def _review(case_number: str, flags: list[dict[str, str]]) -> str:
        lines = [
            f"# {case_number} human privacy review checklist",
            "",
            (
                "Automated redaction is conservative but imperfect. "
                "A manager must review before analysis."
            ),
            "",
            "- [ ] Confirm every PLACEHOLDER contains no original content or attachment metadata.",
            (
                "- [ ] Check remaining prose for names, handles, locations, "
                "student numbers, and links."
            ),
            "- [ ] Check mathematical screenshots/files separately before including them.",
            "- [ ] Confirm reply chronology remains understandable after exclusions.",
            "- [ ] Confirm this package is not a Private Support case.",
            "",
            "## Automated residual flags",
            "",
        ]
        if not flags:
            lines.append("No pattern-based residual flags. Human review is still required.")
        else:
            for flag in flags:
                lines.append(f"- `{flag['messageRef']}`: {flag['category']}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _write_atomic(target: Path, payloads: dict[str, bytes]) -> None:
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary: dict[str, Path] = {}
        try:
            for filename in OUTPUT_FILENAMES:
                with tempfile.NamedTemporaryFile("wb", dir=target, delete=False) as handle:
                    handle.write(payloads[filename])
                    handle.flush()
                    os.fsync(handle.fileno())
                    temporary[filename] = Path(handle.name)
                os.chmod(temporary[filename], 0o600)
            for filename in OUTPUT_FILENAMES:
                os.replace(temporary[filename], target / filename)
        finally:
            for path in temporary.values():
                path.unlink(missing_ok=True)


def _event(message_ref: str, category: str, count: int) -> dict[str, Any]:
    return {
        "messageRef": message_ref,
        "category": category,
        "action": "REPLACED_WITH_CATEGORY_MARKER",
        "count": count,
    }


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError("Anonymizer input JSON is unreadable.") from error
    if not isinstance(value, dict):
        raise ContractValidationError("Anonymizer input JSON must be an object.")
    return value


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _overlaps(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents
