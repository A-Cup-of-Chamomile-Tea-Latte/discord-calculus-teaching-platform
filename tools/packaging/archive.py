"""Build a stable handoff ZIP without confusing fixtures with operator data."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXCLUDED_DIRECTORY_NAMES = frozenset(
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
        "dist",
        "htmlcov",
        "node_modules",
        "venv",
    }
)
EXCLUDED_TOP_LEVEL_DATA_DIRECTORIES = frozenset({"data", "exports", "local-data"})
EXCLUDED_FILE_SUFFIXES = frozenset({".key", ".log", ".pem", ".pyc", ".pyo", ".sqlite", ".sqlite3"})
EXCLUDED_CREDENTIAL_PATTERNS = (
    "*token*.json",
    "client_secret*.json",
    "credentials*.json",
    "deployment*.json",
    "service-account*.json",
)
REQUIRED_CREDENTIAL_NAMED_TEST_FIXTURES = frozenset(
    {"contracts/examples/invalid/user-with-oauth-token.json"}
)


@dataclass(frozen=True, slots=True)
class ArchiveResult:
    output: Path
    file_count: int
    size_bytes: int
    sha256: str


def _is_excluded(relative_path: PurePosixPath) -> bool:
    parts = relative_path.parts
    if not parts:
        return True
    if parts[0] in EXCLUDED_TOP_LEVEL_DATA_DIRECTORIES:
        return True
    if any(part in EXCLUDED_DIRECTORY_NAMES or part == "local-data" for part in parts[:-1]):
        return True

    name = relative_path.name
    if name in {".DS_Store", ".clasp.json", ".clasprc.json"}:
        return True
    if name.startswith("._") or name.endswith((".tmp", ".swp", "~")):
        return True
    if relative_path.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return True
    if relative_path.suffix.lower() in {".zip", ".sha256"}:
        return True
    if relative_path.as_posix() not in REQUIRED_CREDENTIAL_NAMED_TEST_FIXTURES and any(
        fnmatch.fnmatch(name.lower(), pattern) for pattern in EXCLUDED_CREDENTIAL_PATTERNS
    ):
        return True
    return name.startswith(".env") and name != ".env.example"


def iter_archive_files(root: Path) -> list[Path]:
    """Return a sorted immutable inventory relative to *root*.

    Exclusions are component-aware: top-level ``exports/`` is operator output,
    while ``fixtures/exports/`` remains part of the reproducible test dataset.
    Symlinks are intentionally omitted so an archive cannot escape the project.
    """

    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise ValueError("archive root must be a directory")

    included: list[Path] = []
    for directory, directory_names, file_names in os.walk(resolved_root, followlinks=False):
        current = Path(directory)
        relative_directory = current.relative_to(resolved_root)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if not (current / name).is_symlink()
            and not _is_excluded(PurePosixPath(*(relative_directory / name).parts, "placeholder"))
        )
        for name in sorted(file_names):
            path = current / name
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(resolved_root)
            if not _is_excluded(PurePosixPath(*relative.parts)):
                included.append(relative)
    return sorted(included, key=lambda path: path.as_posix())


def build_handoff_archive(root: Path, output: Path) -> ArchiveResult:
    """Atomically create a deterministic ZIP and return its integrity metadata."""

    resolved_root = root.resolve(strict=True)
    resolved_output = output.resolve()
    if resolved_output == resolved_root or (resolved_output.exists() and resolved_output.is_dir()):
        raise ValueError("output must be a ZIP file, not a directory")
    if resolved_output.suffix.lower() != ".zip":
        raise ValueError("output filename must end in .zip")

    files = iter_archive_files(resolved_root)
    required_fixture = Path("fixtures/exports/export-manifests.json")
    if required_fixture not in files:
        raise RuntimeError(f"required packaging fixture is missing: {required_fixture.as_posix()}")

    example_manifest_path = resolved_root / "contracts/examples/manifest.json"
    if example_manifest_path.is_file():
        example_manifest = json.loads(example_manifest_path.read_text(encoding="utf-8"))
        required_examples = {
            Path("contracts/examples") / entry["instance"]
            for group in ("valid", "invalid")
            for entry in example_manifest[group]
        }
        missing_examples = sorted(required_examples.difference(files))
        if missing_examples:
            missing = ", ".join(path.as_posix() for path in missing_examples)
            raise RuntimeError(
                f"contract examples referenced by the manifest are missing: {missing}"
            )

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    temporary_handle, temporary_name = tempfile.mkstemp(
        prefix=f".{resolved_output.stem}.", suffix=".tmp", dir=resolved_output.parent
    )
    os.close(temporary_handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            for relative in files:
                payload = (resolved_root / relative).read_bytes()
                info = zipfile.ZipInfo(relative.as_posix(), date_time=FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        os.replace(temporary, resolved_output)
    finally:
        if temporary.exists():
            temporary.unlink()

    payload = resolved_output.read_bytes()
    return ArchiveResult(
        output=resolved_output,
        file_count=len(files),
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
