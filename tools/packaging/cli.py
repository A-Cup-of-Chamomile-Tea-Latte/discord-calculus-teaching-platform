from __future__ import annotations

import argparse
from pathlib import Path

from .archive import build_handoff_archive


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Create a deterministic fixture-safe handoff ZIP")
    value.add_argument("--root", type=Path, default=Path.cwd(), help="project root")
    value.add_argument("--output", type=Path, required=True, help="output .zip path")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = build_handoff_archive(args.root, args.output)
    print(f"archive={result.output}")
    print(f"files={result.file_count}")
    print(f"bytes={result.size_bytes}")
    print(f"sha256={result.sha256}")
    return 0
