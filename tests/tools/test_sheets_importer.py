from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from bots.common.contracts import ContractRegistry
from bots.common.errors import ContractValidationError, NotConfiguredError
from tools.anonymizer.pipeline import AnonymizerPipeline
from tools.discord_export.adapters import FixtureExportAdapter
from tools.discord_export.pipeline import DiscordExportPipeline
from tools.sheets_importer.adapters import (
    CsvDirectoryAdapter,
    DryRunAdapter,
    FutureGoogleSheetsApiAdapter,
    MockAppsScriptEndpointAdapter,
)
from tools.sheets_importer.importer import BatchImporter
from tools.sheets_importer.models import DestinationMap, ImportRow

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
NOW = "2026-07-19T18:00:00+08:00"


def package(tmp_path: Path) -> tuple[Path, Path]:
    contracts = ContractRegistry.project_default()
    raw = (
        DiscordExportPipeline(FixtureExportAdapter(FIXTURES, contracts), contracts, now=lambda: NOW)
        .export(
            "C01-7K4M2Q-0702-1000",
            tmp_path / "raw",
            initiated_by_user_id="usr_staff_example",
        )
        .output_directory
    )
    sanitized = (
        AnonymizerPipeline(FIXTURES, contracts, now=NOW)
        .sanitize(raw, tmp_path / "sanitized")
        .output_directory
    )
    return raw / "metadata.json", sanitized / "sanitized-thread.json"


def test_dry_run_shows_exact_curated_rows_without_raw_attachment_data(tmp_path: Path) -> None:
    metadata, sanitized = package(tmp_path)
    adapter = DryRunAdapter()
    report = BatchImporter(
        adapter, ContractRegistry.project_default(), batch_size=2
    ).import_package(metadata, sanitized)
    assert report.planned == report.succeeded == 5
    assert report.skipped == 0
    assert report.failed == ()
    assert report.batches == 3
    assert [row.sheet for row in report.rows] == ["Exports", *("AnalysisMessages",) * 4]
    assert [row.idempotency_key for row in report.rows] == [
        "export:export_case_000421_thread",
        "message:export_case_000421_thread:m001",
        "message:export_case_000421_thread:m002",
        "message:export_case_000421_thread:m003",
        "message:export_case_000421_thread:m004",
    ]
    serialized = json.dumps([row.values for row in report.rows])
    assert "discordMessageId" not in serialized
    assert "attachment_graph_a" not in serialized
    assert "fictional-limit-sketch.png" not in serialized
    assert "attachmentCount" in serialized


def test_reimport_with_same_adapter_skips_every_row(tmp_path: Path) -> None:
    metadata, sanitized = package(tmp_path)
    adapter = DryRunAdapter()
    importer = BatchImporter(adapter, ContractRegistry.project_default())
    first = importer.import_package(metadata, sanitized)
    second = importer.import_package(metadata, sanitized)
    assert first.succeeded == 5
    assert second.succeeded == 0
    assert second.skipped == 5
    assert len(adapter.rows) == 5


def test_csv_adapter_persists_idempotency_across_instances(tmp_path: Path) -> None:
    metadata, sanitized = package(tmp_path)
    csv_directory = tmp_path / "csv"
    first = BatchImporter(
        CsvDirectoryAdapter(csv_directory), ContractRegistry.project_default()
    ).import_package(metadata, sanitized)
    second = BatchImporter(
        CsvDirectoryAdapter(csv_directory), ContractRegistry.project_default()
    ).import_package(metadata, sanitized)
    assert first.succeeded == 5
    assert second.skipped == 5
    with (csv_directory / "AnalysisMessages.csv").open(encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 4
    assert csv_directory.stat().st_mode & 0o777 == 0o700
    assert (csv_directory / "AnalysisMessages.csv").stat().st_mode & 0o777 == 0o600


def test_retry_and_partial_failure_keep_successful_rows(tmp_path: Path) -> None:
    metadata, sanitized = package(tmp_path)
    retry_key = "message:export_case_000421_thread:m002"
    failure_key = "message:export_case_000421_thread:m003"
    adapter = MockAppsScriptEndpointAdapter(
        {retry_key: ("RETRY", "SUCCEEDED"), failure_key: ("FAIL",)}
    )
    report = BatchImporter(
        adapter, ContractRegistry.project_default(), batch_size=4, max_retries=2
    ).import_package(metadata, sanitized)
    assert report.succeeded == 4
    assert report.retries == 1
    assert len(report.failed) == 1
    assert report.failed[0].idempotency_key == failure_key
    assert {row.idempotency_key for row in adapter.accepted} == {
        row.idempotency_key for row in report.rows if row.idempotency_key != failure_key
    }


def test_summary_and_destination_mapping_are_configurable(tmp_path: Path) -> None:
    metadata, sanitized = package(tmp_path)
    summaries = tmp_path / "summaries.json"
    summaries.write_text(
        json.dumps(
            [
                {
                    "summaryId": "summary_01",
                    "summaryType": "MANAGER_NOTE",
                    "body": "Fictional manager-reviewed summary.",
                    "createdAt": NOW,
                }
            ]
        ),
        encoding="utf-8",
    )
    mapping = DestinationMap("ExportLedger", "CuratedMessages", "ReviewedSummaries")
    report = BatchImporter(
        DryRunAdapter(), ContractRegistry.project_default(), destination_map=mapping
    ).import_package(metadata, sanitized, summaries_path=summaries)
    assert report.planned == 6
    assert {row.sheet for row in report.rows} == {
        "ExportLedger",
        "CuratedMessages",
        "ReviewedSummaries",
    }


def test_excluded_manifest_and_future_api_fail_without_external_call(tmp_path: Path) -> None:
    metadata_path, sanitized = package(tmp_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["analysisPermission"] = "EXCLUDED"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ContractValidationError):
        BatchImporter(DryRunAdapter(), ContractRegistry.project_default()).import_package(
            metadata_path, sanitized
        )

    future = FutureGoogleSheetsApiAdapter()
    with pytest.raises(NotConfiguredError, match="no external request"):
        future.write_batch("Exports", (ImportRow("Exports", "export:test", {}),))


def test_sanitized_package_must_bind_to_the_same_raw_export(tmp_path: Path) -> None:
    metadata_path, sanitized_path = package(tmp_path)
    sanitized = json.loads(sanitized_path.read_text(encoding="utf-8"))
    sanitized["sourceExportId"] = "export_other_thread"
    sanitized_path.write_text(json.dumps(sanitized), encoding="utf-8")
    with pytest.raises(ContractValidationError, match="not bound"):
        BatchImporter(DryRunAdapter(), ContractRegistry.project_default()).import_package(
            metadata_path, sanitized_path
        )
