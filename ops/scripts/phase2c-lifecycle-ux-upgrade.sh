#!/usr/bin/env bash
set -euo pipefail

release_source=${1:-}
runtime_lock=${2:-}

fail() {
  printf 'upgrade_error=%s\n' "$1" >&2
  exit 2
}

[[ ${EUID} -eq 0 ]] || fail ROOT_REQUIRED
[[ ${APPLY_LIFECYCLE_UX:-} == APPLY-LIFECYCLE-UX ]] || fail EXACT_APPROVAL_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST

release_source=$(realpath -e "$release_source")
runtime_lock=$(realpath -e "$runtime_lock")
[[ $release_source == /home/ding/calculus-discord-staging/releases/* ]] ||
  fail RELEASE_PATH_REFUSED
[[ $runtime_lock == /home/ding/calculus-discord-staging/cutover-ready/*/runtime-requirements.txt ]] ||
  fail RUNTIME_LOCK_PATH_REFUSED

release_id=$(basename "$release_source")
[[ $release_id =~ ^[a-f0-9]{7,40}$ ]] || fail RELEASE_ID_INVALID
release_destination="/opt/calculus-discord/releases/$release_id"
incoming="$release_destination.incoming"
runtime="$release_destination/runtime/discord-course-bots"
database=/var/lib/calculus-discord/runtime.sqlite3
staging_database="/var/lib/calculus-discord/staging/lifecycle-ux-$release_id.sqlite3"
rollback_database="/var/lib/calculus-discord/backups/lifecycle-ux-$release_id.before.sqlite3"
receipt="/var/lib/calculus-discord/receipts/lifecycle-ux-$release_id.txt"
units=(
  calculus-course-assistant.service
  calculus-dump-bot.service
  calculus-data-bridge.service
)

[[ -L /opt/calculus-discord/current ]] || fail CURRENT_RELEASE_MISSING
old_release=$(readlink -f /opt/calculus-discord/current)
[[ $old_release == /opt/calculus-discord/releases/* ]] || fail CURRENT_RELEASE_PATH_INVALID
[[ $old_release != "$release_destination" ]] || fail RELEASE_ALREADY_CURRENT
[[ ! -e $release_destination && ! -e $incoming ]] || fail RELEASE_ALREADY_PRESENT
[[ ! -e /opt/calculus-discord/current.rollback ]] || fail ROLLBACK_LINK_PRESENT
[[ -f $database ]] || fail PRODUCTION_DATABASE_MISSING
[[ ! -e $staging_database && ! -e $rollback_database && ! -e $receipt ]] ||
  fail UPGRADE_ARTIFACT_ALREADY_PRESENT
[[ $(sqlite3 "$database" 'PRAGMA integrity_check;') == ok ]] ||
  fail PRODUCTION_DATABASE_INTEGRITY_FAILED
[[ $(sqlite3 "$database" 'PRAGMA user_version;') == 5 ]] ||
  fail PRODUCTION_DATABASE_SCHEMA_INVALID
[[ $(sqlite3 "$database" 'SELECT COUNT(*) FROM schema_migrations;') == 5 ]] ||
  fail PRODUCTION_DATABASE_LEDGER_INVALID
for unit in "${units[@]}"; do
  [[ $(systemctl is-active "$unit" 2>/dev/null || true) == active ]] ||
    fail REMOTE_SERVICE_NOT_ACTIVE
done

cleanup_preflight() {
  local status=$?
  if [[ -e $staging_database ]]; then
    rm -f -- "$staging_database"
  fi
  if [[ $status -ne 0 ]]; then
    if [[ -d $incoming ]]; then
      rm -rf -- "$incoming"
    fi
    if [[ -d $release_destination ]]; then
      rm -rf -- "$release_destination"
    fi
  fi
}
trap cleanup_preflight EXIT

install -d -o root -g root -m 0755 "$incoming"
tar -C "$release_source" --exclude='./runtime/discord-course-bots/.venv' -cf - . |
  tar -C "$incoming" -xf -
mv "$incoming" "$release_destination"
python3 -m venv "$runtime/.venv"
"$runtime/.venv/bin/pip" install -r "$runtime_lock" >/dev/null
"$runtime/.venv/bin/pip" install --no-deps "$runtime" >/dev/null
for executable in course-assistant dump-bot discord-production-bridge; do
  [[ -x $runtime/.venv/bin/$executable ]] || fail RELEASE_EXECUTABLE_MISSING
done
chown -R root:root "$release_destination"
chmod -R go-w "$release_destination"

sqlite3 "$database" ".backup '$staging_database'"
chmod 0600 "$staging_database"
"$runtime/.venv/bin/python" - "$staging_database" <<'PY'
from pathlib import Path
import sys

from discord_course_bots.repository import Repository

repository = Repository(Path(sys.argv[1]))
try:
    if repository.schema_version != 6 or len(repository.migration_history()) != 6:
        raise SystemExit("staging migration mismatch")
finally:
    repository.close()
PY
[[ $(sqlite3 "$staging_database" 'PRAGMA integrity_check;') == ok ]] ||
  fail STAGING_DATABASE_INTEGRITY_FAILED
[[ $(sqlite3 "$staging_database" 'SELECT COUNT(*) FROM discord_lifecycle_jobs;') == 0 ]] ||
  fail STAGING_LIFECYCLE_QUEUE_NOT_EMPTY
rm -f -- "$staging_database"
trap - EXIT

backup_ready=0
release_switched=0
rollback_upgrade() {
  local status=$?
  if [[ $status -eq 0 ]]; then
    return
  fi
  set +e
  systemctl stop "${units[@]}" >/dev/null 2>&1 || true
  if [[ $release_switched -eq 1 ]]; then
    ln -s "$old_release" /opt/calculus-discord/current.rollback
    mv -Tf /opt/calculus-discord/current.rollback /opt/calculus-discord/current
  fi
  if [[ $backup_ready -eq 1 ]]; then
    install -o calculus-bot -g calculus-bot -m 0600 \
      "$rollback_database" "$database.rollback"
    mv -f "$database.rollback" "$database"
  fi
  systemctl start "${units[@]}" >/dev/null 2>&1 || true
  printf 'rollback=APPLIED\nremote_services=RESTORE_ATTEMPTED\n' >&2
}
trap rollback_upgrade EXIT

systemctl stop "${units[@]}"
sqlite3 "$database" ".backup '$rollback_database'"
chown calculus-bot:calculus-bot "$rollback_database"
chmod 0600 "$rollback_database"
[[ $(sqlite3 "$rollback_database" 'PRAGMA integrity_check;') == ok ]] ||
  fail ROLLBACK_DATABASE_INTEGRITY_FAILED
backup_ready=1
rollback_sha=$(sha256sum "$rollback_database" | cut -d' ' -f1)
printf 'release=%s\nrollback_sha256=%s\n' "$release_id" "$rollback_sha" >"$receipt"
chown calculus-bot:calculus-bot "$receipt"
chmod 0600 "$receipt"

ln -s "releases/$release_id" /opt/calculus-discord/current.incoming
mv -Tf /opt/calculus-discord/current.incoming /opt/calculus-discord/current
release_switched=1

started_at=$(date -u '+%Y-%m-%dT%H:%M:%S+00:00')
wait_for_health() {
  local unit=$1
  local service_key=$2
  local attempts=0
  while ((attempts < 45)); do
    if [[ $(systemctl is-active "$unit" 2>/dev/null || true) == active ]] &&
      [[ $(sqlite3 "$database" \
        "SELECT COUNT(*) FROM service_health WHERE service_key='$service_key' AND status='HEALTHY' AND safe_error_code IS NULL AND last_heartbeat_at >= '$started_at';") == 1 ]]; then
      printf '%s=HEALTHY\n' "$service_key"
      return 0
    fi
    sleep 2
    attempts=$((attempts + 1))
  done
  fail SERVICE_HEALTH_TIMEOUT
}

systemctl start calculus-course-assistant.service
wait_for_health calculus-course-assistant.service course-assistant
systemctl start calculus-dump-bot.service
wait_for_health calculus-dump-bot.service dump-bot
systemctl start calculus-data-bridge.service
wait_for_health calculus-data-bridge.service data-bridge

[[ $(sqlite3 "$database" 'PRAGMA integrity_check;') == ok ]] ||
  fail PRODUCTION_DATABASE_INTEGRITY_FAILED_AFTER_UPGRADE
[[ $(sqlite3 "$database" 'PRAGMA user_version;') == 6 ]] ||
  fail PRODUCTION_DATABASE_SCHEMA_INVALID_AFTER_UPGRADE
[[ $(sqlite3 "$database" 'SELECT COUNT(*) FROM schema_migrations;') == 6 ]] ||
  fail PRODUCTION_DATABASE_LEDGER_INVALID_AFTER_UPGRADE
[[ $(sqlite3 "$database" \
  "SELECT COUNT(*) FROM discord_lifecycle_jobs WHERE status='PERMANENT_FAILURE';") == 0 ]] ||
  fail LIFECYCLE_QUEUE_DEGRADED

trap - EXIT
printf 'upgrade=PASS\nschema=6\nremote_services=HEALTHY\nproduction_writer=REMOTE\n'
