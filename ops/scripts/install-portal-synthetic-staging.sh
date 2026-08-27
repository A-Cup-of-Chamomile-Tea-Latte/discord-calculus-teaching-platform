#!/usr/bin/env bash
set -euo pipefail

package_dir=
host_config=
dry_run=0

fail() {
  printf 'portal_staging_install=FAIL safe_code=%s\n' "$1" >&2
  exit 2
}

while (($#)); do
  case $1 in
    --package-dir) package_dir=${2:-}; shift 2 ;;
    --host-config) host_config=${2:-}; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    *) fail UNKNOWN_ARGUMENT ;;
  esac
done

[[ -n $package_dir && -n $host_config ]] || fail REQUIRED_ARGUMENT_MISSING
[[ -d $package_dir && ! -L $package_dir ]] || fail PACKAGE_DIRECTORY_INVALID
[[ -f $host_config && ! -L $host_config ]] || fail HOST_CONFIG_INVALID
[[ -f $package_dir/manifest.json && -f $package_dir/SHA256SUMS ]] || fail PACKAGE_INCOMPLETE
[[ -z $(find "$package_dir" -type l -print -quit) ]] || fail PACKAGE_SYMLINK_REFUSED
(
  cd "$package_dir"
  sha256sum -c SHA256SUMS >/dev/null
) || fail PACKAGE_CHECKSUM_INVALID

json_value() {
  python3 -I - "$1" "$2" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    value = json.load(handle)[sys.argv[2]]
if isinstance(value, bool) or not isinstance(value, (str, int)):
    raise SystemExit(2)
print(value)
PY
}

release_id=$(json_value "$package_dir/manifest.json" releaseId) || fail MANIFEST_INVALID
package_origin=$(json_value "$package_dir/manifest.json" origin) || fail MANIFEST_INVALID
package_base=$(json_value "$package_dir/manifest.json" basePath) || fail MANIFEST_INVALID
origin=$(json_value "$host_config" origin) || fail HOST_CONFIG_INVALID
base_path=$(json_value "$host_config" basePath) || fail HOST_CONFIG_INVALID
bind_port=$(json_value "$host_config" bindPort) || fail HOST_CONFIG_INVALID
trusted_proxy=$(json_value "$host_config" trustedProxyIp) || fail HOST_CONFIG_INVALID
proxy_adapter=$(json_value "$host_config" proxyAdapter) || fail HOST_CONFIG_INVALID

[[ $release_id =~ ^[0-9a-f]{12}$ ]] || fail RELEASE_ID_INVALID
[[ $origin == "$package_origin" && $base_path == "$package_base" ]] ||
  fail PACKAGE_HOST_CONTRACT_MISMATCH
[[ $origin =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?$ ]] || fail ORIGIN_INVALID
[[ $base_path == / || $base_path =~ ^/[A-Za-z0-9._~-]+(/[A-Za-z0-9._~-]+)*$ ]] ||
  fail BASE_PATH_INVALID
[[ $bind_port =~ ^[0-9]+$ ]] || fail BIND_PORT_INVALID
((bind_port >= 1024 && bind_port <= 65535)) || fail BIND_PORT_INVALID
[[ $trusted_proxy == 127.0.0.1 || $trusted_proxy == ::1 ]] || fail TRUSTED_PROXY_INVALID
[[ $proxy_adapter == /* && -x $proxy_adapter && ! -L $proxy_adapter ]] ||
  fail PROXY_ADAPTER_INVALID

if ((dry_run)); then
  printf 'portal_staging_install_dry_run=PASS\n'
  printf 'release_id=%s\n' "$release_id"
  printf 'origin=%s\n' "$origin"
  printf 'base_path=%s\n' "$base_path"
  printf 'bind_port=%s\n' "$bind_port"
  printf 'production_modified=NO\n'
  exit 0
fi

((EUID == 0)) || fail ROOT_REQUIRED
[[ $(stat -c %u "$host_config") == 0 ]] || fail HOST_CONFIG_OWNER_INVALID
(( (8#$(stat -c %a "$host_config") & 8#022) == 0 )) || fail HOST_CONFIG_MODE_INVALID
[[ $(stat -c %u "$proxy_adapter") == 0 ]] || fail PROXY_ADAPTER_OWNER_INVALID
(( (8#$(stat -c %a "$proxy_adapter") & 8#022) == 0 )) || fail PROXY_ADAPTER_MODE_INVALID

install_root=/opt/calculus-portal-staging
release_root=$install_root/releases/$release_id
current_link=$install_root/current
control_root=/var/lib/calculus-portal-staging-control
environment_root=/etc/calculus-portal-staging
unit_name=calculus-portal-synthetic-staging.service
unit_path=/etc/systemd/system/$unit_name
upstream=http://127.0.0.1:$bind_port
database=/run/calculus-portal-staging/data/portal.synthetic.sqlite3
activated=0
proxy_enabled=0
previous=

if [[ -L $current_link ]]; then
  previous=$(readlink -f "$current_link")
  [[ $previous == "$install_root/releases/"* ]] || fail CURRENT_RELEASE_BOUNDARY_INVALID
fi

restore_on_failure() {
  local exit_code=$?
  ((exit_code != 0)) || return
  if ((proxy_enabled)); then
    "$proxy_adapter" disable --origin "$origin" --base-path "$base_path" \
      --upstream "$upstream" >/dev/null 2>&1 || true
  fi
  if ((activated)); then
    systemctl stop "$unit_name" >/dev/null 2>&1 || true
    if [[ -n $previous && -d $previous ]]; then
      ln -sfn "$previous" "$current_link.rollback"
      mv -Tf "$current_link.rollback" "$current_link"
      systemctl start "$unit_name" >/dev/null 2>&1 || true
    else
      rm -f -- "$current_link"
    fi
  fi
  printf 'portal_staging_install=FAIL safe_code=INSTALL_ROLLED_BACK\n' >&2
  exit "$exit_code"
}
trap restore_on_failure EXIT

install -d -o root -g root -m 0755 "$install_root" "$install_root/releases"
install -d -o root -g root -m 0700 "$control_root" "$environment_root"
[[ ! -e $release_root ]] || fail RELEASE_ALREADY_PRESENT
install -d -o root -g root -m 0755 "$release_root"
cp -a -- "$package_dir"/. "$release_root"/
chown -R root:root "$release_root"
chmod -R go-w "$release_root"

runtime=$release_root/runtime/discord-course-bots
python3 -m venv "$runtime/.venv"
"$runtime/.venv/bin/pip" install --disable-pip-version-check \
  -r "$release_root/ops/portal-runtime-requirements.txt" >/dev/null
"$runtime/.venv/bin/pip" install --disable-pip-version-check --no-deps "$runtime" >/dev/null
[[ -x $runtime/.venv/bin/portal-staging ]] || fail VENV_INSTALL_INVALID
chown -R root:root "$runtime/.venv"
chmod -R go-w "$runtime/.venv"

session_secret=$(openssl rand -hex 32)
environment_incoming=$environment_root/runtime.env.incoming
{
  printf 'PORTAL_STAGING_SYNTHETIC_ONLY=1\n'
  printf 'PORTAL_STAGING_ORIGIN=%s\n' "$origin"
  printf 'PORTAL_STAGING_BASE_PATH=%s\n' "$base_path"
  printf 'PORTAL_STAGING_BIND_PORT=%s\n' "$bind_port"
  printf 'PORTAL_STAGING_TRUSTED_PROXY_IP=%s\n' "$trusted_proxy"
  printf 'PORTAL_STAGING_SESSION_SECRET=%s\n' "$session_secret"
} >"$environment_incoming"
chmod 0600 "$environment_incoming"
chown root:root "$environment_incoming"
mv -f "$environment_incoming" "$environment_root/runtime.env"
unset session_secret

install -o root -g root -m 0644 "$release_root/ops/calculus-portal-synthetic-staging.service" \
  "$unit_path"
ln -sfn "$release_root" "$current_link.incoming"
mv -Tf "$current_link.incoming" "$current_link"
activated=1
systemctl daemon-reload
systemctl enable --now "$unit_name" >/dev/null
systemctl is-active --quiet "$unit_name"

python3 -I "$release_root/ops/portal_staging_smoke.py" \
  --target "$upstream" --origin "$origin" --base-path "$base_path" \
  --database "$database" --forwarded-client 192.0.2.10

"$proxy_adapter" check --origin "$origin" --base-path "$base_path" --upstream "$upstream"
"$proxy_adapter" enable --origin "$origin" --base-path "$base_path" --upstream "$upstream"
proxy_enabled=1
python3 -I "$release_root/ops/portal_staging_smoke.py" \
  --target "$origin" --origin "$origin" --base-path "$base_path" --database "$database"

printf '%s\n' "$previous" >"$control_root/previous-release"
printf '%s\n' "$release_root" >"$control_root/current-release"
chmod 0600 "$control_root/previous-release" "$control_root/current-release"
trap - EXIT
printf 'portal_staging_install=PASS\n'
printf 'release_id=%s\n' "$release_id"
printf 'synthetic_only=YES\nproduction_modified=NO\ndiscord_mutation=NO\n'
