#!/usr/bin/env bash
# Overnight autopilot entrypoint → orchestrator (local-first + cloud escalate).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"

STATE_DIR="${ROOT}/state"
LOG_DIR="${ROOT}/logs"
mkdir -p "$STATE_DIR" "$LOG_DIR"

STAMP="$(date -Iseconds | tr ':' '-')"
LOG="$LOG_DIR/nightly-${STAMP}.log"

exec > >(tee -a "$LOG") 2>&1

echo "== Autocode overnight run @ $STAMP =="
echo "max_tasks=${AUTOCODE_MAX_TASKS_PER_NIGHT:-2} wall=${AUTOCODE_MAX_WALL_MINUTES:-90}m attempts=${AUTOCODE_MAX_LOCAL_ATTEMPTS:-2}"

EXTRA=("$@")

# Live mode needs Notion; mock/demo does not.
if [[ " ${EXTRA[*]} " != *" --mock "* && -z "${NOTION_TOKEN:-}" ]]; then
  echo "NOTION_TOKEN unset — aborting (configure local .env) or pass --mock"
  exit 1
fi

python3 "$ROOT/orchestrator/run_night.py" "${EXTRA[@]}"
echo "Done. Log: $LOG"
