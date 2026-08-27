#!/usr/bin/env bash
set -euo pipefail
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
LC_ALL=C
export LC_ALL
IFS=$' \t\n'
umask 077
unset BASH_ENV ENV PYTHONHOME PYTHONPATH PIP_CONFIG_FILE

source_release=${1:-}
installed_deployer=/usr/local/sbin/calculus-discord-deploy
installed_sudoers=/etc/sudoers.d/calculus-discord-deploy
database=/var/lib/calculus-discord/runtime.sqlite3
trusted_release_root=/var/lib/calculus-discord-deploy/releases
preflight_root=/var/lib/calculus-discord-deploy/preflight
rollback_root=/var/lib/calculus-discord-deploy/rollback
stage_receipt_name=.v13-stage-receipt.json
expected_old_deployer_sha256=05f6375160579374c5341395b53148506c616bcd43743e3ff4d2977ea521d2b6
expected_old_hotfix_deployer_sha256=f1ebe3a301ddb93f15af392a72aeb6ccc223c03d1a427005a3325d69b19f2971
units=(
  calculus-course-assistant.service
  calculus-dump-bot.service
  calculus-data-bridge.service
)

fail() {
  printf 'v13_host_prepare=FAIL\nsafe_error_code=%s\ndeploy_executed=NO\n' "$1" >&2
  exit 2
}

[[ ${EUID} -eq 0 ]] || fail ROOT_REQUIRED
[[ $# -eq 1 ]] || fail ARGUMENTS_INVALID
[[ ${PREPARE_V13_HOST:-} == PREPARE-V13-HOST ]] || fail EXACT_APPROVAL_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST

for command in awk basename bash chmod chown cmp cut date df env find getent head hostname id install ln \
  mktemp mv python3 readlink realpath rm runuser sha256sum sleep sqlite3 stat systemctl visudo wc; do
  command -v "$command" >/dev/null 2>&1 || fail "COMMAND_MISSING_${command^^}"
done
id ding >/dev/null 2>&1 || fail DEPLOY_USER_MISSING

source_release=$(realpath -e "$source_release")
[[ $source_release == "$trusted_release_root"/* ]] ||
  fail RELEASE_PATH_REFUSED
[[ $(stat -c %U:%G "$trusted_release_root") == root:root ]] || fail RELEASE_ROOT_OWNER_INVALID
[[ -z $(find "$trusted_release_root" -maxdepth 0 -perm /022 -print -quit) ]] ||
  fail RELEASE_ROOT_WRITABLE_BY_OTHERS
for secure_root in "$preflight_root" "$rollback_root"; do
  if [[ -e $secure_root ]]; then
    [[ -d $secure_root && ! -L $secure_root ]] || fail SECURE_ARTIFACT_ROOT_INVALID
    [[ $(stat -c %U:%G "$secure_root") == root:root ]] || fail SECURE_ARTIFACT_ROOT_OWNER_INVALID
    [[ -z $(find "$secure_root" -maxdepth 0 -perm /022 -print -quit) ]] ||
      fail SECURE_ARTIFACT_ROOT_WRITABLE_BY_OTHERS
  else
    install -d -o root -g root -m 0700 "$secure_root"
  fi
done
[[ $(stat -c %U:%G "$source_release") == root:root ]] || fail RELEASE_OWNER_INVALID
[[ -z $(find "$source_release" ! -user root -print -quit) ]] || fail RELEASE_TREE_OWNER_INVALID
[[ -z $(find "$source_release" -perm /022 -print -quit) ]] || fail RELEASE_WRITABLE_BY_OTHERS
release_id=$(basename "$source_release")
[[ $release_id =~ ^[a-f0-9]{12}$ ]] || fail RELEASE_ID_INVALID
stage_receipt=$source_release/$stage_receipt_name
[[ -f $stage_receipt && ! -L $stage_receipt ]] || fail STAGE_RECEIPT_MISSING
[[ $(stat -c %U:%G "$stage_receipt") == root:root && $(stat -c %a "$stage_receipt") == 600 ]] ||
  fail STAGE_RECEIPT_BOUNDARY_INVALID
stage_binding_output=$(python3 -I - "$stage_receipt" "$release_id" <<'PY'
import json
from pathlib import Path
import re
import sys

value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
release_id = sys.argv[2]
sha256 = re.compile(r"^[a-f0-9]{64}$")
commit = str(value.get("commit", ""))
if not (
    value.get("status") == "PASS"
    and value.get("releaseId") == release_id
    and len(commit) == 40
    and commit.startswith(release_id)
    and sha256.fullmatch(str(value.get("archiveSha256", "")))
    and sha256.fullmatch(str(value.get("treeSha256", "")))
):
    raise SystemExit(1)
print(commit)
print(value["archiveSha256"])
print(value["treeSha256"])
PY
) || fail STAGE_RECEIPT_INVALID
mapfile -t stage_binding <<<"$stage_binding_output"
[[ ${#stage_binding[@]} -eq 3 ]] || fail STAGE_RECEIPT_INVALID
candidate_commit=${stage_binding[0]}
archive_sha256=${stage_binding[1]}
tree_sha256=${stage_binding[2]}

deployer_source=$source_release/ops/scripts/calculus-discord-deploy
repairer_source=$source_release/ops/scripts/phase2c-repair-restricted-deployer.sh
rehearsal_source=$source_release/ops/scripts/sqlite-recovery-rehearsal.py
host_prepare_source=$source_release/ops/scripts/v13-host-owner-prepare.sh
sudoers_source=$source_release/ops/sudoers/calculus-discord-deploy
dependency_lock=$source_release/ops/requirements/discord-runtime.txt
runtime_project=$source_release/runtime/discord-course-bots/pyproject.toml
for path in "$deployer_source" "$repairer_source" "$rehearsal_source" \
  "$host_prepare_source" \
  "$sudoers_source" "$dependency_lock" "$runtime_project"; do
  [[ -f $path && ! -L $path ]] || fail RELEASE_CRITICAL_FILE_INVALID
done
bash -n "$deployer_source" || fail DEPLOYER_SOURCE_SYNTAX_INVALID
bash -n "$repairer_source" || fail REPAIRER_SOURCE_SYNTAX_INVALID
[[ -x $repairer_source && -x $host_prepare_source ]] || fail RELEASE_ENTRYPOINT_NOT_EXECUTABLE
visudo -cf "$sudoers_source" >/dev/null || fail SUDOERS_SOURCE_INVALID

[[ -z $(find "$source_release" -type l -print -quit) ]] || fail RELEASE_SYMLINK_REFUSED
[[ -z $(find "$source_release" ! -type f ! -type d -print -quit) ]] ||
  fail RELEASE_SPECIAL_FILE_REFUSED
release_file_count=$(find "$source_release" -type f -printf . | wc -c)
release_bytes=$(find "$source_release" -type f -printf '%s\n' | awk '{sum += $1} END {print sum + 0}')
[[ $release_file_count -le 20000 ]] || fail RELEASE_FILE_COUNT_EXCEEDED
[[ $release_bytes -le 268435456 ]] || fail RELEASE_SIZE_EXCEEDED

python3 -I - "$dependency_lock" <<'PY' || fail DEPENDENCY_LOCK_INVALID
from pathlib import Path
import re
import sys

lines = [
    line.strip()
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
exact_pin = re.compile(r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+$")
if not 1 <= len(lines) <= 100 or any(exact_pin.fullmatch(line) is None for line in lines):
    raise SystemExit(1)
PY

id calculus-bot >/dev/null 2>&1 || fail SERVICE_USER_MISSING
id calculus-builder >/dev/null 2>&1 || fail BUILD_USER_MISSING
[[ $(id -gn calculus-builder) == calculus-builder ]] || fail BUILD_USER_GROUP_INVALID
[[ $(getent passwd calculus-builder | cut -d: -f7) == /usr/sbin/nologin ]] ||
  fail BUILD_USER_SHELL_INVALID
[[ -d /var/lib/calculus-discord-build ]] || fail BUILD_HOME_MISSING
[[ $(stat -c %U:%G /var/lib/calculus-discord-build) == calculus-builder:calculus-builder ]] ||
  fail BUILD_HOME_OWNER_INVALID
[[ $(stat -c %a /var/lib/calculus-discord-build) == 700 ]] || fail BUILD_HOME_MODE_INVALID
[[ -d /var/lib/calculus-discord-deploy ]] || fail DEPLOY_WORK_ROOT_MISSING

[[ -f $installed_deployer && ! -L $installed_deployer ]] || fail DEPLOYER_MISSING
[[ $(stat -c %U:%G "$installed_deployer") == root:root ]] || fail DEPLOYER_OWNER_INVALID
[[ $(stat -c %a "$installed_deployer") == 755 ]] || fail DEPLOYER_MODE_INVALID
[[ -f $installed_sudoers && ! -L $installed_sudoers ]] || fail SUDOERS_RULE_MISSING
[[ $(stat -c %U:%G "$installed_sudoers") == root:root ]] || fail SUDOERS_OWNER_INVALID
[[ $(stat -c %a "$installed_sudoers") == 440 ]] || fail SUDOERS_MODE_INVALID
visudo -cf "$installed_sudoers" >/dev/null || fail SUDOERS_INSTALLED_INVALID
cmp -s "$sudoers_source" "$installed_sudoers" || fail SUDOERS_RULE_MISMATCH

candidate_deployer_sha256=$(sha256sum "$deployer_source" | cut -d' ' -f1)
installed_deployer_sha256=$(sha256sum "$installed_deployer" | cut -d' ' -f1)
if [[ $installed_deployer_sha256 == "$candidate_deployer_sha256" ]]; then
  deployer_action=ALREADY_READY
elif [[ $installed_deployer_sha256 == "$expected_old_deployer_sha256" ||
  $installed_deployer_sha256 == "$expected_old_hotfix_deployer_sha256" ]]; then
  deployer_action=REPAIR_REQUIRED
else
  fail INSTALLED_DEPLOYER_VERSION_REFUSED
fi

[[ -L /opt/calculus-discord/current ]] || fail CURRENT_RELEASE_MISSING
current_release=$(readlink -f /opt/calculus-discord/current)
[[ $current_release == /opt/calculus-discord/releases/* ]] || fail CURRENT_RELEASE_PATH_INVALID
[[ -d $current_release && ! -L $current_release ]] || fail CURRENT_RELEASE_BOUNDARY_INVALID
[[ $(stat -c %U:%G "$current_release") == root:root ]] || fail CURRENT_RELEASE_OWNER_INVALID
[[ -z $(find "$current_release" ! -user root -print -quit) ]] ||
  fail CURRENT_RELEASE_TREE_OWNER_INVALID
[[ -z $(find "$current_release" -perm /022 -print -quit) ]] ||
  fail CURRENT_RELEASE_WRITABLE_BY_OTHERS
[[ -f $database && ! -L $database ]] || fail PRODUCTION_DATABASE_MISSING
[[ $(stat -c %U:%G "$database") == calculus-bot:calculus-bot ]] ||
  fail PRODUCTION_DATABASE_OWNER_INVALID
[[ $(stat -c %a "$database") == 600 ]] || fail PRODUCTION_DATABASE_MODE_INVALID

current_schema=$(python3 -B -I - "$database" "$source_release" <<'PY'
from pathlib import Path
from datetime import UTC, datetime
import sqlite3
import sys

database = Path(sys.argv[1]).resolve()
source = Path(sys.argv[2]).resolve() / "runtime" / "discord-course-bots" / "src"
sys.path.insert(0, str(source))
from discord_course_bots.migrations import MIGRATIONS

connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
try:
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise SystemExit(1)
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise SystemExit(1)
    current_schema = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if current_schema not in {6, 13}:
        raise SystemExit(1)
    actual = connection.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    expected = [
        (item.version, item.name, item.checksum) for item in MIGRATIONS[:current_schema]
    ]
    if actual != expected:
        raise SystemExit(1)
    health = connection.execute(
        "SELECT service_key, status, safe_error_code, checked_at "
        "FROM service_health ORDER BY service_key"
    ).fetchall()
    if [(row[0], row[1], row[2]) for row in health] != [
        ("course-assistant", "HEALTHY", None),
        ("data-bridge", "HEALTHY", None),
        ("dump-bot", "HEALTHY", None),
    ]:
        raise SystemExit(1)
    now = datetime.now(UTC)
    for row in health:
        checked = datetime.fromisoformat(str(row[3]))
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=UTC)
        age = (now - checked.astimezone(UTC)).total_seconds()
        if age < -60 or age > 300:
            raise SystemExit(1)
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    failures = 0
    for table in (
        "discord_lifecycle_jobs",
        "discord_dm_outbox",
        "course_role_jobs",
        "private_open_requests",
        "email_delivery_outbox",
        "projection_outbox",
    ):
        if table in tables:
            failures += int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {table} "
                    "WHERE status IN ('RETRYABLE_FAILURE', 'PERMANENT_FAILURE')"
                ).fetchone()[0]
            )
    if "private_dump_jobs" in tables:
        failures += int(
            connection.execute(
                "SELECT COUNT(*) FROM private_dump_jobs WHERE status = 'FAILED'"
            ).fetchone()[0]
        )
    if failures:
        raise SystemExit(1)
    print(current_schema)
finally:
    connection.close()
PY
) || fail PRODUCTION_DATABASE_SCHEMA_INVALID
[[ $current_schema == 6 || $current_schema == 13 ]] ||
  fail PRODUCTION_DATABASE_SCHEMA_INVALID
if [[ $current_schema == 6 ]]; then
  migration_class=ADDITIVE
else
  migration_class=NONE
fi

for unit in "${units[@]}"; do
  [[ $(systemctl is-active "$unit" 2>/dev/null) == active ]] ||
    fail REMOTE_SERVICE_NOT_ACTIVE
  [[ $(systemctl is-enabled "$unit" 2>/dev/null) == enabled ]] ||
    fail REMOTE_SERVICE_NOT_ENABLED
  [[ $(systemctl show -p User --value "$unit" 2>/dev/null) == calculus-bot ]] ||
    fail REMOTE_SERVICE_USER_INVALID
done

runtime_env_owner_action=ALREADY_ROOT_OWNED
for env_file in /etc/calculus-discord/course-assistant.env \
  /etc/calculus-discord/dump-bot.env /etc/calculus-discord/data-bridge.env; do
  [[ -f $env_file && ! -L $env_file ]] || fail RUNTIME_ENV_MISSING
  env_owner=$(stat -c %U:%G "$env_file")
  if [[ $env_owner == calculus-bot:calculus-bot ]]; then
    runtime_env_owner_action=HARDEN_REQUIRED
  elif [[ $env_owner != root:root ]]; then
    fail RUNTIME_ENV_OWNER_INVALID
  fi
  [[ $(stat -c %a "$env_file") == 600 ]] || fail RUNTIME_ENV_MODE_INVALID
done

python3 -I - <<'PY' || fail RUNTIME_ENV_INVALID
from pathlib import Path
import pwd
import shlex


def values(path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed = shlex.split(value, comments=True)
        result[key.strip()] = " ".join(parsed).strip()
    return result


course = values("/etc/calculus-discord/course-assistant.env")
dump = values("/etc/calculus-discord/dump-bot.env")
bridge = values("/etc/calculus-discord/data-bridge.env")
required = (
    (course, ("COURSE_ASSISTANT_TOKEN", "TEST_GUILD_ID", "BOT_OWNER_IDS", "DATABASE_PATH")),
    (dump, ("DUMP_BOT_TOKEN", "TEST_GUILD_ID", "DATABASE_PATH")),
    (
        bridge,
        ("GAS_DEPLOYMENT_ID", "GOOGLE_OAUTH_CREDENTIALS", "SHEET_FINGERPRINT", "DATABASE_PATH"),
    ),
)
if any(not mapping.get(key, "").strip() for mapping, keys in required for key in keys):
    raise SystemExit(1)
expected_database = "/var/lib/calculus-discord/runtime.sqlite3"
if {course["DATABASE_PATH"], dump["DATABASE_PATH"], bridge["DATABASE_PATH"]} != {
    expected_database
}:
    raise SystemExit(1)
if course["TEST_GUILD_ID"] != dump["TEST_GUILD_ID"]:
    raise SystemExit(1)


def positive_integer(value: str) -> bool:
    try:
        return int(value) > 0
    except ValueError:
        return False


if not positive_integer(course["TEST_GUILD_ID"]):
    raise SystemExit(1)
owners = [part.strip() for part in course["BOT_OWNER_IDS"].split(",") if part.strip()]
if not owners or any(not positive_integer(owner) for owner in owners):
    raise SystemExit(1)
for mapping, optional_ids in (
    (course, ("COURSE_ASSISTANT_CLIENT_ID", "DUMP_BOT_CLIENT_ID")),
    (dump, ("DUMP_BOT_CLIENT_ID",)),
):
    if any(mapping.get(key) and not positive_integer(mapping[key]) for key in optional_ids):
        raise SystemExit(1)

try:
    reminder = int(course.get("DRAFT_REMINDER_SECONDS", "86400"))
    delete = int(course.get("DRAFT_DELETE_SECONDS", "172800"))
    idle = int(course.get("CASE_IDLE_SECONDS", "172800"))
    auto_close = int(course.get("CASE_AUTO_CLOSE_SECONDS", "172800"))
    capacity = int(course.get("PRIVATE_OPEN_CAPACITY", "50"))
    bridge_interval = int(bridge.get("BRIDGE_INTERVAL_SECONDS", "60"))
except ValueError:
    raise SystemExit(1) from None
if not (0 < reminder < delete and idle > 0 and auto_close > 0 and capacity > 0):
    raise SystemExit(1)
if not 30 <= bridge_interval <= 300:
    raise SystemExit(1)
if bridge.get("BRIDGE_ENVIRONMENT", "STAGING").upper() != "PRODUCTION":
    raise SystemExit(1)
if bridge.get("BRIDGE_SYNTHETIC_ONLY", "0") != "0":
    raise SystemExit(1)
credential = Path(bridge["GOOGLE_OAUTH_CREDENTIALS"])
if (
    not credential.is_absolute()
    or not credential.is_file()
    or credential.is_symlink()
):
    raise SystemExit(1)
credential_metadata = credential.stat()
if (
    credential_metadata.st_mode & 0o077
    or credential_metadata.st_uid != pwd.getpwnam("calculus-bot").pw_uid
):
    raise SystemExit(1)
PY

inbox=/home/ding/calculus-discord-staging/deploy-inbox
[[ ! -e $inbox/request.txt && ! -e $inbox/release.tar ]] || fail DEPLOY_INBOX_NOT_EMPTY
[[ ! -e /opt/calculus-discord/current.incoming ]] || fail CURRENT_INCOMING_PRESENT
[[ ! -e /opt/calculus-discord/current.rollback ]] || fail CURRENT_ROLLBACK_PRESENT
[[ ! -e /opt/calculus-discord/releases/$release_id ]] || fail RELEASE_ALREADY_PRESENT
[[ ! -e /opt/calculus-discord/releases/$release_id.incoming ]] ||
  fail RELEASE_INCOMING_PRESENT
[[ ! -e $rollback_root/$release_id ]] || fail DEPLOY_ROLLBACK_ARTIFACT_PRESENT

for filesystem in /home/ding/calculus-discord-staging /opt/calculus-discord \
  /var/lib/calculus-discord /var/lib/calculus-discord-deploy; do
  available_kib=$(df -Pk "$filesystem" | awk 'NR == 2 {print $4}')
  available_inodes=$(df -Pi "$filesystem" | awk 'NR == 2 {print $4}')
  [[ $available_kib =~ ^[0-9]+$ && $available_kib -ge 1048576 ]] ||
    fail DISK_SPACE_INSUFFICIENT
  [[ $available_inodes =~ ^[0-9]+$ && $available_inodes -ge 10000 ]] ||
    fail DISK_INODES_INSUFFICIENT
done

if [[ $runtime_env_owner_action == HARDEN_REQUIRED ]]; then
  chown root:root /etc/calculus-discord/course-assistant.env \
    /etc/calculus-discord/dump-bot.env /etc/calculus-discord/data-bridge.env
  for env_file in /etc/calculus-discord/course-assistant.env \
    /etc/calculus-discord/dump-bot.env /etc/calculus-discord/data-bridge.env; do
    [[ $(stat -c %U:%G "$env_file") == root:root && $(stat -c %a "$env_file") == 600 ]] ||
      fail RUNTIME_ENV_HARDEN_FAILED
  done
  runtime_env_owner_action=HARDENED
fi

if [[ $deployer_action == REPAIR_REQUIRED ]]; then
  REPAIR_CALCULUS_DEPLOYER=REPAIR-CALCULUS-DEPLOYER \
    /bin/bash -- "$repairer_source" "$source_release" >/dev/null
fi
[[ $(sha256sum "$installed_deployer" | cut -d' ' -f1) == "$candidate_deployer_sha256" ]] ||
  fail DEPLOYER_NOT_READY_AFTER_REPAIR

preflight_bundle=$preflight_root/$release_id
preflight_incoming=$preflight_bundle.incoming
work_root=$preflight_incoming/work
backup=$preflight_bundle/backup.sqlite3
receipt=$preflight_bundle/receipt.json
if [[ -e $preflight_bundle ]]; then
  [[ -d $preflight_bundle && ! -L $preflight_bundle ]] || fail PREFLIGHT_BUNDLE_INVALID
  [[ $(stat -c %U:%G "$preflight_bundle") == root:root && \
    $(stat -c %a "$preflight_bundle") == 700 ]] || fail PREFLIGHT_BUNDLE_BOUNDARY_INVALID
  [[ -f $backup && ! -L $backup && -f $receipt && ! -L $receipt ]] ||
    fail PREFLIGHT_BUNDLE_INCOMPLETE
  [[ $(stat -c %U:%G "$backup") == root:root && $(stat -c %a "$backup") == 600 ]] ||
    fail PREFLIGHT_BACKUP_BOUNDARY_INVALID
  [[ $(stat -c %U:%G "$receipt") == root:root && $(stat -c %a "$receipt") == 600 ]] ||
    fail PREFLIGHT_RECEIPT_BOUNDARY_INVALID
  if ! python3 -I - "$backup" "$receipt" "$release_id" "$candidate_deployer_sha256" \
    "$candidate_commit" "$archive_sha256" "$tree_sha256" "$current_schema" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

backup, receipt = Path(sys.argv[1]), Path(sys.argv[2])
value = json.loads(receipt.read_text(encoding="utf-8"))
digest = hashlib.sha256(backup.read_bytes()).hexdigest()
if not (
    value.get("status") == "PASS"
    and value.get("releaseId") == sys.argv[3]
    and value.get("candidateDeployerSha256") == sys.argv[4]
    and value.get("candidateCommit") == sys.argv[5]
    and value.get("archiveSha256") == sys.argv[6]
    and value.get("treeSha256") == sys.argv[7]
    and value.get("expectedSourceSchemaVersion") == int(sys.argv[8])
    and value.get("expectedTargetSchemaVersion") == 13
    and value.get("backupSha256") == digest
    and value.get("productionDatabaseModified") is False
    and value.get("deployExecuted") is False
    and value.get("sensitiveValuesPrinted") is False
):
    raise SystemExit(1)
PY
  then
    fail PREFLIGHT_ARTIFACT_INVALID
  fi
  printf 'v13_host_prepare=ALREADY_READY\nbackup_rehearsal=PASS\n'
  printf 'source_schema=%s\ntarget_schema=13\nmigration_class=%s\n' \
    "$current_schema" "$migration_class"
  printf 'deployer=READY\nruntime_env_ownership=%s\n' "$runtime_env_owner_action"
  printf 'production_database_modified=NO\ndeploy_executed=NO\n'
  exit 0
fi

[[ ! -e $preflight_incoming ]] || fail PREFLIGHT_INCOMING_PRESENT
install -d -o root -g root -m 0700 "$preflight_incoming" "$work_root"
backup_incoming=$preflight_incoming/backup.sqlite3
raw_receipt=$preflight_incoming/rehearsal.raw.json
receipt_incoming=$preflight_incoming/receipt.json
cleanup_prepare() {
  local result=$?
  if [[ $result -ne 0 && -d $preflight_incoming ]]; then
    rm -rf -- "$preflight_incoming"
  fi
  return "$result"
}
trap cleanup_prepare EXIT

sqlite3 "$database" ".backup '$backup_incoming'"
chmod 0600 "$backup_incoming"
[[ $(sqlite3 "$backup_incoming" 'PRAGMA integrity_check;') == ok ]] ||
  fail PREFLIGHT_BACKUP_INTEGRITY_FAILED
python3 -B -I "$rehearsal_source" "$backup_incoming" "$work_root" \
  --expected-source-schema "$current_schema" --expected-target-schema 13 >"$raw_receipt" ||
  fail RECOVERY_REHEARSAL_FAILED
chmod 0600 "$raw_receipt"

python3 -I - "$raw_receipt" "$backup_incoming" "$receipt_incoming" "$release_id" \
  "$candidate_deployer_sha256" "$candidate_commit" "$archive_sha256" \
  "$tree_sha256" <<'PY' || fail RECOVERY_RECEIPT_INVALID
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import sys

raw, backup, destination = map(Path, sys.argv[1:4])
value = json.loads(raw.read_text(encoding="utf-8"))
if value.get("status") != "PASS":
    raise SystemExit(1)
value.update(
    {
        "releaseId": sys.argv[4],
        "candidateDeployerSha256": sys.argv[5],
        "candidateCommit": sys.argv[6],
        "archiveSha256": sys.argv[7],
        "treeSha256": sys.argv[8],
        "backupSha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        "observedAt": datetime.now(UTC).isoformat(),
        "productionDatabaseModified": False,
        "deployExecuted": False,
        "sensitiveValuesPrinted": False,
    }
)
destination.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
destination.chmod(0o600)
PY

rm -f -- "$raw_receipt"
mv "$preflight_incoming" "$preflight_bundle"
trap - EXIT
printf 'v13_host_prepare=PASS\nbackup_rehearsal=PASS\ndeployer=READY\n'
printf 'source_schema=%s\ntarget_schema=13\nmigration_class=%s\n' \
  "$current_schema" "$migration_class"
printf 'runtime_env_ownership=%s\n' "$runtime_env_owner_action"
printf 'production_database_modified=NO\ndeploy_executed=NO\n'
