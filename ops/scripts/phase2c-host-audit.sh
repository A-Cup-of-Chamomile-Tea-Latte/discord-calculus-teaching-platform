#!/usr/bin/env bash
set -euo pipefail

printf 'distro='; . /etc/os-release; printf '%s %s\n' "$ID" "$VERSION_ID"
printf 'kernel='; uname -sr
printf 'architecture='; uname -m
printf 'systemd='; systemctl --version | head -n 1
printf 'python='; python3 --version
printf 'sqlite='; sqlite3 --version | cut -d' ' -f1
printf 'disk='; df -h / | awk 'NR==2 {print $4 " free"}'
printf 'memory='; awk '/MemTotal/ {printf "%.1f GiB\n", $2/1024/1024}' /proc/meminfo
printf 'cpu='; getconf _NPROCESSORS_ONLN
printf 'timezone='; timedatectl show -p Timezone --value
printf 'ntp='; timedatectl show -p NTPSynchronized --value
printf 'discord_https='; curl --silent --show-error --fail --max-time 10 https://discord.com/api/v10/gateway >/dev/null && printf 'ok\n'
printf 'google_https='; curl --silent --show-error --fail --max-time 10 'https://script.googleapis.com/$discovery/rest?version=v1' >/dev/null && printf 'ok\n'
