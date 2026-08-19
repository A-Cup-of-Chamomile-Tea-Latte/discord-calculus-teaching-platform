#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  printf 'Run as root on the audited remote host.\n' >&2
  exit 2
fi

getent group calculus-bot >/dev/null || groupadd --system calculus-bot
id calculus-bot >/dev/null 2>&1 || useradd --system --gid calculus-bot --home-dir /var/lib/calculus-discord --shell /usr/sbin/nologin calculus-bot
install -d -o root -g root -m 0755 /opt/calculus-discord /opt/calculus-discord/releases
install -d -o calculus-bot -g calculus-bot -m 0700 /var/lib/calculus-discord /var/lib/calculus-discord/staging /var/lib/calculus-discord/backups
install -d -o root -g calculus-bot -m 0750 /etc/calculus-discord
printf 'host skeleton ready\n'
