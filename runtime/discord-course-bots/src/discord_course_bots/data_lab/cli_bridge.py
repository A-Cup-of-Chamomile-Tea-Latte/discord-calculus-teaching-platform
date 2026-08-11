from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from discord_course_bots.data_lab.carrier import ensure_staging_carrier, load_staging_config
from discord_course_bots.data_lab.commands import command_status, fetch_once
from discord_course_bots.data_lab.projection import project_once, projection_status
from discord_course_bots.data_lab.transport import FakeGasTransport


def _print(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Phase 2B one-shot synthetic data bridge")
    result.add_argument("--lab-root", type=Path, default=Path(".local/phase2b-data-lab"))
    commands = result.add_subparsers(dest="command", required=True)
    project = commands.add_parser("project")
    project.add_argument("--once", action="store_true", required=True)
    mode = project.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    project.add_argument("--confirm")
    commands.add_parser("projection-status")
    fetch = commands.add_parser("fetch")
    fetch.add_argument("--once", action="store_true", required=True)
    fetch_mode = fetch.add_mutually_exclusive_group(required=True)
    fetch_mode.add_argument("--dry-run", action="store_true")
    fetch_mode.add_argument("--apply", action="store_true")
    fetch.add_argument("--confirm")
    status = commands.add_parser("command-status")
    status.add_argument("--command-id", required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    if args.command == "projection-status":
        _print(projection_status(args.lab_root))
        return
    paths = ensure_staging_carrier(args.lab_root)
    config = load_staging_config(paths)
    transport = FakeGasTransport(str(config["expectedSourceFingerprint"]))
    if args.command == "project":
        _print(
            project_once(
                args.lab_root,
                transport,
                apply=args.apply,
                confirmation_nonce=args.confirm,
            )
        )
        return
    if args.command == "command-status":
        _print(command_status(args.lab_root, args.command_id))
        return
    if args.command == "fetch":
        if args.apply and not args.confirm:
            raise SystemExit("--apply requires --confirm <nonce>")
        _print(
            fetch_once(
                args.lab_root,
                transport,
                apply=args.apply,
                confirmation_nonce=args.confirm,
            )
        )


if __name__ == "__main__":
    main()
