#!/usr/bin/env bash
set -euo pipefail
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
LC_ALL=C
export LC_ALL
IFS=$' \t\n'
umask 077
unset BASH_ENV ENV PYTHONHOME PYTHONPATH PIP_CONFIG_FILE

archive=${1:-}
expected_sha256=${2:-}
release_id=${3:-}
staging_root=/home/ding/calculus-discord-staging

fail() {
  printf 'v13_friend_bootstrap=FAIL\nsafe_error_code=%s\ndeploy_executed=NO\n' "$1" >&2
  exit 2
}

[[ ${EUID} -eq 0 ]] || fail ROOT_REQUIRED
[[ $# -eq 3 ]] || fail ARGUMENTS_INVALID
[[ ${BOOTSTRAP_V13_RELEASE:-} == BOOTSTRAP-V13-RELEASE ]] || fail EXACT_APPROVAL_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST
[[ $release_id =~ ^[a-f0-9]{12}$ ]] || fail RELEASE_ID_INVALID
[[ $expected_sha256 =~ ^[a-f0-9]{64}$ ]] || fail ARCHIVE_SHA256_INVALID
[[ $archive == "$staging_root/v13-release-$release_id.tar" ]] ||
  fail ARCHIVE_PATH_REFUSED
id ding >/dev/null 2>&1 || fail DEPLOY_USER_MISSING
for command in chown chmod find hostname id install mv python3 rm stat; do
  command -v "$command" >/dev/null 2>&1 || fail "COMMAND_MISSING_${command^^}"
done

release_root=$staging_root/releases
destination=$release_root/$release_id
incoming=$destination.incoming
[[ ! -e $destination && ! -e $incoming ]] || fail RELEASE_DESTINATION_NOT_EMPTY
install -d -o ding -g ding -m 0700 "$release_root"
install -d -o root -g root -m 0700 "$incoming"
cleanup_bootstrap() {
  local result=$?
  if [[ $result -ne 0 && -d $incoming ]]; then
    rm -rf -- "$incoming"
  fi
  return "$result"
}
trap cleanup_bootstrap EXIT

python3 - "$archive" "$incoming" "$expected_sha256" "$release_id" <<'PY' ||
  fail ARCHIVE_VALIDATION_FAILED
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile

archive = Path(sys.argv[1])
destination = Path(sys.argv[2])
expected_sha256 = sys.argv[3]
release_id = sys.argv[4]
descriptor = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW)
try:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise SystemExit(1)
    if metadata.st_size > 104_857_600:
        raise SystemExit(1)
    with os.fdopen(descriptor, "rb", closefd=False) as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if digest != expected_sha256:
            raise SystemExit(1)
        handle.seek(0)
        with tarfile.open(fileobj=handle, mode="r:") as bundle:
            commit = str(bundle.pax_headers.get("comment", ""))
            if len(commit) != 40 or not commit.startswith(release_id):
                raise SystemExit(1)
            members = bundle.getmembers()
            if not 1 <= len(members) <= 20_000:
                raise SystemExit(1)
            if sum(item.size for item in members if item.isfile()) > 268_435_456:
                raise SystemExit(1)
            for item in members:
                path = PurePosixPath(item.name)
                if path.is_absolute() or ".." in path.parts:
                    raise SystemExit(1)
                if not (item.isfile() or item.isdir()):
                    raise SystemExit(1)
            bundle.extractall(destination, filter="data")
finally:
    os.close(descriptor)
PY

[[ -z $(find "$incoming" -type l -print -quit) ]] || fail EXTRACTED_SYMLINK_REFUSED
[[ -z $(find "$incoming" ! -type f ! -type d -print -quit) ]] ||
  fail EXTRACTED_SPECIAL_FILE_REFUSED
host_prepare=$incoming/ops/scripts/v13-host-owner-prepare.sh
[[ -x $host_prepare && -f $host_prepare && ! -L $host_prepare ]] ||
  fail HOST_PREPARE_ENTRYPOINT_INVALID
chown -R ding:ding "$incoming"
[[ -z $(find "$incoming" -perm /022 -print -quit) ]] || fail EXTRACTED_WRITABLE_BY_OTHERS
mv "$incoming" "$destination"
trap - EXIT

PREPARE_V13_HOST=PREPARE-V13-HOST \
  "$destination/ops/scripts/v13-host-owner-prepare.sh" "$destination"
printf 'v13_friend_bootstrap=PASS\nrelease_staged=PASS\ndeploy_executed=NO\n'
