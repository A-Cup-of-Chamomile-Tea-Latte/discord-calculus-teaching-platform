from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

import bots.dump_bot.inventory as inventory_module
from bots.archive_reader.admin_app import ArchiveReaderAdminApp
from bots.archive_reader.models import (
    AnalysisDecision,
    ArchiveMessageRecord,
    AuthorDisplayMode,
    AuthorRole,
    ExportHandoff,
    ExportMode,
)
from bots.archive_reader.service import ArchiveReaderService
from bots.dump_bot import (
    DumpBotAdminApp,
    DumpBotService,
    FixtureStructureInventorySource,
    StructureInventoryService,
    build_export_manifest,
    reconcile_handoff,
)

ROOT = Path(__file__).resolve().parents[2]


def inventory_fixture() -> dict[str, object]:
    value: object = json.loads(
        (ROOT / "fixtures/discord/structure-inventory.json").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_structure_inventory_is_fixture_only_and_matches_contract() -> None:
    inventory = StructureInventoryService().capture(
        FixtureStructureInventorySource(inventory_fixture())
    )
    schema = json.loads(
        (ROOT / "contracts/schemas/discord-structure-inventory.schema.json").read_text()
    )
    common = json.loads((ROOT / "contracts/schemas/common.schema.json").read_text())
    from referencing import Registry, Resource

    registry = Registry().with_resources(
        [
            (str(schema["$id"]), Resource.from_contents(schema)),
            (str(common["$id"]), Resource.from_contents(common)),
        ]
    )
    errors = list(
        Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()).iter_errors(
            inventory
        )
    )
    assert errors == []
    assert "messages" not in str(inventory)


def test_structure_inventory_rejects_live_or_content_shaped_sources() -> None:
    class LiveSource:
        fixture_only = False

        def read_structure(self) -> dict[str, object]:
            return inventory_fixture()

    with pytest.raises(PermissionError):
        StructureInventoryService().capture(LiveSource())
    unsafe = inventory_fixture()
    server = unsafe["server"]
    assert isinstance(server, dict)
    unsafe["server"] = {**server, "messages": []}
    with pytest.raises(ValueError):
        StructureInventoryService().capture(FixtureStructureInventorySource(unsafe))

    member_target = inventory_fixture()
    overwrites = member_target["permissionOverwrites"]
    assert isinstance(overwrites, list)
    assert isinstance(overwrites[0], dict)
    overwrites[0]["targetType"] = "MEMBER"
    with pytest.raises(ValueError, match="role permission overwrites only"):
        StructureInventoryService().capture(FixtureStructureInventorySource(member_target))


def test_dump_bot_alias_preserves_existing_archive_reader_api_and_has_no_polling() -> None:
    assert DumpBotService is ArchiveReaderService
    assert DumpBotAdminApp is ArchiveReaderAdminApp
    source = inspect.getsource(inventory_module)
    assert "asyncio.sleep" not in source
    assert "create_task(" not in source


def test_reconciliation_and_export_manifest_are_deterministic() -> None:
    message = ArchiveMessageRecord(
        message_id="message_fixture_001",
        case_id="case_fixture_001",
        author_user_id="usr_fixture_ta",
        author_role=AuthorRole.TA,
        author_display_mode=AuthorDisplayMode.COURSE_ALIAS,
        body="Synthetic explanation.",
        analysis_permission=AnalysisDecision.INCLUDED,
        parent_message_id=None,
        discord_message_id="123456789012345678",
        edited_at=None,
        attachments=(),
        created_at="2026-07-23T09:00:00+08:00",
    )
    handoff = ExportHandoff(
        request_id="export_fixture_001",
        mode=ExportMode.DUMP,
        case_id="case_fixture_001",
        case_number="C99-Z8Y7X6-0723-0900",
        thread_id="fixture_thread_001",
        messages=(message,),
        starting_after_message_id=None,
        last_exported_message_id=message.discord_message_id,
        page_count=1,
        created_at="2026-07-23T09:00:00+08:00",
    )
    assert reconcile_handoff(handoff).consistent is True
    manifest = build_export_manifest(
        handoff,
        initiated_by_user_id="usr_fixture_ta",
        completed_at="2026-07-23T09:01:00+08:00",
    )
    assert manifest["messageCount"] == 1
    assert manifest["cursor"] == message.discord_message_id
    files = manifest["files"]
    assert isinstance(files, list)
    assert isinstance(files[0], dict)
    digest = files[0]["sha256"]
    assert isinstance(digest, str)
    assert len(digest) == 64
