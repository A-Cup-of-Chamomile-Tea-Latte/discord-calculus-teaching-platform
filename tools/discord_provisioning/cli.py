"""Read-only CLI that prints a dry-run and its rollback plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.discord_provisioning.planner import compute_diff, print_plan, rollback_plan


def _read(path: Path) -> dict[str, Any]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("fixture document must be an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print a fixture-only Discord provisioning diff")
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--desired", type=Path, required=True)
    args = parser.parse_args(argv)
    changes = compute_diff(_read(args.current), _read(args.desired))
    print(print_plan(changes))
    print("\nRollback plan:\n")
    print(print_plan(rollback_plan(changes)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
