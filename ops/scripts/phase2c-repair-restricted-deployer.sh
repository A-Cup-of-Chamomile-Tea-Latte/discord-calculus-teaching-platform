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
installed_sudoers=/etc/sudoers.d/calculus-discord-deploy
expected_old_sha256=05f6375160579374c5341395b53148506c616bcd43743e3ff4d2977ea521d2b6
expected_old_hotfix_sha256=f1ebe3a301ddb93f15af392a72aeb6ccc223c03d1a427005a3325d69b19f2971

fail() {
  printf 'repair_error=%s\n' "$1" >&2
  exit 2
}

[[ ${EUID} -eq 0 ]] || fail ROOT_REQUIRED
[[ $# -eq 1 ]] || fail ARGUMENTS_INVALID
[[ ${REPAIR_CALCULUS_DEPLOYER:-} == REPAIR-CALCULUS-DEPLOYER ]] ||
  fail EXACT_APPROVAL_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST

source_release=$(realpath -e "$source_release")
[[ $source_release == /var/lib/calculus-discord-deploy/releases/* ]] ||
  fail RELEASE_PATH_REFUSED
[[ $(stat -c %U:%G "$source_release") == root:root ]] || fail RELEASE_OWNER_INVALID
[[ -z $(find "$source_release" ! -user root -print -quit) ]] || fail RELEASE_TREE_OWNER_INVALID
[[ -z $(find "$source_release" -perm /022 -print -quit) ]] ||
  fail RELEASE_WRITABLE_BY_OTHERS
deployer_source=$source_release/ops/scripts/calculus-discord-deploy
sudoers_source=$source_release/ops/sudoers/calculus-discord-deploy
[[ -f $deployer_source && ! -L $deployer_source ]] || fail DEPLOYER_SOURCE_MISSING
[[ -f $sudoers_source && ! -L $sudoers_source ]] || fail SUDOERS_SOURCE_MISSING
bash -n "$deployer_source" || fail DEPLOYER_SYNTAX_INVALID
visudo -cf "$sudoers_source" >/dev/null || fail SUDOERS_SOURCE_INVALID

[[ -f $installed_deployer && ! -L $installed_deployer ]] || fail DEPLOYER_MISSING
[[ $(stat -c %U:%G "$installed_deployer") == root:root ]] || fail DEPLOYER_OWNER_INVALID
[[ $(stat -c %a "$installed_deployer") == 755 ]] || fail DEPLOYER_MODE_INVALID
[[ -f $installed_sudoers && ! -L $installed_sudoers ]] || fail SUDOERS_RULE_MISSING
[[ $(stat -c %U:%G "$installed_sudoers") == root:root ]] || fail SUDOERS_OWNER_INVALID
[[ $(stat -c %a "$installed_sudoers") == 440 ]] || fail SUDOERS_MODE_INVALID
visudo -cf "$installed_sudoers" >/dev/null || fail SUDOERS_INSTALLED_INVALID
cmp -s "$sudoers_source" "$installed_sudoers" || fail SUDOERS_RULE_MISMATCH

installed_sha256=$(sha256sum "$installed_deployer" | cut -d' ' -f1)
candidate_sha256=$(sha256sum "$deployer_source" | cut -d' ' -f1)
if [[ $installed_sha256 == "$candidate_sha256" ]]; then
  printf 'deployer_repair=ALREADY_READY\nnew_port=NO\nsecrets_changed=NO\n'
  printf 'systemd_units_changed=NO\ndeploy_executed=NO\n'
  exit 0
fi
[[ $installed_sha256 == "$expected_old_sha256" ||
  $installed_sha256 == "$expected_old_hotfix_sha256" ]] ||
  fail INSTALLED_DEPLOYER_VERSION_REFUSED

incoming=$installed_deployer.incoming
[[ ! -e $incoming ]] || fail DEPLOYER_INCOMING_PRESENT
cleanup_repair() {
  local result=$?
  rm -f -- "$incoming"
  return "$result"
}
trap cleanup_repair EXIT

install -o root -g root -m 0755 "$deployer_source" "$incoming"
[[ $(sha256sum "$incoming" | cut -d' ' -f1) == "$candidate_sha256" ]] ||
  fail DEPLOYER_COPY_MISMATCH
mv -f "$incoming" "$installed_deployer"
[[ $(sha256sum "$installed_deployer" | cut -d' ' -f1) == "$candidate_sha256" ]] ||
  fail DEPLOYER_PROMOTION_MISMATCH
trap - EXIT
printf 'deployer_repair=PASS\nnew_port=NO\nsecrets_changed=NO\nsystemd_units_changed=NO\n'
printf 'deploy_executed=NO\n'
