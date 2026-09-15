#!/usr/bin/env bash
# Overnight autopilot entrypoint — pull Ready Local-safe work, run Hermes, log results.
# Guardrails: never touch main; max tasks / wall time from .env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"

MAX_TASKS="${AUTOCODE_MAX_TASKS_PER_NIGHT:-2}"
MAX_WALL="${AUTOCODE_MAX_WALL_MINUTES:-90}"
BRANCH_PREFIX="${AUTOCODE_BRANCH_PREFIX:-hermes}"
STATE_DIR="${ROOT}/state"
LOG_DIR="${ROOT}/logs"
mkdir -p "$STATE_DIR" "$LOG_DIR"

STAMP="$(date -Iseconds)"
LOG="$LOG_DIR/nightly-${STAMP}.log"
DIGEST="$STATE_DIR/digest-${STAMP}.txt"

exec > >(tee -a "$LOG") 2>&1

echo "== Autocode overnight run @ $STAMP =="
echo "max_tasks=$MAX_TASKS max_wall_min=$MAX_WALL"

if [[ -z "${NOTION_TOKEN:-}" ]]; then
  echo "NOTION_TOKEN unset — aborting (configure .env on Jetson)."
  exit 1
fi

mapfile -t READY < <(python3 "$ROOT/notion/client.py" list-ready | awk '/^BLD-/ {print}' || true)
if [[ ${#READY[@]} -eq 0 ]]; then
  echo "No Ready + Local-safe tasks." | tee "$DIGEST"
  "$ROOT/scripts/send_telegram_digest.sh" "$DIGEST" || true
  exit 0
fi

count=0
: >"$DIGEST"
echo "Autocode digest $STAMP" >>"$DIGEST"

for line in "${READY[@]}"; do
  [[ "$count" -ge "$MAX_TASKS" ]] && break
  count=$((count + 1))

  # list-ready prints: BLD-n\tname\t... then next line "  id=..."
  # Re-query with python for structured pickup in a later iteration; stub loop for scaffold.
  echo "Would process: $line" | tee -a "$DIGEST"
done

echo
echo "Scaffold note: full Hermes invoke + git branch/PR automation lands in Phase 3."
echo "Tonight this entrypoint proves timers + Notion list-ready + digest plumbing."
echo "Branch pattern when live: ${BRANCH_PREFIX}/<task-id>-short-slug"
echo "Wall budget reminder: ${MAX_WALL} minutes / task"

"$ROOT/scripts/send_telegram_digest.sh" "$DIGEST" || true
echo "Done."
