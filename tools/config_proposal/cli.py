"""Local-only proposed configuration command line interface."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.config_proposal.core import generate_documents, load_bundle, validate_bundle


def _default_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate proposed local configuration and generate review documents"
    )
    parser.add_argument(
        "command",
        choices=("validate", "generate"),
        help="validate only, or validate and regenerate docs/generated",
    )
    parser.add_argument("--root", type=Path, default=_default_root())
    args = parser.parse_args(argv)

    bundle = load_bundle(args.root)
    issues = validate_bundle(args.root, bundle)
    for issue in issues:
        print(f"{issue.severity} {issue.code} {issue.path}: {issue.message}")
    errors = [issue for issue in issues if issue.severity == "ERROR"]
    if errors:
        print(f"configuration validation failed: {len(errors)} error(s)")
        return 1
    if args.command == "generate":
        outputs = generate_documents(args.root, bundle, issues)
        print(f"generated {len(outputs)} document(s)")
    print(
        "configuration validation passed "
        f"with {sum(issue.severity == 'WARNING' for issue in issues)} warning(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
