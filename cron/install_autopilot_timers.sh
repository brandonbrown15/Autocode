#!/usr/bin/env bash
# Install systemd user/system timers for overnight autopilot.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-user}" # user | system

UNIT_DIR="$HOME/.config/systemd/user"
if [[ "$MODE" == "system" ]]; then
  UNIT_DIR="/etc/systemd/system"
fi

mkdir -p "$UNIT_DIR"
# Rewrite WorkingDirectory to this clone for user installs
sed "s|/opt/autocode|${ROOT}|g" "$ROOT/cron/autocode-overnight.service" >"$UNIT_DIR/autocode-overnight.service"
cp "$ROOT/cron/autocode-overnight.timer" "$UNIT_DIR/autocode-overnight.timer"

if [[ "$MODE" == "system" ]]; then
  sudo systemctl daemon-reload
  sudo systemctl enable --now autocode-overnight.timer
  sudo systemctl list-timers | grep autocode || true
else
  systemctl --user daemon-reload
  systemctl --user enable --now autocode-overnight.timer
  systemctl --user list-timers | grep autocode || true
fi

echo "Installed autocode-overnight.timer ($MODE)."
echo "Dry-run: $ROOT/cron/overnight_run.sh"
