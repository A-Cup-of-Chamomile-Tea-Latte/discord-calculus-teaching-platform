#!/usr/bin/env bash
set -euo pipefail

bundle=${1:-}
release_id=${2:-}

fail() {
  printf 'repair_error=%s\n' "$1" >&2
  exit 2
}

[[ ${EUID} -eq 0 ]] || fail ROOT_REQUIRED
[[ ${GO_LIVE_CUTOVER:-} == GO-LIVE-CUTOVER ]] || fail EXACT_GO_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST
[[ $release_id =~ ^[a-f0-9]{7,40}$ ]] || fail RELEASE_ID_INVALID
bundle=$(realpath -e "$bundle")
[[ $bundle == /home/ding/calculus-discord-staging/cutover-ready/* ]] ||
  fail BUNDLE_PATH_REFUSED

release=/opt/calculus-discord/releases/$release_id
runtime=$release/runtime/discord-course-bots
venv=$runtime/.venv
broken=$runtime/.venv.broken-atomic-move
database=/var/lib/calculus-discord/runtime.sqlite3
units=(
  calculus-course-assistant.service
  calculus-dump-bot.service
  calculus-data-bridge.service
)

[[ $(readlink -f /opt/calculus-discord/current) == "$release" ]] ||
  fail CURRENT_RELEASE_MISMATCH
[[ -d $runtime && -d $venv ]] || fail RELEASE_VENV_MISSING
[[ ! -e $broken ]] || fail BROKEN_VENV_BACKUP_PRESENT
[[ -f $bundle/runtime-requirements.txt ]] || fail RUNTIME_LOCK_MISSING
[[ -f $database ]] || fail PRODUCTION_DATABASE_MISSING
[[ $(sqlite3 "$database" 'PRAGMA integrity_check;') == ok ]] ||
  fail PRODUCTION_DATABASE_INTEGRITY_FAILED
[[ $(sqlite3 "$database" 'PRAGMA user_version;') == 5 ]] ||
  fail PRODUCTION_DATABASE_SCHEMA_INVALID
for unit in "${units[@]}"; do
  [[ $(systemctl is-active "$unit" 2>/dev/null || true) != active ]] ||
    fail REMOTE_SERVICE_ALREADY_ACTIVE
done

systemctl disable --now "${units[@]}" >/dev/null 2>&1 || true
repair_failure() {
  local status=$?
  if [[ $status -eq 0 ]]; then
    return
  fi
  systemctl stop "${units[@]}" >/dev/null 2>&1 || true
  systemctl disable "${units[@]}" >/dev/null 2>&1 || true
  if [[ -d $broken ]]; then
    if [[ -e $venv ]]; then
      rm -rf -- "$venv"
    fi
    mv "$broken" "$venv"
  fi
  printf 'remote_services=STOPPED_AFTER_FAILURE\n' >&2
}
trap repair_failure EXIT
mv "$venv" "$broken"

python3 -m venv "$venv"
"$venv/bin/pip" install -r "$bundle/runtime-requirements.txt" >/dev/null
"$venv/bin/pip" install --no-deps "$runtime" >/dev/null
for executable in course-assistant dump-bot discord-production-bridge; do
  [[ -x $venv/bin/$executable ]] || fail RELEASE_EXECUTABLE_MISSING
  [[ $(head -n 1 "$venv/bin/$executable") == "#!$venv/bin/python" ]] ||
    fail RELEASE_SHEBANG_INVALID
done
chown -R root:root "$venv"
chmod -R go-w "$venv"

started_at=$(date -u '+%Y-%m-%dT%H:%M:%S+00:00')
wait_for_health() {
  local unit=$1
  local service_key=$2
  local attempts=0
  while (( attempts < 30 )); do
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

systemctl enable calculus-course-assistant.service >/dev/null
systemctl start calculus-course-assistant.service
wait_for_health calculus-course-assistant.service course-assistant

systemctl enable calculus-dump-bot.service >/dev/null
systemctl start calculus-dump-bot.service
wait_for_health calculus-dump-bot.service dump-bot

systemctl enable calculus-data-bridge.service >/dev/null
systemctl start calculus-data-bridge.service
wait_for_health calculus-data-bridge.service data-bridge
sleep 10
[[ $(sqlite3 "$database" \
  "SELECT COUNT(*) FROM service_health WHERE service_key='data-bridge' AND status='HEALTHY' AND safe_error_code IS NULL AND last_heartbeat_at >= '$started_at';") == 1 ]] ||
  fail DATA_BRIDGE_DEGRADED
[[ $(sqlite3 "$database" \
  "SELECT COUNT(*) FROM projection_outbox WHERE status != 'COMPLETED';") == 0 ]] ||
  fail DATA_BRIDGE_BACKLOG_NOT_DRAINED

rm -rf -- "$broken"
trap - EXIT
printf 'venv_repair=PASS\n'
printf 'course-assistant=HEALTHY\n'
printf 'dump-bot=HEALTHY\n'
printf 'data-bridge=HEALTHY\n'
printf 'remote_services=HEALTHY\n'
printf 'production_writer=REMOTE\n'
