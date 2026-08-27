from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUILDER = PROJECT_ROOT / "ops/scripts/build_portal_staging_package.py"
INSTALLER = PROJECT_ROOT / "ops/scripts/install-portal-synthetic-staging.sh"
ROLLBACK = PROJECT_ROOT / "ops/scripts/rollback-portal-synthetic-staging.sh"
RUNNER = PROJECT_ROOT / "ops/scripts/run-portal-synthetic-staging"
SMOKE = PROJECT_ROOT / "ops/scripts/portal_staging_smoke.py"
UNIT = PROJECT_ROOT / "ops/systemd/calculus-portal-synthetic-staging.service"


def load_builder():
    spec = importlib.util.spec_from_file_location("portal_staging_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_staging_scripts_parse_and_plan_without_root(tmp_path: Path) -> None:
    for script in (INSTALLER, ROLLBACK, RUNNER):
        subprocess.run(["bash", "-n", script], check=True)
    subprocess.run(["python3", "-m", "py_compile", BUILDER, SMOKE], check=True)
    completed = subprocess.run(
        [
            "python3",
            BUILDER,
            "--origin",
            "https://staging.example.edu",
            "--base-path",
            "/portal-staging",
            "--output-dir",
            tmp_path,
            "--plan-only",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "portal_staging_package_plan=PASS" in completed.stdout


def test_package_contract_rejects_origin_paths_and_bad_base() -> None:
    builder = load_builder()
    assert builder.normalize_contract("https://staging.example.edu", "/") == (
        "https://staging.example.edu",
        "/",
    )
    with pytest.raises(builder.PackageError):
        builder.normalize_contract("https://staging.example.edu/path", "/")
    with pytest.raises(builder.PackageError):
        builder.normalize_contract("https://staging.example.edu", "/bad/")


def test_package_scan_rejects_symlinks_and_secret_filenames(tmp_path: Path) -> None:
    builder = load_builder()
    (tmp_path / "safe.txt").write_text("safe", encoding="utf-8")
    assert builder.regular_files(tmp_path) == [tmp_path / "safe.txt"]
    (tmp_path / "unsafe.env").write_text("SECRET=value", encoding="utf-8")
    # A suffix named .env is not automatically secret; the exact .env name is.
    assert len(builder.regular_files(tmp_path)) == 2
    (tmp_path / ".env").write_text("SECRET=value", encoding="utf-8")
    with pytest.raises(builder.PackageError, match="SECRET_FILENAME"):
        builder.regular_files(tmp_path)
    (tmp_path / ".env").unlink()
    (tmp_path / "link").symlink_to(tmp_path / "safe.txt")
    with pytest.raises(builder.PackageError, match="SYMLINK"):
        builder.regular_files(tmp_path)


def test_installer_dry_run_validates_exact_package_and_proxy_contract(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "payload.txt").write_text("safe", encoding="utf-8")
    digest = subprocess.check_output(["sha256sum", package / "payload.txt"], text=True).split()[0]
    (package / "manifest.json").write_text(
        json.dumps(
            {
                "releaseId": "0123456789ab",
                "origin": "https://staging.example.edu",
                "basePath": "/portal-staging",
            }
        ),
        encoding="utf-8",
    )
    manifest_digest = subprocess.check_output(
        ["sha256sum", package / "manifest.json"], text=True
    ).split()[0]
    (package / "SHA256SUMS").write_text(
        f"{digest}  payload.txt\n{manifest_digest}  manifest.json\n", encoding="utf-8"
    )
    adapter = tmp_path / "proxy-adapter"
    adapter.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    adapter.chmod(adapter.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "host.json"
    config.write_text(
        json.dumps(
            {
                "origin": "https://staging.example.edu",
                "basePath": "/portal-staging",
                "bindPort": 18081,
                "trustedProxyIp": "127.0.0.1",
                "proxyAdapter": str(adapter),
            }
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            "bash",
            INSTALLER,
            "--package-dir",
            package,
            "--host-config",
            config,
            "--dry-run",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "portal_staging_install_dry_run=PASS" in completed.stdout
    assert "production_modified=NO" in completed.stdout


def test_unit_isolated_from_production_and_uses_runtime_directory() -> None:
    source = UNIT.read_text(encoding="utf-8")
    assert "DynamicUser=yes" in source
    assert "RuntimeDirectory=calculus-portal-staging" in source
    assert "RuntimeDirectoryMode=0700" in source
    assert "InaccessiblePaths=-/var/lib/calculus-discord -/etc/calculus-discord" in source
    assert "IPAddressAllow=localhost" in source
    assert "/opt/calculus-discord/current" not in source
    assert "calculus-course-assistant.service" not in source
    assert "calculus-dump-bot.service" not in source
    assert "calculus-data-bridge.service" not in source
