from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tarfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEPLOYER = PROJECT_ROOT / "ops/scripts/calculus-discord-deploy"
INSTALLER = PROJECT_ROOT / "ops/scripts/install-calculus-discord-deployer.sh"
PREPARER = PROJECT_ROOT / "ops/scripts/prepare-calculus-discord-deploy-request.sh"
REPAIRER = PROJECT_ROOT / "ops/scripts/phase2c-repair-restricted-deployer.sh"
HOST_PREPARER = PROJECT_ROOT / "ops/scripts/v13-host-owner-prepare.sh"
FRIEND_BOOTSTRAP = PROJECT_ROOT / "ops/scripts/v13-friend-bootstrap.sh"
RUNBOOK = PROJECT_ROOT / "docs/ops/V13_RELEASE_SAFETY_RUNBOOK.md"
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
    assert "trusted_release_root=/var/lib/calculus-discord-deploy/releases" in source
    assert "LEGACY_INBOX_ARCHIVE_REFUSED" in source
    assert "PREFLIGHT_BINDING_INVALID" in source
    assert "preflight_root=/var/lib/calculus-discord-deploy/preflight" in source
    assert "rollback_root=/var/lib/calculus-discord-deploy/rollback" in source
    assert ".v13-source-archive.tar" in source
    assert 'rm -f -- "$request_source" || true' in source
    assert 'rm -f -- "$request_source" "$archive_source"' not in source
    assert "incoming_created=0" in source
    assert "release_created=0" in source
    assert "[[ ${incoming_created:-0} -eq 1" in source
    assert "[[ ${release_created:-0} -eq 1" in source
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


def test_request_preparer_uses_only_root_owned_frozen_archive() -> None:
    source = PREPARER.read_text(encoding="utf-8")
    assert "/var/lib/calculus-discord-deploy/releases/*" in source
    assert "TRUSTED_ARCHIVE_BOUNDARY_INVALID" in source
    assert 'archive_sha256=$(sha256sum "$trusted_archive"' in source
    assert "tar -C" not in source
    assert "archive.incoming" not in source


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
    assert "/var/lib/calculus-discord-deploy/releases/*" in source
    assert "RELEASE_TREE_OWNER_INVALID" in source
    assert '== "$candidate_sha256"' in source
    assert "install -o root -g root -m 0440" not in source
    assert "/etc/calculus-discord" not in source


def test_v13_host_preparer_is_exact_scope_and_never_deploys() -> None:
    source = HOST_PREPARER.read_text(encoding="utf-8")
    assert "PREPARE_V13_HOST:-" in source
    assert "PRODUCTION_DATABASE_V6_INVALID" in source
    assert "--expected-source-schema 6 --expected-target-schema 13" in source
    assert "BOT_OWNER_IDS" in source
    assert "trusted_release_root=/var/lib/calculus-discord-deploy/releases" in source
    assert "RELEASE_TREE_OWNER_INVALID" in source
    assert 'value.get("candidateCommit")' in source
    assert 'value.get("archiveSha256")' in source
    assert 'value.get("treeSha256")' in source
    assert "preflight_root=/var/lib/calculus-discord-deploy/preflight" in source
    assert "runtime_env_owner_action=HARDEN_REQUIRED" in source
    assert "RUNTIME_ENV_HARDEN_FAILED" in source
    assert "mktemp" in source
    assert "runuser" in source
    assert "v13_host_prepare=PASS" in source
    assert "deploy_executed=NO" in source
    assert "systemctl stop" not in source
    assert "systemctl start" not in source
    assert "sudo -n /usr/local/sbin/calculus-discord-deploy" not in source


def test_v13_runbook_uses_interpreter_for_noexec_safe_trusted_copy() -> None:
    source = RUNBOOK.read_text(encoding="utf-8")
    assert '/bin/bash -- "$trusted" "$archive"' in source
    assert '\n  "$trusted" "$archive"' not in source
    assert "jerrymk-workstation" in source


def test_superseded_phase2c_mutators_refuse_before_old_logic() -> None:
    for script in SUPERSEDED_MUTATORS:
        lines = script.read_text(encoding="utf-8").splitlines()
        assert lines[1] == "printf 'phase2c_error=SUPERSEDED_USE_V13_HOST_OWNER_PREPARE\\n' >&2"
        assert lines[2] == "exit 2"


def test_friend_bootstrap_validates_exact_archive_then_only_prepares_host() -> None:
    source = FRIEND_BOOTSTRAP.read_text(encoding="utf-8")
    assert "BOOTSTRAP_V13_RELEASE:-" in source
    assert "PYTHON_VERSION_UNSUPPORTED" in source
    assert "(3, 12) <= sys.version_info[:2] < (3, 15)" in source
    assert "ARCHIVE_PATH_REFUSED" in source
    assert "os.O_NOFOLLOW" in source
    assert "hashlib.file_digest" in source
    assert 'bundle.pax_headers.get("comment"' in source
    assert 'bundle.extractall(stage, filter="data")' in source
    assert "/run/v13-bootstrap.*/v13-friend-bootstrap.sh" in source
    assert "UNTRUSTED_BOOTSTRAP_PATH" in source
    assert "UNTRUSTED_BOOTSTRAP_FILE" in source
    assert "UNTRUSTED_BOOTSTRAP_PARENT" in source
    assert "trusted_root=/var/lib/calculus-discord-deploy" in source
    assert "EXTRACTED_OWNER_INVALID" in source
    assert "treeSha256" in source
    assert "ALREADY_STAGED" in source
    assert "chown -R ding:ding" not in source
    assert "/home/ding/calculus-discord-staging/releases" not in source
    assert "PREPARE_V13_HOST=PREPARE-V13-HOST" in source
    assert "if ! PREPARE_V13_HOST=" in source
    assert "fail HOST_PREPARE_FAILED" in source
    assert "deploy_executed=NO" in source
    assert "systemctl stop" not in source
    assert "systemctl start" not in source
    assert "/usr/local/sbin/calculus-discord-deploy" not in source


def _embedded_stage_validator(tmp_path: Path) -> Path:
    source = FRIEND_BOOTSTRAP.read_text(encoding="utf-8")
    marker = "<<'PY' ||\n  fail ARCHIVE_OR_STAGE_VALIDATION_FAILED\n"
    body = source.split(marker, maxsplit=1)[1].split("\nPY\n", maxsplit=1)[0]
    helper = tmp_path / "stage_validator.py"
    helper.write_text(body, encoding="utf-8")
    return helper


def _fixture_release_archive(tmp_path: Path) -> tuple[Path, str, str]:
    release_id = "a" * 12
    commit = release_id + "b" * 28
    source = tmp_path / "source"
    script = source / "ops/scripts/v13-host-owner-prepare.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\nprintf 'safe\\n'\n", encoding="utf-8")
    script.chmod(0o775)
    readme = source / "README.md"
    readme.write_text("fixture\n", encoding="utf-8")
    readme.chmod(0o664)
    archive = tmp_path / f"v13-release-{release_id}.tar"
    with tarfile.open(
        archive, "w", format=tarfile.PAX_FORMAT, pax_headers={"comment": commit}
    ) as bundle:
        for path in sorted(source.rglob("*")):
            bundle.add(path, arcname=path.relative_to(source), recursive=False)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    return archive, digest, release_id


def test_embedded_stage_validator_normalizes_modes_and_resumes_exact_tree(tmp_path: Path) -> None:
    helper = _embedded_stage_validator(tmp_path)
    archive, digest, release_id = _fixture_release_archive(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)
    args = [
        sys.executable,
        str(helper),
        str(archive),
        str(stage),
        digest,
        release_id,
        "STAGE_NEW",
        ".v13-stage-receipt.json",
        ".v13-source-archive.tar",
    ]
    subprocess.run(args, check=True)
    assert (stage / "README.md").stat().st_mode & 0o777 == 0o644
    assert (stage / "ops/scripts/v13-host-owner-prepare.sh").stat().st_mode & 0o777 == 0o755
    receipt = stage / ".v13-stage-receipt.json"
    assert receipt.stat().st_mode & 0o777 == 0o600
    trusted_archive = stage / ".v13-source-archive.tar"
    assert trusted_archive.stat().st_mode & 0o777 == 0o444
    assert hashlib.sha256(trusted_archive.read_bytes()).hexdigest() == digest

    args[-3] = "ALREADY_STAGED"
    subprocess.run(args, check=True)


def test_embedded_stage_validator_refuses_modified_resumed_tree(tmp_path: Path) -> None:
    helper = _embedded_stage_validator(tmp_path)
    archive, digest, release_id = _fixture_release_archive(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)
    args = [
        sys.executable,
        str(helper),
        str(archive),
        str(stage),
        digest,
        release_id,
        "STAGE_NEW",
        ".v13-stage-receipt.json",
        ".v13-source-archive.tar",
    ]
    subprocess.run(args, check=True)
    (stage / "README.md").write_text("tampered\n", encoding="utf-8")
    args[-3] = "ALREADY_STAGED"
    assert subprocess.run(args, check=False).returncode != 0
