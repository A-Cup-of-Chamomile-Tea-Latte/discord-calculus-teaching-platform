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
upload_root=/home/ding/calculus-discord-staging
trusted_root=/var/lib/calculus-discord-deploy
release_root=$trusted_root/releases
destination=$release_root/$release_id
incoming=$destination.incoming
receipt_name=.v13-stage-receipt.json
trusted_archive_name=.v13-source-archive.tar

fail() {
  printf 'v13_friend_bootstrap=FAIL\nsafe_error_code=%s\ndeploy_executed=NO\n' "$1" >&2
  exit 2
}

unexpected_error() {
  local result=$?
  trap - ERR
  printf 'v13_friend_bootstrap=FAIL\nsafe_error_code=UNEXPECTED_ERROR\n' >&2
  printf 'deploy_executed=NO\n' >&2
  exit "$result"
}
trap unexpected_error ERR

[[ ${EUID} -eq 0 ]] || fail ROOT_REQUIRED
[[ $# -eq 3 ]] || fail ARGUMENTS_INVALID
[[ ${BOOTSTRAP_V13_RELEASE:-} == BOOTSTRAP-V13-RELEASE ]] || fail EXACT_APPROVAL_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST
[[ $release_id =~ ^[a-f0-9]{12}$ ]] || fail RELEASE_ID_INVALID
[[ $expected_sha256 =~ ^[a-f0-9]{64}$ ]] || fail ARCHIVE_SHA256_INVALID
[[ $archive == "$upload_root/v13-release-$release_id.tar" ]] || fail ARCHIVE_PATH_REFUSED
id ding >/dev/null 2>&1 || fail DEPLOY_USER_MISSING
for command in dirname find hostname id install mv python3 realpath rm stat; do
  command -v "$command" >/dev/null 2>&1 || fail "COMMAND_MISSING_${command^^}"
done
python3 -I - <<'PY' || fail PYTHON_VERSION_UNSUPPORTED
import sys

if not (3, 12) <= sys.version_info[:2] < (3, 15):
    raise SystemExit(1)
PY

self=$(realpath -e "$0")
self_parent=$(dirname "$self")
[[ $self == /run/v13-bootstrap.*/v13-friend-bootstrap.sh ]] || fail UNTRUSTED_BOOTSTRAP_PATH
[[ $(stat -c %U:%G "$self") == root:root && $(stat -c %a "$self") == 700 ]] ||
  fail UNTRUSTED_BOOTSTRAP_FILE
[[ $(stat -c %U:%G "$self_parent") == root:root && $(stat -c %a "$self_parent") == 700 ]] ||
  fail UNTRUSTED_BOOTSTRAP_PARENT
[[ -d $trusted_root && ! -L $trusted_root ]] || fail TRUSTED_ROOT_MISSING
[[ $(stat -c %U:%G "$trusted_root") == root:root && $(stat -c %a "$trusted_root") == 711 ]] ||
  fail TRUSTED_ROOT_BOUNDARY_INVALID
if [[ -e $release_root ]]; then
  [[ -d $release_root && ! -L $release_root ]] || fail RELEASE_ROOT_INVALID
  [[ $(stat -c %U:%G "$release_root") == root:root ]] || fail RELEASE_ROOT_OWNER_INVALID
  [[ -z $(find "$release_root" -maxdepth 0 -perm /022 -print -quit) ]] ||
    fail RELEASE_ROOT_WRITABLE_BY_OTHERS
else
  install -d -o root -g root -m 0755 "$release_root"
fi

[[ ! -e $incoming ]] || fail RELEASE_INCOMING_PRESENT
if [[ -e $destination ]]; then
  [[ -d $destination && ! -L $destination ]] || fail RELEASE_DESTINATION_INVALID
  stage_action=ALREADY_STAGED
else
  install -d -o root -g root -m 0700 "$incoming"
  stage_action=STAGE_NEW
fi

cleanup_bootstrap() {
  local result=$?
  if [[ $result -ne 0 && $stage_action == STAGE_NEW && -d $incoming ]]; then
    rm -rf -- "$incoming"
  fi
  return "$result"
}
trap cleanup_bootstrap EXIT

stage_path=$destination
[[ $stage_action == STAGE_NEW ]] && stage_path=$incoming
python3 -I - "$archive" "$stage_path" "$expected_sha256" "$release_id" \
  "$stage_action" "$receipt_name" "$trusted_archive_name" <<'PY' ||
  fail ARCHIVE_OR_STAGE_VALIDATION_FAILED
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile

archive = Path(sys.argv[1])
stage = Path(sys.argv[2])
expected_sha256 = sys.argv[3]
release_id = sys.argv[4]
stage_action = sys.argv[5]
receipt_name = sys.argv[6]
trusted_archive_name = sys.argv[7]


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(root: Path) -> tuple[str, int, int]:
    digest = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative in {receipt_name, trusted_archive_name}:
            continue
        metadata = path.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            kind = "D"
            content = ""
        elif stat.S_ISREG(metadata.st_mode):
            kind = "F"
            content = file_digest(path)
            total += metadata.st_size
        else:
            raise SystemExit(1)
        mode = stat.S_IMODE(metadata.st_mode)
        digest.update(f"{kind}\0{relative}\0{mode:o}\0{metadata.st_size}\0{content}\n".encode())
        count += 1
    return digest.hexdigest(), count, total


descriptor = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW)
try:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 104_857_600:
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
            expanded_bytes = sum(item.size for item in members if item.isfile())
            if expanded_bytes > 268_435_456:
                raise SystemExit(1)
            for item in members:
                path = PurePosixPath(item.name)
                if path.is_absolute() or ".." in path.parts:
                    raise SystemExit(1)
                if path.as_posix() in {receipt_name, trusted_archive_name}:
                    raise SystemExit(1)
                if not (item.isfile() or item.isdir()):
                    raise SystemExit(1)
        if stage_action == "STAGE_NEW":
            handle.seek(0)
            trusted_archive = stage / trusted_archive_name
            with trusted_archive.open("xb") as destination:
                shutil.copyfileobj(handle, destination)
            trusted_archive.chmod(0o444)
            handle.seek(0)
            with tarfile.open(fileobj=handle, mode="r:") as bundle:
                bundle.extractall(stage, filter="data")
finally:
    os.close(descriptor)

if stage_action == "STAGE_NEW":
    for path in sorted(stage.rglob("*"), key=lambda value: len(value.parts), reverse=True):
        if path.relative_to(stage).as_posix() == trusted_archive_name:
            continue
        metadata = path.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            path.chmod(0o755)
        elif stat.S_ISREG(metadata.st_mode):
            path.chmod(0o755 if metadata.st_mode & stat.S_IXUSR else 0o644)
        else:
            raise SystemExit(1)
    stage.chmod(0o755)
    tree_sha256, extracted_count, extracted_bytes = tree_digest(stage)
    if extracted_count != len(members) or extracted_bytes != expanded_bytes:
        raise SystemExit(1)
    receipt = {
        "archiveSha256": expected_sha256,
        "commit": commit,
        "expandedBytes": expanded_bytes,
        "memberCount": len(members),
        "releaseId": release_id,
        "status": "PASS",
        "treeSha256": tree_sha256,
    }
    receipt_path = stage / receipt_name
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    receipt_path.chmod(0o600)
else:
    trusted_archive = stage / trusted_archive_name
    if (
        not trusted_archive.is_file()
        or trusted_archive.is_symlink()
        or file_digest(trusted_archive) != expected_sha256
    ):
        raise SystemExit(1)
    receipt_path = stage / receipt_name
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise SystemExit(1)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    tree_sha256, extracted_count, extracted_bytes = tree_digest(stage)
    if not (
        receipt.get("status") == "PASS"
        and receipt.get("archiveSha256") == expected_sha256
        and receipt.get("commit") == commit
        and receipt.get("releaseId") == release_id
        and receipt.get("memberCount") == len(members) == extracted_count
        and receipt.get("expandedBytes") == expanded_bytes == extracted_bytes
        and receipt.get("treeSha256") == tree_sha256
    ):
        raise SystemExit(1)
PY

[[ -z $(find "$stage_path" -type l -print -quit) ]] || fail EXTRACTED_SYMLINK_REFUSED
[[ -z $(find "$stage_path" ! -type f ! -type d -print -quit) ]] ||
  fail EXTRACTED_SPECIAL_FILE_REFUSED
[[ -z $(find "$stage_path" ! -user root -print -quit) ]] || fail EXTRACTED_OWNER_INVALID
[[ -z $(find "$stage_path" -perm /022 -print -quit) ]] || fail EXTRACTED_WRITABLE_BY_OTHERS
receipt=$stage_path/$receipt_name
[[ -f $receipt && ! -L $receipt && $(stat -c %U:%G "$receipt") == root:root && \
  $(stat -c %a "$receipt") == 600 ]] || fail STAGE_RECEIPT_BOUNDARY_INVALID
trusted_archive=$stage_path/$trusted_archive_name
[[ -f $trusted_archive && ! -L $trusted_archive && \
  $(stat -c %U:%G "$trusted_archive") == root:root && \
  $(stat -c %a "$trusted_archive") == 444 ]] || fail TRUSTED_ARCHIVE_BOUNDARY_INVALID
host_prepare=$stage_path/ops/scripts/v13-host-owner-prepare.sh
[[ -x $host_prepare && -f $host_prepare && ! -L $host_prepare ]] ||
  fail HOST_PREPARE_ENTRYPOINT_INVALID

if [[ $stage_action == STAGE_NEW ]]; then
  mv "$incoming" "$destination"
  stage_path=$destination
fi
trap - EXIT

if ! PREPARE_V13_HOST=PREPARE-V13-HOST \
  "$stage_path/ops/scripts/v13-host-owner-prepare.sh" "$stage_path"; then
  fail HOST_PREPARE_FAILED
fi
printf 'v13_friend_bootstrap=PASS\nrelease_staged=%s\ndeploy_executed=NO\n' \
  "${stage_action/STAGE_NEW/PASS}"
