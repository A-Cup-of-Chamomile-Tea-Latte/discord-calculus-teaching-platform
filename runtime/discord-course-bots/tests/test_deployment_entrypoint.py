from __future__ import annotations

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEPLOYER = PROJECT_ROOT / "ops/scripts/calculus-discord-deploy"
INSTALLER = PROJECT_ROOT / "ops/scripts/install-calculus-discord-deployer.sh"
PREPARER = PROJECT_ROOT / "ops/scripts/prepare-calculus-discord-deploy-request.sh"
REPAIRER = PROJECT_ROOT / "ops/scripts/phase2c-repair-restricted-deployer.sh"
HOST_PREPARER = PROJECT_ROOT / "ops/scripts/v13-host-owner-prepare.sh"
FRIEND_BOOTSTRAP = PROJECT_ROOT / "ops/scripts/v13-friend-bootstrap.sh"
SUDOERS = PROJECT_ROOT / "ops/sudoers/calculus-discord-deploy"
DEPENDENCY_LOCK = PROJECT_ROOT / "ops/requirements/discord-runtime.txt"
SUPERSEDED_MUTATORS = (
    PROJECT_ROOT / "ops/scripts/phase2c-lifecycle-ux-upgrade.sh",
    PROJECT_ROOT / "ops/scripts/phase2c-remote-cutover.sh",
    PROJECT_ROOT / "ops/scripts/phase2c-repair-venv-and-resume.sh",
)


def test_deployment_scripts_are_executable_and_parse_as_bash() -> None:
    for script in (
        DEPLOYER,
        INSTALLER,
        PREPARER,
        REPAIRER,
        HOST_PREPARER,
        FRIEND_BOOTSTRAP,
    ):
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
    assert "ADDITIVE_MIGRATION_CHAIN_REFUSED" in source
    assert "current_schema -eq 6 && $target_schema -eq 13" in source
    assert 'filter="data"' in source
    assert "calculus-builder" in source
    assert "rollback=APPLIED" in source
    assert "rollback=FAILED_SERVICES_STOPPED" in source
    assert "remote_services=STOPPED" in source
    assert "RESTORE_ATTEMPTED" not in source
    assert 'chmod -R u=rwX,go=rX "$release_destination"' in source
    assert "BUILDER_RUNTIME_ACCESS_DENIED" in source
    assert "SERVICE_RUNTIME_ACCESS_DENIED" in source
    assert (
        'install -d -o calculus-builder -g calculus-builder -m 0700 "$migration_workspace"'
        in source
    )
    assert "MIGRATION_WORKSPACE_NOT_WRITABLE" in source
    assert "STAGING_DATABASE_NOT_WRITABLE" in source
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
    assert "printf 'deploy_executed=NO\\n'" in source
    assert source.rstrip().endswith("printf 'deploy_executed=NO\\n'")


def test_one_time_repairer_is_guarded_and_only_replaces_the_deployer() -> None:
    source = REPAIRER.read_text(encoding="utf-8")
    assert "REPAIR_CALCULUS_DEPLOYER=REPAIR-CALCULUS-DEPLOYER" not in source
    assert "REPAIR_CALCULUS_DEPLOYER:-" in source
    assert "expected_old_sha256=" in source
    assert "INSTALLED_DEPLOYER_VERSION_REFUSED" in source
    assert "ALREADY_READY" in source
    assert "SUDOERS_RULE_MISMATCH" in source
    assert "SUDOERS_RULE_MISSING" in source
    assert "install -o root -g root -m 0440" not in source
    assert "/etc/calculus-discord" not in source


def test_v13_host_preparer_is_exact_scope_and_never_deploys() -> None:
    source = HOST_PREPARER.read_text(encoding="utf-8")
    assert "PREPARE_V13_HOST:-" in source
    assert "PRODUCTION_DATABASE_V6_INVALID" in source
    assert "--expected-source-schema 6 --expected-target-schema 13" in source
    assert "BOT_OWNER_IDS" in source
    assert "v13_host_prepare=PASS" in source
    assert "deploy_executed=NO" in source
    assert "systemctl stop" not in source
    assert "systemctl start" not in source
    assert "sudo -n /usr/local/sbin/calculus-discord-deploy" not in source


def test_superseded_phase2c_mutators_refuse_before_old_logic() -> None:
    for script in SUPERSEDED_MUTATORS:
        lines = script.read_text(encoding="utf-8").splitlines()
        assert lines[1] == "printf 'phase2c_error=SUPERSEDED_USE_V13_HOST_OWNER_PREPARE\\n' >&2"
        assert lines[2] == "exit 2"


def test_friend_bootstrap_validates_exact_archive_then_only_prepares_host() -> None:
    source = FRIEND_BOOTSTRAP.read_text(encoding="utf-8")
    assert "BOOTSTRAP_V13_RELEASE:-" in source
    assert "ARCHIVE_PATH_REFUSED" in source
    assert "os.O_NOFOLLOW" in source
    assert "hashlib.file_digest" in source
    assert 'bundle.pax_headers.get("comment"' in source
    assert 'bundle.extractall(destination, filter="data")' in source
    assert "PREPARE_V13_HOST=PREPARE-V13-HOST" in source
    assert "deploy_executed=NO" in source
    assert "systemctl stop" not in source
    assert "systemctl start" not in source
    assert "/usr/local/sbin/calculus-discord-deploy" not in source
