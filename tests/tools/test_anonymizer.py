from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from bots.common.contracts import ContractRegistry
from bots.common.errors import AuthorizationError, ConflictError
from tools.anonymizer.pipeline import AnonymizerPipeline
from tools.discord_export.adapters import FixtureExportAdapter
from tools.discord_export.pipeline import DiscordExportPipeline

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
NOW = "2026-07-19T17:00:00+08:00"


def load(path: Path) -> dict[str, Any]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rebind_thread_checksum(raw: Path) -> None:
    metadata = load(raw / "metadata.json")
    digest = hashlib.sha256((raw / "thread.json").read_bytes()).hexdigest()
    for item in metadata["files"]:
        if item["path"] == "thread.json":
            item["sha256"] = digest
    write(raw / "metadata.json", metadata)


def raw_export(tmp_path: Path) -> Path:
    contracts = ContractRegistry.project_default()
    exporter = DiscordExportPipeline(
        FixtureExportAdapter(FIXTURES, contracts), contracts, now=lambda: NOW
    )
    return exporter.export(
        "C01-7K4M2Q-0702-1000",
        tmp_path / "raw",
        initiated_by_user_id="usr_staff_example",
    ).output_directory


def anonymizer() -> AnonymizerPipeline:
    return AnonymizerPipeline(FIXTURES, ContractRegistry.project_default(), now=NOW)


def test_excluded_content_is_placeholder_and_reply_chronology_survives(tmp_path: Path) -> None:
    raw = raw_export(tmp_path)
    raw_thread = load(raw / "thread.json")
    excluded_text = raw_thread["messages"][2]["body"]
    result = anonymizer().sanitize(raw, tmp_path / "sanitized")

    assert result.included_messages == 3
    assert result.placeholder_messages == 1
    document = load(result.output_directory / "sanitized-thread.json")
    ContractRegistry.project_default().validate("sanitized-thread.schema.json", document)
    messages = document["messages"]
    assert messages[2]["contentStatus"] == "PLACEHOLDER"
    assert messages[2]["body"] == "[Content excluded by consent.]"
    assert messages[2]["attachments"] == []
    assert messages[3]["parentRef"] == "m003"
    all_output = "\n".join(
        path.read_text(encoding="utf-8") for path in result.output_directory.iterdir()
    )
    assert excluded_text not in all_output
    assert "msg_000421" not in all_output
    assert "423456789012345" not in all_output
    assert "usr_amber" not in all_output
    assert "Taylor Teaching Example" not in all_output
    assert "01007" not in all_output


def test_known_and_pattern_pii_are_replaced_without_logging_removed_values(
    tmp_path: Path,
) -> None:
    raw = raw_export(tmp_path)
    thread = load(raw / "thread.json")
    sensitive = (
        "Taylor Teaching Example amber.student@example.com B12345678 "
        "https://example.com/private <@423456789012345678>"
    )
    thread["messages"][1]["body"] = sensitive
    write(raw / "thread.json", thread)
    rebind_thread_checksum(raw)
    result = anonymizer().sanitize(raw, tmp_path / "sanitized")
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in result.output_directory.iterdir()
    )
    for value in sensitive.split():
        assert value not in combined
    assert "[NAME]" in combined
    assert "[EMAIL]" in combined
    assert "[STUDENT_ID]" in combined
    assert "[URL]" in combined
    assert "[DISCORD_USER]" in combined
    log = load(result.output_directory / "redaction-log.json")
    assert {entry["category"] for entry in log["entries"]} >= {
        "KNOWN_NAME",
        "KNOWN_EMAIL",
        "URL",
        "DISCORD_MENTION",
        "STUDENT_ID",
    }


def test_private_or_case_excluded_manifest_is_rejected_before_content_read(
    tmp_path: Path,
) -> None:
    raw = raw_export(tmp_path)
    metadata = load(raw / "metadata.json")
    metadata["caseType"] = "PRIVATE_SUPPORT"
    metadata["analysisPermission"] = "EXCLUDED"
    write(raw / "metadata.json", metadata)
    (raw / "thread.json").write_text("private sensitive content", encoding="utf-8")
    output = tmp_path / "sanitized"
    with pytest.raises(AuthorizationError):
        anonymizer().sanitize(raw, output)
    assert not output.exists()


def test_missing_current_consent_fails_closed_to_placeholder(tmp_path: Path) -> None:
    raw = raw_export(tmp_path)
    thread = load(raw / "thread.json")
    original = thread["messages"][0]["body"]
    thread["messages"][0]["authorUserId"] = "usr_unknown"
    write(raw / "thread.json", thread)
    rebind_thread_checksum(raw)
    result = anonymizer().sanitize(raw, tmp_path / "sanitized")
    document = load(result.output_directory / "sanitized-thread.json")
    assert document["messages"][0]["contentStatus"] == "PLACEHOLDER"
    assert original not in json.dumps(document)


def test_raw_and_sanitized_directories_must_not_overlap(tmp_path: Path) -> None:
    raw = raw_export(tmp_path)
    with pytest.raises(ValueError, match="separate"):
        anonymizer().sanitize(raw, raw)


def test_tampered_raw_thread_is_rejected_by_manifest_checksum(tmp_path: Path) -> None:
    raw = raw_export(tmp_path)
    thread = load(raw / "thread.json")
    thread["messages"][0]["body"] = "Schema-valid but unbound tampered content."
    write(raw / "thread.json", thread)
    with pytest.raises(ConflictError, match="checksum"):
        anonymizer().sanitize(raw, tmp_path / "sanitized")
