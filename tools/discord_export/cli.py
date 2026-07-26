"""Command-line entry point for one explicit local export invocation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from bots.common.contracts import ContractRegistry
from bots.common.errors import BotCoreError
from tools.discord_export.adapters import FixtureExportAdapter, LiveDiscordExportAdapter
from tools.discord_export.models import ThreadExportAdapter
from tools.discord_export.pipeline import DiscordExportPipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.discord_export",
        description="Export one selected fixture/Discord thread to deterministic local files.",
    )
    parser.add_argument("selection", help="Case number or Discord thread ID")
    parser.add_argument("--adapter", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "exports")
    parser.add_argument("--fixture-root", type=Path, default=PROJECT_ROOT / "fixtures")
    parser.add_argument("--after-message-id")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--initiated-by-user-id")
    parser.add_argument(
        "--credential-env",
        default="ARCHIVE_READER_DISCORD_TOKEN",
        help="Environment-variable name only; never pass a credential value as an argument.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    contracts = ContractRegistry.project_default()
    adapter: ThreadExportAdapter
    if arguments.adapter == "fixture":
        adapter = FixtureExportAdapter(arguments.fixture_root, contracts)
        initiated_by = arguments.initiated_by_user_id or "usr_staff_example"
    else:
        if arguments.initiated_by_user_id is None:
            parser.error("live adapter requires --initiated-by-user-id")
        adapter = LiveDiscordExportAdapter(arguments.credential_env)
        initiated_by = arguments.initiated_by_user_id
    pipeline = DiscordExportPipeline(adapter, contracts, now=_utc_now)
    result = pipeline.export(
        arguments.selection,
        arguments.output_dir,
        initiated_by_user_id=initiated_by,
        after_message_id=arguments.after_message_id,
        page_size=arguments.page_size,
    )
    print(
        json.dumps(
            {
                "outputDirectory": str(result.output_directory),
                "totalMessages": result.total_messages,
                "addedMessages": result.added_messages,
                "pageCount": result.page_count,
                "checkpoint": result.checkpoint,
                "unchanged": result.unchanged,
            },
            ensure_ascii=False,
        )
    )
    return 0


def run() -> None:
    try:
        raise SystemExit(main())
    except (BotCoreError, OSError, ValueError) as error:
        print(f"Export failed: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        print("Export cancelled.", file=sys.stderr)
        raise SystemExit(130) from None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
