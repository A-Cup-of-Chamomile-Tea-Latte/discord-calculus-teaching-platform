from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from discord_course_bots.data_lab.service import (
    apply_ingest,
    case_status,
    dry_run_ingest,
    inspect_run,
    staging_summary,
)


def _print(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 2B synthetic staging data lab")
    parser.add_argument(
        "--lab-root", type=Path, default=Path(".local/phase2b-data-lab")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--fixture", required=True)
    mode = ingest.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    ingest.add_argument("--confirm")
    status = commands.add_parser("case-status")
    status.add_argument("--case-ref", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--run-id", required=True)
    commands.add_parser("summary")
    commands.add_parser("create-case").add_argument("--interactive", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "ingest":
        if args.dry_run:
            _print(dry_run_ingest(args.lab_root, args.fixture))
        else:
            if not args.confirm:
                raise SystemExit("--apply requires --confirm <nonce>")
            _print(apply_ingest(args.lab_root, args.fixture, args.confirm))
    elif args.command == "case-status":
        _print(case_status(args.lab_root, args.case_ref))
    elif args.command == "inspect":
        _print(inspect_run(args.lab_root, args.run_id))
    elif args.command == "summary":
        _print(staging_summary(args.lab_root))
    else:
        raise SystemExit(
            "Interactive wizard accepts only synthetic fields and will be enabled "
            "after lab review; "
            "use an allowlisted --fixture for this staging mission."
        )


if __name__ == "__main__":
    main()
