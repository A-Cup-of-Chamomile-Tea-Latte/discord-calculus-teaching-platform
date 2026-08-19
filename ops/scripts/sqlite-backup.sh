#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'usage: %s SOURCE.sqlite3 DESTINATION.sqlite3\n' "$0" >&2
  exit 2
fi
source_db=$1
destination=$2
[[ -f $source_db ]] || { printf 'source database is missing\n' >&2; exit 2; }
[[ ! -e $destination ]] || { printf 'destination already exists\n' >&2; exit 2; }
umask 077
sqlite3 "$source_db" ".backup '$destination'"
[[ $(sqlite3 "$destination" 'PRAGMA integrity_check;') == ok ]] || {
  printf 'backup integrity check failed\n' >&2
  exit 1
}
chmod 0600 "$destination"
sha256sum "$destination"
