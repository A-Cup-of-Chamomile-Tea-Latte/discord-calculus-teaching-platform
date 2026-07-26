"""Lightweight secret-pattern check for files that Git could commit."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str


_PRIVATE_KEY_MARKER: Final = "-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
_RULES: Final = (
    ("private-key", re.compile(_PRIVATE_KEY_MARKER)),
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_-]{30,}")),
    (
        "assigned-secret",
        re.compile(
            r"(?im)^\s*(?:DISCORD_[A-Z_]*TOKEN|GOOGLE_[A-Z_]*(?:SECRET|KEY)|"
            r"OAUTH_[A-Z_]*SECRET)\s*=\s*['\"]?[^\s#'\"]{12,}"
        ),
    ),
)

_FALLBACK_EXCLUDED_DIRECTORIES: Final = frozenset(
    {
        ".astro",
        ".cache",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "data",
        "dist",
        "exports",
        "htmlcov",
        "local-data",
        "node_modules",
        "venv",
    }
)
_FALLBACK_ARCHIVE_SUFFIXES: Final = frozenset(
    {".7z", ".bz2", ".dmg", ".gz", ".iso", ".rar", ".tar", ".tgz", ".whl", ".xz", ".zip"}
)


def _git_candidates(root: Path) -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            check=False,
            capture_output=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return sorted(root / item.decode() for item in result.stdout.split(b"\0") if item)


def _fallback_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(
            part in _FALLBACK_EXCLUDED_DIRECTORIES or part.endswith(".egg-info")
            for part in relative.parts[:-1]
        ):
            continue
        name = path.name
        if name == ".DS_Store" or name.startswith("._"):
            continue
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            continue
        if path.suffix.lower() in _FALLBACK_ARCHIVE_SUFFIXES or name.endswith(".tar.gz"):
            continue
        yield path


def candidate_files(root: Path) -> list[Path]:
    """Return Git candidates, or a bounded filesystem fallback for handoff archives."""
    normalized_root = root.resolve()
    git_candidates = _git_candidates(normalized_root)
    if git_candidates is not None:
        return git_candidates
    return list(_fallback_files(normalized_root))


def scan_file(path: Path) -> list[Finding]:
    """Scan a reasonably sized UTF-8 text file and report rule names, never values."""
    if path.stat().st_size > 2_000_000:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    findings: list[Finding] = []
    for rule, pattern in _RULES:
        for match in pattern.finditer(text):
            findings.append(
                Finding(path=path, line=text.count("\n", 0, match.start()) + 1, rule=rule)
            )
    return findings


def scan_repository(root: Path) -> list[Finding]:
    """Scan all candidate files in a repository."""
    return [finding for path in candidate_files(root) for finding in scan_file(path)]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    findings = scan_repository(root)
    for finding in findings:
        print(f"{finding.path.relative_to(root)}:{finding.line}: {finding.rule}")
    if findings:
        print(f"secret scan failed: {len(findings)} finding(s)")
        return 1
    print(f"secret scan passed: {len(candidate_files(root))} candidate file(s), 0 findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
