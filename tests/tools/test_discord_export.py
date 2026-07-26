from __future__ import annotations

import hashlib
import inspect
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bots.common.contracts import ContractRegistry
from bots.common.errors import (
    AuthorizationError,
    ConflictError,
    ProviderUnavailableError,
    ResourceNotFoundError,
)
from tools.discord_export.adapters import FixtureExportAdapter, LiveDiscordExportAdapter
from tools.discord_export.pipeline import DiscordExportPipeline

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
CASE_NUMBER = "C01-7K4M2Q-0702-1000"
THREAD_ID = "223456789012345678"
MANAGER_ID = "usr_staff_example"
FIRST_NOW = "2026-07-19T16:30:00+08:00"
SECOND_NOW = "2026-07-19T16:31:00+08:00"


def load_object(path: Path) -> dict[str, Any]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def load_array(path: Path) -> list[dict[str, Any]]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, list)
    assert all(isinstance(item, dict) for item in value)
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pipeline(fixture_root: Path = FIXTURES, *, now: str = FIRST_NOW) -> DiscordExportPipeline:
    contracts = ContractRegistry.project_default()
    adapter = FixtureExportAdapter(fixture_root, contracts)
    return DiscordExportPipeline(adapter, contracts, now=lambda: now)


def test_fixture_export_matches_contracts_and_renders_reply_context(tmp_path: Path) -> None:
    result = pipeline().export(
        CASE_NUMBER,
        tmp_path,
        initiated_by_user_id=MANAGER_ID,
        page_size=2,
    )

    assert result.total_messages == 4
    assert result.added_messages == 4
    assert result.page_count == 2
    assert result.checkpoint == "423456789012345681"
    output = tmp_path / CASE_NUMBER
    assert result.output_directory == output
    assert {path.name for path in output.iterdir()} == {
        "thread.json",
        "thread.md",
        "metadata.json",
        "attachments.json",
    }

    contracts = ContractRegistry.project_default()
    thread = load_object(output / "thread.json")
    metadata = load_object(output / "metadata.json")
    attachments = load_object(output / "attachments.json")
    contracts.validate("thread-export.schema.json", thread)
    contracts.validate("export-manifest.schema.json", metadata)
    contracts.validate("attachment-index.schema.json", attachments)

    messages = thread["messages"]
    assert isinstance(messages, list)
    assert [item["messageId"] for item in messages] == [
        "msg_000421_a",
        "msg_000421_b",
        "msg_000421_c",
        "msg_000421_d",
    ]
    assert messages[0]["authorLabel"] == "01007"
    assert str(messages[1]["authorLabel"]).startswith("ta-")
    assert messages[0]["analysisPermission"] == "INCLUDED"
    assert messages[0]["analysisPermissionSource"] == "ACCOUNT_DEFAULT"
    assert messages[2]["analysisPermission"] == "EXCLUDED"
    assert messages[2]["analysisPermissionSource"] == "MESSAGE_OVERRIDE"
    assert messages[2]["editedAt"] == "2026-07-02T10:09:00+08:00"
    assert "Taylor Teaching Example" not in json.dumps(thread)

    attachment_records = attachments["attachments"]
    assert isinstance(attachment_records, list)
    assert attachment_records[0]["messageId"] == "msg_000421_c"
    assert "url" not in json.dumps(attachments).lower()
    markdown = (output / "thread.md").read_text(encoding="utf-8")
    assert "Reply to: `msg_000421_a`" in markdown
    assert "In this fictional example" in markdown
    assert "Attachments:" in markdown

    manifest_files = metadata["files"]
    assert isinstance(manifest_files, list)
    for item in manifest_files:
        path = output / str(item["path"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        assert path.stat().st_mode & 0o777 == 0o600


def test_rerun_is_byte_and_mtime_idempotent(tmp_path: Path) -> None:
    first = pipeline(now=FIRST_NOW).export(
        THREAD_ID,
        tmp_path,
        initiated_by_user_id=MANAGER_ID,
        page_size=3,
    )
    output = first.output_directory
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in output.iterdir()}

    second = pipeline(now=SECOND_NOW).export(
        CASE_NUMBER,
        tmp_path,
        initiated_by_user_id=MANAGER_ID,
        page_size=2,
    )
    after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in output.iterdir()}
    assert first.unchanged is False
    assert second.unchanged is True
    assert second.added_messages == 0
    assert before == after


def test_incremental_export_adds_only_new_message_and_rejects_stale_cursor(
    tmp_path: Path,
) -> None:
    fixture_copy = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixture_copy)
    message_path = fixture_copy / "messages" / "case-000421-thread.json"
    all_messages = load_array(message_path)
    write_json(message_path, all_messages[:3])
    output_root = tmp_path / "exports"

    first = pipeline(fixture_copy).export(
        CASE_NUMBER,
        output_root,
        initiated_by_user_id=MANAGER_ID,
        page_size=2,
    )
    assert first.total_messages == 3
    assert first.checkpoint == "423456789012345680"

    write_json(message_path, all_messages)
    second = pipeline(fixture_copy, now=SECOND_NOW).export(
        CASE_NUMBER,
        output_root,
        initiated_by_user_id=MANAGER_ID,
        after_message_id=first.checkpoint,
        page_size=1,
    )
    assert second.total_messages == 4
    assert second.added_messages == 1
    assert second.checkpoint == "423456789012345681"
    thread = load_object(second.output_directory / "thread.json")
    messages = thread["messages"]
    assert isinstance(messages, list)
    assert len({item["messageId"] for item in messages}) == 4

    third = pipeline(fixture_copy, now=SECOND_NOW).export(
        CASE_NUMBER,
        output_root,
        initiated_by_user_id=MANAGER_ID,
        after_message_id=second.checkpoint,
        page_size=1,
    )
    assert third.unchanged is True
    assert third.added_messages == 0
    with pytest.raises(ConflictError):
        pipeline(fixture_copy).export(
            CASE_NUMBER,
            output_root,
            initiated_by_user_id=MANAGER_ID,
            after_message_id=first.checkpoint,
        )


def test_full_dump_refreshes_an_edited_message_without_duplication(tmp_path: Path) -> None:
    fixture_copy = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixture_copy)
    message_path = fixture_copy / "messages" / "case-000421-thread.json"
    output_root = tmp_path / "exports"
    first = pipeline(fixture_copy).export(CASE_NUMBER, output_root, initiated_by_user_id=MANAGER_ID)

    messages = load_array(message_path)
    messages[1]["body"] = "This fixture answer was edited during a later full dump."
    messages[1]["editedAt"] = "2026-07-19T16:35:00+08:00"
    write_json(message_path, messages)
    second = pipeline(fixture_copy, now=SECOND_NOW).export(
        CASE_NUMBER, output_root, initiated_by_user_id=MANAGER_ID
    )
    assert first.total_messages == second.total_messages == 4
    assert second.added_messages == 0
    assert second.unchanged is False
    thread = load_object(second.output_directory / "thread.json")
    exported = thread["messages"]
    assert isinstance(exported, list)
    assert exported[1]["body"] == messages[1]["body"]
    assert len({item["messageId"] for item in exported}) == 4


def test_partial_output_or_wrong_incremental_owner_fails_closed(tmp_path: Path) -> None:
    output = tmp_path / CASE_NUMBER
    output.mkdir()
    (output / "thread.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ConflictError):
        pipeline().export(CASE_NUMBER, tmp_path, initiated_by_user_id=MANAGER_ID)

    shutil.rmtree(output)
    pipeline().export(CASE_NUMBER, tmp_path, initiated_by_user_id=MANAGER_ID)
    with pytest.raises(ConflictError):
        pipeline().export(CASE_NUMBER, tmp_path, initiated_by_user_id="usr_archive_manager")


def test_private_selection_and_live_adapter_fail_before_network(tmp_path: Path) -> None:
    with pytest.raises(ResourceNotFoundError, match="not found"):
        pipeline().export("C99-B4W9K6-0702-1500-P", tmp_path, initiated_by_user_id=MANAGER_ID)
    assert not any(tmp_path.iterdir())

    with pytest.raises(AuthorizationError):
        LiveDiscordExportAdapter("ARCHIVE_READER_DISCORD_TOKEN", environ={})
    live = LiveDiscordExportAdapter(
        "ARCHIVE_READER_DISCORD_TOKEN",
        environ={"ARCHIVE_READER_DISCORD_TOKEN": "fixture-only-value"},
    )
    with pytest.raises(ProviderUnavailableError, match="not implemented"):
        live.resolve_case(CASE_NUMBER)


def test_export_pipeline_contains_no_continuous_process() -> None:
    import tools.discord_export.cli as cli_module
    import tools.discord_export.pipeline as pipeline_module

    source = inspect.getsource(cli_module) + inspect.getsource(pipeline_module)
    assert "create_task(" not in source
    assert "asyncio.sleep" not in source
    assert "tasks.loop" not in source
