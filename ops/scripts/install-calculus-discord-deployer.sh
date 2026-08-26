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

fail() {
  printf 'installer_error=%s\n' "$1" >&2
  exit 2
}

[[ ${EUID} -eq 0 ]] || fail ROOT_REQUIRED
[[ $# -eq 1 ]] || fail ARGUMENTS_INVALID
[[ ${INSTALL_CALCULUS_DEPLOYER:-} == INSTALL-CALCULUS-DEPLOYER ]] ||
  fail EXACT_APPROVAL_REQUIRED
[[ $(hostname) == jerrymk-workstation ]] || fail WRONG_HOST
[[ ! -e /usr/local/sbin/calculus-discord-deploy ]] || fail DEPLOYER_ALREADY_PRESENT
[[ ! -e /etc/sudoers.d/calculus-discord-deploy ]] || fail SUDOERS_RULE_ALREADY_PRESENT
id ding >/dev/null 2>&1 || fail DEPLOY_USER_MISSING

source_release=$(realpath -e "$source_release")
[[ $source_release == /home/ding/calculus-discord-staging/releases/* ]] ||
  fail RELEASE_PATH_REFUSED

deployer_source=$source_release/ops/scripts/calculus-discord-deploy
sudoers_source=$source_release/ops/sudoers/calculus-discord-deploy
[[ -f $deployer_source && ! -L $deployer_source ]] || fail DEPLOYER_SOURCE_MISSING
[[ -f $sudoers_source && ! -L $sudoers_source ]] || fail SUDOERS_SOURCE_MISSING
bash -n "$deployer_source" || fail DEPLOYER_SYNTAX_INVALID
visudo -cf "$sudoers_source" >/dev/null || fail SUDOERS_SOURCE_INVALID

getent group calculus-builder >/dev/null || groupadd --system calculus-builder
id calculus-builder >/dev/null 2>&1 ||
  useradd --system --gid calculus-builder \
    --home-dir /var/lib/calculus-discord-build --shell /usr/sbin/nologin calculus-builder
install -d -o calculus-builder -g calculus-builder -m 0700 \
  /var/lib/calculus-discord-build
[[ $(id -gn calculus-builder) == calculus-builder ]] || fail BUILD_USER_GROUP_INVALID
[[ $(getent passwd calculus-builder | cut -d: -f7) == /usr/sbin/nologin ]] ||
  fail BUILD_USER_SHELL_INVALID
install -d -o root -g root -m 0711 /var/lib/calculus-discord-deploy

installer_complete=0
files_promoted=0
cleanup_installer() {
  local result=$?
  if [[ $result -ne 0 && $installer_complete -eq 0 ]]; then
    rm -f -- \
      /usr/local/sbin/calculus-discord-deploy.incoming \
      /etc/sudoers.d/calculus-discord-deploy.incoming
    if [[ $files_promoted -eq 1 ]]; then
      rm -f -- \
        /usr/local/sbin/calculus-discord-deploy \
        /etc/sudoers.d/calculus-discord-deploy
    fi
  fi
  return "$result"
}
trap cleanup_installer EXIT

install -o root -g root -m 0755 "$deployer_source" \
  /usr/local/sbin/calculus-discord-deploy.incoming
install -o root -g root -m 0440 "$sudoers_source" \
  /etc/sudoers.d/calculus-discord-deploy.incoming
visudo -cf /etc/sudoers.d/calculus-discord-deploy.incoming >/dev/null ||
  fail SUDOERS_INCOMING_INVALID

files_promoted=1
mv /usr/local/sbin/calculus-discord-deploy.incoming \
  /usr/local/sbin/calculus-discord-deploy
mv /etc/sudoers.d/calculus-discord-deploy.incoming \
  /etc/sudoers.d/calculus-discord-deploy
visudo -cf /etc/sudoers.d/calculus-discord-deploy >/dev/null ||
  fail SUDOERS_INSTALL_INVALID

installer_complete=1
trap - EXIT
printf 'deploy_entry=INSTALLED\nnew_port=NO\nsecrets_changed=NO\nsystemd_units_changed=NO\n'
printf 'deploy_executed=NO\n'
