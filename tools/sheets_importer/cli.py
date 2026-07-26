from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from bots.common.contracts import ContractRegistry
from bots.common.errors import BotCoreError
from tools.sheets_importer.adapters import (
    CsvDirectoryAdapter,
    DryRunAdapter,
    FutureGoogleSheetsApiAdapter,
    MockAppsScriptEndpointAdapter,
)
from tools.sheets_importer.importer import BatchImporter
from tools.sheets_importer.models import BatchDestination, DestinationMap


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch curated export rows to a local adapter.")
    parser.add_argument("raw_metadata", type=Path)
    parser.add_argument("sanitized_thread", type=Path)
    parser.add_argument("--summaries", type=Path)
    parser.add_argument(
        "--adapter", choices=("dry-run", "csv", "mock", "sheets"), default="dry-run"
    )
    parser.add_argument("--csv-dir", type=Path, default=Path("local-data/import-csv"))
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--exports-sheet", default="Exports")
    parser.add_argument("--messages-sheet", default="AnalysisMessages")
    parser.add_argument("--summaries-sheet", default="AnalysisSummaries")
    arguments = parser.parse_args(argv)
    destination: BatchDestination
    if arguments.adapter == "dry-run":
        destination = DryRunAdapter()
    elif arguments.adapter == "csv":
        destination = CsvDirectoryAdapter(arguments.csv_dir)
    elif arguments.adapter == "mock":
        destination = MockAppsScriptEndpointAdapter()
    else:
        destination = FutureGoogleSheetsApiAdapter()
    importer = BatchImporter(
        destination,
        ContractRegistry.project_default(),
        destination_map=DestinationMap(
            arguments.exports_sheet,
            arguments.messages_sheet,
            arguments.summaries_sheet,
        ),
        batch_size=arguments.batch_size,
        max_retries=arguments.max_retries,
    )
    report = importer.import_package(
        arguments.raw_metadata,
        arguments.sanitized_thread,
        summaries_path=arguments.summaries,
    )
    print(
        json.dumps(
            {
                "planned": report.planned,
                "succeeded": report.succeeded,
                "skipped": report.skipped,
                "failed": [failure.__dict__ for failure in report.failed],
                "batches": report.batches,
                "retries": report.retries,
                "rows": [
                    {
                        "sheet": row.sheet,
                        "idempotencyKey": row.idempotency_key,
                        "values": row.values,
                    }
                    for row in report.rows
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if report.failed else 0


def run() -> None:
    try:
        raise SystemExit(main())
    except (BotCoreError, OSError, ValueError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
