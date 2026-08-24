#!/usr/bin/env bash
set -euo pipefail
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
LC_ALL=C
export LC_ALL
IFS=$' \t\n'
umask 077
unset BASH_ENV ENV PYTHONHOME PYTHONPATH PIP_CONFIG_FILE

source_release=${1:-}
installed_deployer=/usr/local/sbin/calculus-discord-deploy
expected_old_sha256=f388f862e7951babf4f5dd4d94280142b00c36f7607dc6ece321b130abb6d91e

fail() {
  printf 'repair_error=%s\n' "$1" >&2
  exit 2
}

[[ ${EUID} -eq 0 ]] || fail ROOT_REQUIRED
[[ $# -eq 1 ]] || fail ARGUMENTS_INVALID
[[ ${REPAIR_CALCULUS_DEPLOYER:-} == REPAIR-CALCULUS-DEPLOYER ]] ||
  fail EXACT_APPROVAL_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST
[[ -f $installed_deployer && ! -L $installed_deployer ]] || fail DEPLOYER_MISSING
[[ $(stat -c %U:%G "$installed_deployer") == root:root ]] || fail DEPLOYER_OWNER_INVALID
[[ $(stat -c %a "$installed_deployer") == 755 ]] || fail DEPLOYER_MODE_INVALID
[[ $(sha256sum "$installed_deployer" | cut -d' ' -f1) == "$expected_old_sha256" ]] ||
  fail INSTALLED_DEPLOYER_VERSION_REFUSED

source_release=$(realpath -e "$source_release")
[[ $source_release == /home/ding/calculus-discord-staging/releases/* ]] ||
  fail RELEASE_PATH_REFUSED
deployer_source=$source_release/ops/scripts/calculus-discord-deploy
[[ -f $deployer_source && ! -L $deployer_source ]] || fail DEPLOYER_SOURCE_MISSING
bash -n "$deployer_source" || fail DEPLOYER_SYNTAX_INVALID

incoming=$installed_deployer.incoming
[[ ! -e $incoming ]] || fail DEPLOYER_INCOMING_PRESENT
cleanup_repair() {
  local result=$?
  rm -f -- "$incoming"
  return "$result"
}
trap cleanup_repair EXIT

install -o root -g root -m 0755 "$deployer_source" "$incoming"
[[ $(sha256sum "$incoming" | cut -d' ' -f1) == \
  "$(sha256sum "$deployer_source" | cut -d' ' -f1)" ]] || fail DEPLOYER_COPY_MISMATCH
mv -f "$incoming" "$installed_deployer"
trap - EXIT
printf 'deployer_repair=PASS\nnew_port=NO\nsecrets_changed=NO\nsystemd_units_changed=NO\n'
"$installed_deployer"
