#!/usr/bin/env bash
set -euo pipefail

unit_dir=${1:-ops/systemd}
systemd-analyze verify \
  "$unit_dir/calculus-course-assistant.service" \
  "$unit_dir/calculus-dump-bot.service" \
  "$unit_dir/calculus-data-bridge.service"
