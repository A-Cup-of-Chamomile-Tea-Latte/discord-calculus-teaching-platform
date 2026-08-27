#!/usr/bin/env bash
set -euo pipefail

host_config=${1:-}
[[ ${EUID} -eq 0 ]] || { printf 'portal_staging_rollback=FAIL safe_code=ROOT_REQUIRED\n' >&2; exit 2; }
[[ -f $host_config && ! -L $host_config ]] || {
  printf 'portal_staging_rollback=FAIL safe_code=HOST_CONFIG_INVALID\n' >&2
  exit 2
}

json_value() {
  python3 -I - "$host_config" "$1" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle)[sys.argv[2]])
PY
}

origin=$(json_value origin)
base_path=$(json_value basePath)
bind_port=$(json_value bindPort)
trusted_proxy=$(json_value trustedProxyIp)
proxy_adapter=$(json_value proxyAdapter)
[[ $origin =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?$ ]] || {
  printf 'portal_staging_rollback=FAIL safe_code=ORIGIN_INVALID\n' >&2
  exit 2
}
[[ $base_path == / || $base_path =~ ^/[A-Za-z0-9._~-]+(/[A-Za-z0-9._~-]+)*$ ]] || {
  printf 'portal_staging_rollback=FAIL safe_code=BASE_PATH_INVALID\n' >&2
  exit 2
}
[[ $bind_port =~ ^[0-9]+$ ]] && ((bind_port >= 1024 && bind_port <= 65535)) || {
  printf 'portal_staging_rollback=FAIL safe_code=BIND_PORT_INVALID\n' >&2
  exit 2
}
[[ $trusted_proxy == 127.0.0.1 || $trusted_proxy == ::1 ]] || {
  printf 'portal_staging_rollback=FAIL safe_code=TRUSTED_PROXY_INVALID\n' >&2
  exit 2
}
[[ $(stat -c %u "$host_config") == 0 ]] || {
  printf 'portal_staging_rollback=FAIL safe_code=HOST_CONFIG_OWNER_INVALID\n' >&2
  exit 2
}
(( (8#$(stat -c %a "$host_config") & 8#022) == 0 )) || {
  printf 'portal_staging_rollback=FAIL safe_code=HOST_CONFIG_MODE_INVALID\n' >&2
  exit 2
}
[[ $proxy_adapter == /* && -x $proxy_adapter && ! -L $proxy_adapter ]] || {
  printf 'portal_staging_rollback=FAIL safe_code=PROXY_ADAPTER_INVALID\n' >&2
  exit 2
}
[[ $(stat -c %u "$proxy_adapter") == 0 ]] || {
  printf 'portal_staging_rollback=FAIL safe_code=PROXY_ADAPTER_OWNER_INVALID\n' >&2
  exit 2
}
(( (8#$(stat -c %a "$proxy_adapter") & 8#022) == 0 )) || {
  printf 'portal_staging_rollback=FAIL safe_code=PROXY_ADAPTER_MODE_INVALID\n' >&2
  exit 2
}

install_root=/opt/calculus-portal-staging
current_link=$install_root/current
control_root=/var/lib/calculus-portal-staging-control
unit_name=calculus-portal-synthetic-staging.service
upstream=http://127.0.0.1:$bind_port
previous=$(sed -n '1p' "$control_root/previous-release" 2>/dev/null || true)

"$proxy_adapter" disable --origin "$origin" --base-path "$base_path" --upstream "$upstream"
systemctl stop "$unit_name"
if [[ -z $previous ]]; then
  systemctl disable "$unit_name" >/dev/null
  printf 'portal_staging_rollback=PASS\nresult=STOPPED_NO_PREVIOUS_RELEASE\n'
  printf 'production_modified=NO\n'
  exit 0
fi
[[ $previous == "$install_root/releases/"* && -d $previous && ! -L $previous ]] || {
  printf 'portal_staging_rollback=FAIL safe_code=PREVIOUS_RELEASE_INVALID\n' >&2
  exit 2
}
ln -sfn "$previous" "$current_link.rollback"
mv -Tf "$current_link.rollback" "$current_link"
systemctl start "$unit_name"
systemctl is-active --quiet "$unit_name"
"$proxy_adapter" enable --origin "$origin" --base-path "$base_path" --upstream "$upstream"
printf 'portal_staging_rollback=PASS\nresult=PREVIOUS_STAGING_RELEASE_RESTORED\n'
printf 'production_modified=NO\n'
