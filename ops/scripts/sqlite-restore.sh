#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  printf 'usage: %s BACKUP.sqlite3 DESTINATION.sqlite3 EXPECTED_SHA256\n' "$0" >&2
  exit 2
fi
backup_db=$1
destination=$2
expected_sha256=$(printf '%s' "$3" | tr '[:upper:]' '[:lower:]')

[[ -f $backup_db ]] || { printf 'backup database is missing\n' >&2; exit 2; }
[[ ! -e $destination ]] || { printf 'destination already exists\n' >&2; exit 2; }
[[ $expected_sha256 =~ ^[a-f0-9]{64}$ ]] || {
  printf 'expected SHA-256 is invalid\n' >&2
  exit 2
}

actual_sha256=$(sha256sum "$backup_db" | awk '{print $1}')
[[ $actual_sha256 == "$expected_sha256" ]] || {
  printf 'backup checksum mismatch\n' >&2
  exit 1
}
[[ $(sqlite3 "$backup_db" 'PRAGMA integrity_check;') == ok ]] || {
  printf 'backup integrity check failed\n' >&2
  exit 1
}

umask 077
install -m 0600 "$backup_db" "$destination"
[[ $(sqlite3 "$destination" 'PRAGMA integrity_check;') == ok ]] || {
  printf 'restored database integrity check failed\n' >&2
  exit 1
}
restored_sha256=$(sha256sum "$destination" | awk '{print $1}')
[[ $restored_sha256 == "$expected_sha256" ]] || {
  printf 'restored database checksum mismatch\n' >&2
  exit 1
}
printf '%s\n' "$restored_sha256"
