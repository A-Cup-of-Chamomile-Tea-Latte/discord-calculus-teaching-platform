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
expected_old_deployer_sha256=05f6375160579374c5341395b53148506c616bcd43743e3ff4d2977ea521d2b6
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

for command in awk bash chmod cmp cut df find getent hostname id install mv python3 readlink \
  realpath rm sha256sum sqlite3 stat systemctl visudo wc; do
  command -v "$command" >/dev/null 2>&1 || fail "COMMAND_MISSING_${command^^}"
done
id ding >/dev/null 2>&1 || fail DEPLOY_USER_MISSING

source_release=$(realpath -e "$source_release")
[[ $source_release == /home/ding/calculus-discord-staging/releases/* ]] ||
  fail RELEASE_PATH_REFUSED
[[ $(stat -c %U:%G "$source_release") == ding:ding ]] || fail RELEASE_OWNER_INVALID
[[ -z $(find "$source_release" -perm /022 -print -quit) ]] || fail RELEASE_WRITABLE_BY_OTHERS
release_id=$(basename "$source_release")
[[ $release_id =~ ^[a-f0-9]{7,40}$ ]] || fail RELEASE_ID_INVALID

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

python3 - "$dependency_lock" <<'PY' || fail DEPENDENCY_LOCK_INVALID
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
elif [[ $installed_deployer_sha256 == "$expected_old_deployer_sha256" ]]; then
  deployer_action=REPAIR_REQUIRED
else
  fail INSTALLED_DEPLOYER_VERSION_REFUSED
fi

[[ -L /opt/calculus-discord/current ]] || fail CURRENT_RELEASE_MISSING
current_release=$(readlink -f /opt/calculus-discord/current)
[[ $current_release == /opt/calculus-discord/releases/* ]] || fail CURRENT_RELEASE_PATH_INVALID
[[ -f $database && ! -L $database ]] || fail PRODUCTION_DATABASE_MISSING
[[ $(stat -c %U:%G "$database") == calculus-bot:calculus-bot ]] ||
  fail PRODUCTION_DATABASE_OWNER_INVALID
[[ $(stat -c %a "$database") == 600 ]] || fail PRODUCTION_DATABASE_MODE_INVALID

python3 - "$database" "$source_release" <<'PY' || fail PRODUCTION_DATABASE_V6_INVALID
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
    if connection.execute("PRAGMA user_version").fetchone()[0] != 6:
        raise SystemExit(1)
    actual = connection.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    expected = [(item.version, item.name, item.checksum) for item in MIGRATIONS[:6]]
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
    failures = (
        connection.execute(
            "SELECT COUNT(*) FROM discord_lifecycle_jobs "
            "WHERE status IN ('RETRYABLE_FAILURE', 'PERMANENT_FAILURE')"
        ).fetchone()[0]
        + connection.execute(
            "SELECT COUNT(*) FROM projection_outbox "
            "WHERE status IN ('RETRYABLE_FAILURE', 'PERMANENT_FAILURE')"
        ).fetchone()[0]
        + connection.execute(
            "SELECT COUNT(*) FROM private_dump_jobs WHERE status = 'FAILED'"
        ).fetchone()[0]
    )
    if failures:
        raise SystemExit(1)
finally:
    connection.close()
PY

for unit in "${units[@]}"; do
  [[ $(systemctl is-active "$unit" 2>/dev/null) == active ]] ||
    fail REMOTE_SERVICE_NOT_ACTIVE
  [[ $(systemctl is-enabled "$unit" 2>/dev/null) == enabled ]] ||
    fail REMOTE_SERVICE_NOT_ENABLED
  [[ $(systemctl show -p User --value "$unit" 2>/dev/null) == calculus-bot ]] ||
    fail REMOTE_SERVICE_USER_INVALID
done

for env_file in /etc/calculus-discord/course-assistant.env \
  /etc/calculus-discord/dump-bot.env /etc/calculus-discord/data-bridge.env; do
  [[ -f $env_file && ! -L $env_file ]] || fail RUNTIME_ENV_MISSING
  [[ $(stat -c %U:%G "$env_file") == root:root ]] || fail RUNTIME_ENV_OWNER_INVALID
  [[ $(stat -c %a "$env_file") == 600 ]] || fail RUNTIME_ENV_MODE_INVALID
done

python3 - <<'PY' || fail RUNTIME_ENV_REQUIRED_VALUE_MISSING
from pathlib import Path
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
if course["DATABASE_PATH"] != dump["DATABASE_PATH"] or course["DATABASE_PATH"] != bridge["DATABASE_PATH"]:
    raise SystemExit(1)
credential = Path(bridge["GOOGLE_OAUTH_CREDENTIALS"])
if not credential.is_file() or credential.is_symlink() or credential.stat().st_mode & 0o077:
    raise SystemExit(1)
PY

inbox=/home/ding/calculus-discord-staging/deploy-inbox
[[ ! -e $inbox/request.txt && ! -e $inbox/release.tar ]] || fail DEPLOY_INBOX_NOT_EMPTY
[[ ! -e /opt/calculus-discord/current.incoming ]] || fail CURRENT_INCOMING_PRESENT
[[ ! -e /opt/calculus-discord/current.rollback ]] || fail CURRENT_ROLLBACK_PRESENT
[[ ! -e /opt/calculus-discord/releases/$release_id ]] || fail RELEASE_ALREADY_PRESENT
[[ ! -e /opt/calculus-discord/releases/$release_id.incoming ]] ||
  fail RELEASE_INCOMING_PRESENT
[[ ! -e /var/lib/calculus-discord/backups/deploy-$release_id.before.sqlite3 ]] ||
  fail DEPLOY_ROLLBACK_ARTIFACT_PRESENT
[[ ! -e /var/lib/calculus-discord/receipts/deploy-$release_id.txt ]] ||
  fail DEPLOY_RECEIPT_PRESENT

for filesystem in /home/ding/calculus-discord-staging /opt/calculus-discord \
  /var/lib/calculus-discord; do
  available_kib=$(df -Pk "$filesystem" | awk 'NR == 2 {print $4}')
  available_inodes=$(df -Pi "$filesystem" | awk 'NR == 2 {print $4}')
  [[ $available_kib =~ ^[0-9]+$ && $available_kib -ge 1048576 ]] ||
    fail DISK_SPACE_INSUFFICIENT
  [[ $available_inodes =~ ^[0-9]+$ && $available_inodes -ge 10000 ]] ||
    fail DISK_INODES_INSUFFICIENT
done

if [[ $deployer_action == REPAIR_REQUIRED ]]; then
  REPAIR_CALCULUS_DEPLOYER=REPAIR-CALCULUS-DEPLOYER \
    "$repairer_source" "$source_release" >/dev/null
fi
[[ $(sha256sum "$installed_deployer" | cut -d' ' -f1) == "$candidate_deployer_sha256" ]] ||
  fail DEPLOYER_NOT_READY_AFTER_REPAIR

backup_root=/var/lib/calculus-discord/backups
receipt_root=/var/lib/calculus-discord/receipts
work_root=/var/lib/calculus-discord/staging/v13-$release_id
backup=$backup_root/v13-preflight-$release_id.sqlite3
receipt=$receipt_root/v13-preflight-$release_id.json
if [[ -e $backup || -e $receipt ]]; then
  [[ -f $backup && ! -L $backup && -f $receipt && ! -L $receipt ]] ||
    fail PREFLIGHT_ARTIFACT_PARTIAL
  [[ $(stat -c %U:%G "$backup") == root:root && $(stat -c %a "$backup") == 600 ]] ||
    fail PREFLIGHT_BACKUP_BOUNDARY_INVALID
  [[ $(stat -c %U:%G "$receipt") == root:root && $(stat -c %a "$receipt") == 600 ]] ||
    fail PREFLIGHT_RECEIPT_BOUNDARY_INVALID
  python3 - "$backup" "$receipt" "$release_id" "$candidate_deployer_sha256" <<'PY' ||
    fail PREFLIGHT_ARTIFACT_INVALID
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
    and value.get("backupSha256") == digest
):
    raise SystemExit(1)
PY
  printf 'v13_host_prepare=ALREADY_READY\nbackup_rehearsal=PASS\n'
  printf 'deployer=READY\ndeploy_executed=NO\n'
  exit 0
fi

install -d -o root -g root -m 0700 "$backup_root" "$receipt_root" "$work_root"
backup_incoming=$backup.incoming
raw_receipt=$receipt.incoming.raw
receipt_incoming=$receipt.incoming
cleanup_prepare() {
  local result=$?
  rm -f -- "$backup_incoming" "$raw_receipt" "$receipt_incoming"
  return "$result"
}
trap cleanup_prepare EXIT

sqlite3 "$database" ".backup '$backup_incoming'"
chmod 0600 "$backup_incoming"
[[ $(sqlite3 "$backup_incoming" 'PRAGMA integrity_check;') == ok ]] ||
  fail PREFLIGHT_BACKUP_INTEGRITY_FAILED
python3 "$rehearsal_source" "$backup_incoming" "$work_root" \
  --expected-source-schema 6 --expected-target-schema 13 >"$raw_receipt" ||
  fail RECOVERY_REHEARSAL_FAILED
chmod 0600 "$raw_receipt"

python3 - "$raw_receipt" "$backup_incoming" "$receipt_incoming" "$release_id" \
  "$candidate_deployer_sha256" <<'PY' || fail RECOVERY_RECEIPT_INVALID
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

mv "$backup_incoming" "$backup"
mv "$receipt_incoming" "$receipt"
rm -f -- "$raw_receipt"
trap - EXIT
printf 'v13_host_prepare=PASS\nbackup_rehearsal=PASS\ndeployer=READY\n'
printf 'production_database_modified=NO\ndeploy_executed=NO\n'
