#!/usr/bin/env bash
set -euo pipefail

mode=${1:---dry-run}
if [[ $mode != --dry-run && $mode != --apply ]]; then
  printf 'usage: %s [--dry-run|--apply]\n' "$0" >&2
  exit 2
fi
printf 'cutover plan: stop old writers -> backup -> transfer -> migrate -> start course assistant -> dump bot -> bridge\n'
if [[ $mode == --dry-run ]]; then
  printf 'dry-run only; no process or database changed\n'
  exit 0
fi
if [[ ${GO_LIVE_CUTOVER:-} != GO-LIVE-CUTOVER ]]; then
  printf 'exact GO-LIVE-CUTOVER authorization is required\n' >&2
  exit 3
fi
printf 'Apply mode is intentionally orchestrated by the operator runbook; no implicit remote target is accepted.\n' >&2
exit 4
