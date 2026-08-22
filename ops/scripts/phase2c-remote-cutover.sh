#!/usr/bin/env bash
set -euo pipefail

mode=${1:-}
bundle=${2:-}
release_source=${3:-}

fail() {
  printf 'cutover_error=%s\n' "$1" >&2
  exit 2
}

[[ ${EUID} -eq 0 ]] || fail ROOT_REQUIRED
[[ ${GO_LIVE_CUTOVER:-} == GO-LIVE-CUTOVER ]] || fail EXACT_GO_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST
[[ $mode == prepare || $mode == activate ]] || fail MODE_REQUIRED

bundle=$(realpath -e "$bundle")
release_source=$(realpath -e "$release_source")
[[ $bundle == /home/ding/calculus-discord-staging/cutover-ready/* ]] ||
  fail BUNDLE_PATH_REFUSED
[[ $release_source == /home/ding/calculus-discord-staging/releases/* ]] ||
  fail RELEASE_PATH_REFUSED

release_id=$(basename "$release_source")
[[ $release_id =~ ^[a-f0-9]{7,40}$ ]] || fail RELEASE_ID_INVALID
release_destination="/opt/calculus-discord/releases/$release_id"
runtime_directory="$release_destination/runtime/discord-course-bots"
database=/var/lib/calculus-discord/runtime.sqlite3
units=(
  calculus-course-assistant.service
  calculus-dump-bot.service
  calculus-data-bridge.service
)

for unit in "${units[@]}"; do
  [[ $(systemctl is-active "$unit" 2>/dev/null || true) != active ]] ||
    fail REMOTE_SERVICE_ALREADY_ACTIVE
done

if [[ $mode == prepare ]]; then
  [[ ! -e /opt/calculus-discord/current ]] || fail CURRENT_ALREADY_PRESENT
  [[ ! -e $release_destination ]] || fail RELEASE_ALREADY_PRESENT
  for file in course-assistant.env dump-bot.env data-bridge.env google-oauth.json; do
    [[ -f $bundle/$file ]] || fail BUNDLE_FILE_MISSING
    [[ $(stat -c %a "$bundle/$file") == 600 ]] || fail BUNDLE_FILE_MODE_INVALID
  done
  for unit in "${units[@]}"; do
    [[ -f $bundle/units/$unit ]] || fail BUNDLE_UNIT_MISSING
  done
  [[ -f $bundle/runtime-requirements.txt ]] || fail RUNTIME_LOCK_MISSING

  getent group calculus-bot >/dev/null || groupadd --system calculus-bot
  id calculus-bot >/dev/null 2>&1 ||
    useradd --system --gid calculus-bot --home-dir /var/lib/calculus-discord \
      --shell /usr/sbin/nologin calculus-bot
  install -d -o root -g root -m 0755 \
    /opt/calculus-discord /opt/calculus-discord/releases
  install -d -o calculus-bot -g calculus-bot -m 0700 \
    /var/lib/calculus-discord /var/lib/calculus-discord/staging \
    /var/lib/calculus-discord/backups /var/lib/calculus-discord/receipts \
    /var/lib/calculus-discord/exports /var/lib/calculus-discord/exports/public \
    /var/lib/calculus-discord/exports/private
  install -d -o root -g calculus-bot -m 0750 /etc/calculus-discord

  incoming="$release_destination.incoming"
  [[ ! -e $incoming ]] || fail RELEASE_INCOMING_PRESENT
  install -d -o root -g root -m 0755 "$incoming"
  cleanup_incoming() {
    if [[ -n ${incoming:-} && -d $incoming ]]; then
      rm -rf -- "$incoming"
    fi
  }
  trap cleanup_incoming ERR
  tar -C "$release_source" \
    --exclude='./runtime/discord-course-bots/.venv' -cf - . |
    tar -C "$incoming" -xf -
  python3 -m venv "$incoming/runtime/discord-course-bots/.venv"
  "$incoming/runtime/discord-course-bots/.venv/bin/pip" install \
    -r "$bundle/runtime-requirements.txt" >/dev/null
  "$incoming/runtime/discord-course-bots/.venv/bin/pip" install --no-deps \
    "$incoming/runtime/discord-course-bots" >/dev/null
  for executable in course-assistant dump-bot discord-production-bridge; do
    [[ -x $incoming/runtime/discord-course-bots/.venv/bin/$executable ]] ||
      fail RELEASE_EXECUTABLE_MISSING
  done
  chown -R root:root "$incoming"
  chmod -R go-w "$incoming"
  mv "$incoming" "$release_destination"
  trap - ERR

  install -o calculus-bot -g calculus-bot -m 0600 \
    "$bundle/course-assistant.env" /etc/calculus-discord/course-assistant.env
  install -o calculus-bot -g calculus-bot -m 0600 \
    "$bundle/dump-bot.env" /etc/calculus-discord/dump-bot.env
  install -o calculus-bot -g calculus-bot -m 0600 \
    "$bundle/data-bridge.env" /etc/calculus-discord/data-bridge.env
  install -o calculus-bot -g calculus-bot -m 0600 \
    "$bundle/google-oauth.json" /etc/calculus-discord/google-oauth.json
  for unit in "${units[@]}"; do
    install -o root -g root -m 0644 \
      "$bundle/units/$unit" "/etc/systemd/system/$unit"
  done
  systemctl daemon-reload
  printf 'prepare=PASS\nrelease_ready=true\nservices_started=false\n'
  exit 0
fi

[[ -d $release_destination ]] || fail RELEASE_NOT_PREPARED
[[ ! -e /opt/calculus-discord/current ]] || fail CURRENT_ALREADY_PRESENT
[[ ! -e $database ]] || fail PRODUCTION_DATABASE_ALREADY_PRESENT
[[ -f $bundle/runtime.sqlite3 ]] || fail PRODUCTION_DATABASE_MISSING
[[ $(stat -c %a "$bundle/runtime.sqlite3") == 600 ]] ||
  fail PRODUCTION_DATABASE_MODE_INVALID
[[ $(sqlite3 "$bundle/runtime.sqlite3" 'PRAGMA integrity_check;') == ok ]] ||
  fail PRODUCTION_DATABASE_INTEGRITY_FAILED
[[ $(sqlite3 "$bundle/runtime.sqlite3" 'PRAGMA user_version;') == 5 ]] ||
  fail PRODUCTION_DATABASE_SCHEMA_INVALID
[[ $(sqlite3 "$bundle/runtime.sqlite3" \
  'SELECT COUNT(*) FROM schema_migrations;') == 5 ]] ||
  fail PRODUCTION_DATABASE_LEDGER_INVALID

install -o calculus-bot -g calculus-bot -m 0600 \
  "$bundle/runtime.sqlite3" "$database.incoming"
mv "$database.incoming" "$database"
ln -s "releases/$release_id" /opt/calculus-discord/current.incoming
mv /opt/calculus-discord/current.incoming /opt/calculus-discord/current

rollback_remote() {
  systemctl stop "${units[@]}" >/dev/null 2>&1 || true
  systemctl disable "${units[@]}" >/dev/null 2>&1 || true
  printf 'remote_services=STOPPED_AFTER_FAILURE\n' >&2
}
trap rollback_remote ERR

wait_for_health() {
  local unit=$1
  local service_key=$2
  local attempts=0
  while (( attempts < 30 )); do
    if [[ $(systemctl is-active "$unit" 2>/dev/null || true) == active ]] &&
      [[ $(sqlite3 "$database" \
        "SELECT COUNT(*) FROM service_health WHERE service_key='$service_key' AND status='HEALTHY' AND safe_error_code IS NULL;") == 1 ]]; then
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
  "SELECT COUNT(*) FROM service_health WHERE service_key='data-bridge' AND status='HEALTHY' AND safe_error_code IS NULL;") == 1 ]] ||
  fail DATA_BRIDGE_DEGRADED

trap - ERR
printf 'activate=PASS\nremote_services=HEALTHY\nproduction_writer=REMOTE\n'
