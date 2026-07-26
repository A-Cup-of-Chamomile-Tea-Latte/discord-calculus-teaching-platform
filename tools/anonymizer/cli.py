from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from bots.common.contracts import ContractRegistry
from bots.common.errors import BotCoreError
from tools.anonymizer.pipeline import AnonymizerPipeline

ROOT = Path(__file__).resolve().parents[2]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a manager-reviewed sanitized package.")
    parser.add_argument("raw_case_directory", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "local-data/sanitized")
    parser.add_argument("--fixture-root", type=Path, default=ROOT / "fixtures")
    arguments = parser.parse_args(argv)
    pipeline = AnonymizerPipeline(
        arguments.fixture_root,
        ContractRegistry.project_default(),
        now=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    result = pipeline.sanitize(arguments.raw_case_directory, arguments.output_dir)
    print(
        json.dumps(
            {
                "outputDirectory": str(result.output_directory),
                "includedMessages": result.included_messages,
                "placeholderMessages": result.placeholder_messages,
                "redactionEvents": result.redaction_events,
                "reviewFlags": result.review_flags,
            },
            ensure_ascii=False,
        )
    )
    return 0


def run() -> None:
    try:
        raise SystemExit(main())
    except (BotCoreError, OSError, ValueError) as error:
        print(f"Anonymization failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
