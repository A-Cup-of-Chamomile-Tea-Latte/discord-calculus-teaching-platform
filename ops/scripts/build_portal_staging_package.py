#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELEASE_PATHS = (
    "runtime/discord-course-bots",
    "ops/requirements/discord-runtime.txt",
    "ops/systemd/calculus-portal-synthetic-staging.service",
    "ops/scripts/run-portal-synthetic-staging",
    "ops/scripts/portal_staging_smoke.py",
    "ops/scripts/install-portal-synthetic-staging.sh",
    "ops/scripts/rollback-portal-synthetic-staging.sh",
    "ops/portal-staging/HOST_PROXY_ADAPTER_CONTRACT.md",
    "ops/portal-staging/host-config.example.json",
)
BUILD_INPUT_PATHS = (
    "apps/portal",
    "config/academic/115-1/course-operations.yaml",
    "runtime/discord-course-bots/src",
    "runtime/discord-course-bots/pyproject.toml",
    *RELEASE_PATHS[1:],
)
DENIED_NAMES = frozenset(
    {".env", "credentials.json", "token.json", "client_secret.json", "id_rsa", "id_ed25519"}
)
DENIED_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
BASE_PATH_RE = re.compile(r"^/[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*$")


class PackageError(RuntimeError):
    pass


def normalize_contract(origin: str, base_path: str) -> tuple[str, str]:
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise PackageError("ORIGIN_INVALID")
    normalized_origin = f"https://{parsed.netloc}"
    if base_path != "/" and not BASE_PATH_RE.fullmatch(base_path):
        raise PackageError("BASE_PATH_INVALID")
    return normalized_origin, base_path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def regular_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise PackageError(f"SYMLINK_REFUSED:{path.relative_to(root)}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise PackageError(f"SPECIAL_FILE_REFUSED:{path.relative_to(root)}")
        lowered = path.name.casefold()
        if lowered in DENIED_NAMES or lowered.endswith(DENIED_SUFFIXES):
            raise PackageError(f"SECRET_FILENAME_REFUSED:{path.relative_to(root)}")
        files.append(path)
    return files


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def git_output(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=PROJECT_ROOT, text=True).strip()


def export_release(commit: str, destination: Path) -> None:
    archive = subprocess.Popen(
        ["git", "archive", "--format=tar", commit, *RELEASE_PATHS],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
    )
    assert archive.stdout is not None
    with tarfile.open(fileobj=archive.stdout, mode="r|") as source:
        source.extractall(destination, filter="data")
    if archive.wait() != 0:
        raise PackageError("GIT_ARCHIVE_FAILED")


def copy_payload(exported: Path, static: Path, package: Path) -> None:
    shutil.copytree(exported / "runtime", package / "runtime")
    (package / "static").mkdir()
    shutil.copytree(static, package / "static", dirs_exist_ok=True)
    ops = package / "ops"
    ops.mkdir()
    shutil.copy2(
        exported / "ops/requirements/discord-runtime.txt",
        ops / "portal-runtime-requirements.txt",
    )
    shutil.copy2(
        exported / "ops/systemd/calculus-portal-synthetic-staging.service",
        ops / "calculus-portal-synthetic-staging.service",
    )
    for name in (
        "run-portal-synthetic-staging",
        "portal_staging_smoke.py",
        "install-portal-synthetic-staging.sh",
        "rollback-portal-synthetic-staging.sh",
    ):
        shutil.copy2(exported / "ops/scripts" / name, ops / name)
    shutil.copy2(
        exported / "ops/portal-staging/HOST_PROXY_ADAPTER_CONTRACT.md",
        package / "HOST_PROXY_ADAPTER_CONTRACT.md",
    )
    shutil.copy2(
        exported / "ops/portal-staging/host-config.example.json",
        package / "host-config.example.json",
    )


def deterministic_tar(source: Path, destination: Path, mtime: int) -> None:
    with tarfile.open(destination, "w", format=tarfile.PAX_FORMAT) as archive:
        for path in [source, *sorted(source.rglob("*"))]:
            info = archive.gettarinfo(path, arcname=path.relative_to(source.parent))
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = mtime
            if info.isdir():
                info.mode = 0o755
                archive.addfile(info)
            else:
                info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
                with path.open("rb") as handle:
                    archive.addfile(info, handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build exact Portal synthetic staging package")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--base-path", default="/")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    origin, base_path = normalize_contract(args.origin, args.base_path)
    commit = git_output("rev-parse", args.commit)
    release_id = commit[:12]
    if args.plan_only:
        print("portal_staging_package_plan=PASS")
        print(f"release_id={release_id}")
        print(f"origin={origin}")
        print(f"base_path={base_path}")
        return 0
    dirty_inputs = git_output(
        "status", "--porcelain", "--untracked-files=no", "--", *BUILD_INPUT_PATHS
    )
    if dirty_inputs:
        raise PackageError("PACKAGE_BUILD_INPUTS_NOT_CLEAN")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    package = output / f"portal-staging-{release_id}"
    archive_path = output / f"portal-staging-{release_id}.tar"
    if package.exists() or archive_path.exists():
        raise PackageError("OUTPUT_ALREADY_EXISTS")

    with tempfile.TemporaryDirectory(prefix="portal-staging-build.") as temporary:
        exported = Path(temporary) / "export"
        exported.mkdir()
        export_release(commit, exported)
        env = os.environ.copy()
        normalized_base = "" if base_path == "/" else base_path
        env.update(
            {
                "ASTRO_BASE_PATH": base_path,
                "ASTRO_SITE_URL": origin,
                "PUBLIC_PORTAL_BUILD": "true",
                "PUBLIC_JOIN_APPLICATION_ENDPOINT": f"{normalized_base}/api/join",
                "PUBLIC_PORTAL_SESSION_ENDPOINT": f"{normalized_base}/api/session",
                "PUBLIC_CASE_STATUS_ENDPOINT": f"{normalized_base}/api/cases/lookup",
            }
        )
        run(
            ["npm", "run", "build:public", "--workspace", "@calculus/portal"],
            cwd=PROJECT_ROOT,
            env=env,
        )
        run(
            [
                "npm",
                "run",
                "verify:public",
                "--workspace",
                "@calculus/portal",
                "--",
                base_path,
            ],
            cwd=PROJECT_ROOT,
            env=env,
        )
        copy_payload(exported, PROJECT_ROOT / "apps/portal/dist", package)

    files_before_manifest = regular_files(package)
    manifest = {
        "schemaVersion": "1.0",
        "kind": "CALCULUS_PORTAL_SYNTHETIC_STAGING",
        "releaseId": release_id,
        "commit": commit,
        "origin": origin,
        "basePath": base_path,
        "syntheticOnly": True,
        "productionConnected": False,
        "sourceFiles": len(files_before_manifest),
    }
    (package / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    checksum_files = regular_files(package)
    (package / "SHA256SUMS").write_text(
        "".join(f"{digest(path)}  {path.relative_to(package)}\n" for path in checksum_files),
        encoding="utf-8",
    )
    regular_files(package)
    commit_time = int(git_output("show", "-s", "--format=%ct", commit))
    deterministic_tar(package, archive_path, commit_time)
    (archive_path.with_suffix(".tar.sha256")).write_text(
        f"{digest(archive_path)}  {archive_path.name}\n", encoding="utf-8"
    )
    print("portal_staging_package=PASS")
    print(f"release_id={release_id}")
    print(f"archive_sha256={digest(archive_path)}")
    print("contains_secrets=NO")
    print("contains_symlinks=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
