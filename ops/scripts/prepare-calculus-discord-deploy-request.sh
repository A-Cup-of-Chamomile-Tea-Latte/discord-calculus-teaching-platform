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
[[ $release_source == /var/lib/calculus-discord-deploy/releases/* ]] ||
  fail RELEASE_PATH_REFUSED
[[ $(stat -c %U:%G "$release_source") == root:root ]] || fail RELEASE_OWNER_INVALID
[[ -z $(find "$release_source" ! -user root -print -quit) ]] || fail RELEASE_TREE_OWNER_INVALID
[[ -z $(find "$release_source" -perm /022 -print -quit) ]] ||
  fail RELEASE_WRITABLE_BY_OTHERS
release_id=$(basename "$release_source")
[[ $release_id =~ ^[a-f0-9]{12}$ ]] || fail RELEASE_ID_INVALID
[[ $target_schema =~ ^[0-9]{1,3}$ ]] || fail TARGET_SCHEMA_INVALID
[[ $migration_class == NONE || $migration_class == ADDITIVE ]] ||
  fail MIGRATION_CLASS_INVALID
[[ -f $release_source/runtime/discord-course-bots/pyproject.toml ]] ||
  fail RUNTIME_SOURCE_MISSING

inbox=/home/ding/calculus-discord-staging/deploy-inbox
request=$inbox/request.txt
legacy_archive=$inbox/release.tar
trusted_archive=$release_source/.v13-source-archive.tar
[[ -f $trusted_archive && ! -L $trusted_archive ]] || fail TRUSTED_ARCHIVE_MISSING
[[ $(stat -c %U:%G "$trusted_archive") == root:root && \
  $(stat -c %a "$trusted_archive") == 444 ]] || fail TRUSTED_ARCHIVE_BOUNDARY_INVALID
[[ ! -e $legacy_archive && ! -e $request ]] || fail DEPLOY_INBOX_NOT_EMPTY
install -d -o ding -g ding -m 0700 "$inbox"
umask 077
archive_sha256=$(sha256sum "$trusted_archive" | cut -d' ' -f1)
printf 'release_id=%s\narchive_sha256=%s\ntarget_schema=%s\nmigration_class=%s\n' \
  "$release_id" "$archive_sha256" "$target_schema" "$migration_class" \
  >"$request.incoming"
chmod 0600 "$request.incoming"
mv "$request.incoming" "$request"
printf 'deploy_request=READY\nrelease=%s\ntarget_schema=%s\nmigration_class=%s\n' \
  "$release_id" "$target_schema" "$migration_class"
