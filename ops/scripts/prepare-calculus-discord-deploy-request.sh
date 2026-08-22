#!/usr/bin/env bash
set -euo pipefail
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
LC_ALL=C
export LC_ALL
IFS=$' \t\n'

release_source=${1:-}
target_schema=${2:-}
migration_class=${3:-}

fail() {
  printf 'request_error=%s\n' "$1" >&2
  exit 2
}

[[ ${EUID} -ne 0 ]] || fail ROOT_REFUSED
[[ $(id -un) == ding ]] || fail DEPLOY_USER_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST
release_source=$(realpath -e "$release_source")
[[ $release_source == /home/ding/calculus-discord-staging/releases/* ]] ||
  fail RELEASE_PATH_REFUSED
release_id=$(basename "$release_source")
[[ $release_id =~ ^[a-f0-9]{7,40}$ ]] || fail RELEASE_ID_INVALID
[[ $target_schema =~ ^[0-9]{1,3}$ ]] || fail TARGET_SCHEMA_INVALID
[[ $migration_class == NONE || $migration_class == ADDITIVE ]] ||
  fail MIGRATION_CLASS_INVALID
[[ -f $release_source/runtime/discord-course-bots/pyproject.toml ]] ||
  fail RUNTIME_SOURCE_MISSING

inbox=/home/ding/calculus-discord-staging/deploy-inbox
archive=$inbox/release.tar
request=$inbox/request.txt
[[ ! -e $archive && ! -e $request ]] || fail DEPLOY_INBOX_NOT_EMPTY
install -d -o ding -g ding -m 0700 "$inbox"
umask 077
tar -C "$release_source" --exclude='./runtime/discord-course-bots/.venv' -cf \
  "$archive.incoming" .
archive_sha256=$(sha256sum "$archive.incoming" | cut -d' ' -f1)
printf 'release_id=%s\narchive_sha256=%s\ntarget_schema=%s\nmigration_class=%s\n' \
  "$release_id" "$archive_sha256" "$target_schema" "$migration_class" \
  >"$request.incoming"
chmod 0600 "$archive.incoming" "$request.incoming"
mv "$archive.incoming" "$archive"
mv "$request.incoming" "$request"
printf 'deploy_request=READY\nrelease=%s\ntarget_schema=%s\nmigration_class=%s\n' \
  "$release_id" "$target_schema" "$migration_class"
