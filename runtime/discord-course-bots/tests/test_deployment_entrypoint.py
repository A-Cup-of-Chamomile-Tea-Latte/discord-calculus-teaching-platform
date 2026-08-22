from __future__ import annotations

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEPLOYER = PROJECT_ROOT / "ops/scripts/calculus-discord-deploy"
INSTALLER = PROJECT_ROOT / "ops/scripts/install-calculus-discord-deployer.sh"
PREPARER = PROJECT_ROOT / "ops/scripts/prepare-calculus-discord-deploy-request.sh"
SUDOERS = PROJECT_ROOT / "ops/sudoers/calculus-discord-deploy"
DEPENDENCY_LOCK = PROJECT_ROOT / "ops/requirements/discord-runtime.txt"


def test_deployment_scripts_are_executable_and_parse_as_bash() -> None:
    for script in (DEPLOYER, INSTALLER, PREPARER):
        assert os.access(script, os.X_OK)
        subprocess.run(["bash", "-n", script], check=True)


def test_sudoers_rule_grants_only_the_fixed_root_owned_entrypoint() -> None:
    active_lines = [
        line.strip()
        for line in SUDOERS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert active_lines == ['ding ALL=(root) NOPASSWD: /usr/local/sbin/calculus-discord-deploy ""']


def test_deployer_is_fixed_scope_and_does_not_install_units_or_secrets() -> None:
    source = DEPLOYER.read_text(encoding="utf-8")
    assert "[[ $# -eq 0 ]] || fail ARGUMENTS_REFUSED" in source
    assert "deploy-inbox" in source
    assert "migration_class=(NONE|ADDITIVE)" in source
    assert 'filter="data"' in source
    assert "calculus-builder" in source
    assert "rollback=APPLIED" in source
    assert "ops/systemd" not in source
    assert "/etc/calculus-discord/*.env" not in source
    assert "google-oauth.json" not in source


def test_release_dependency_lock_uses_only_exact_pins() -> None:
    pins = [
        line.strip()
        for line in DEPENDENCY_LOCK.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert pins
    assert all("==" in pin and not any(mark in pin for mark in (">", "<", "~=")) for pin in pins)
    assert "ops/requirements/discord-runtime.txt" in DEPLOYER.read_text(encoding="utf-8")


def test_installer_explicitly_reports_unchanged_network_secrets_and_units() -> None:
    source = INSTALLER.read_text(encoding="utf-8")
    assert "[[ $# -eq 1 ]] || fail ARGUMENTS_INVALID" in source
    assert "new_port=NO" in source
    assert "secrets_changed=NO" in source
    assert "systemd_units_changed=NO" in source
