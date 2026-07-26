"""Canonical fixture-only dump bot; archive_reader remains a compatibility package."""

from bots.archive_reader.admin_app import ArchiveReaderAdminApp as DumpBotAdminApp
from bots.archive_reader.service import ArchiveReaderService as DumpBotService
from bots.dump_bot.inventory import FixtureStructureInventorySource, StructureInventoryService
from bots.dump_bot.reconciliation import build_export_manifest, reconcile_handoff

__all__ = [
    "DumpBotAdminApp",
    "DumpBotService",
    "FixtureStructureInventorySource",
    "StructureInventoryService",
    "build_export_manifest",
    "reconcile_handoff",
]
