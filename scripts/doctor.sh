#!/usr/bin/env bash
# Health doctor for Autocode on Jetson — reports what still blocks go-live.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"

export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:/usr/local/bin:${PATH}"

ok_n=0
warn_n=0
fail_n=0
pass() { echo "  OK   $*"; ok_n=$((ok_n + 1)); }
warn_msg() { echo "  WARN $*"; warn_n=$((warn_n + 1)); }
bad()  { echo "  FAIL $*"; fail_n=$((fail_n + 1)); }

echo "== Autocode doctor =="

# Repo layout
[[ -f .env ]] && pass ".env present" || bad ".env missing (cp .env.example .env)"
[[ -f orchestrator/run_night.py ]] && pass "orchestrator present" || bad "orchestrator/run_night.py missing"

# Host hints
if [[ "$(uname -m)" == "aarch64" ]]; then pass "aarch64"; else warn_msg "not aarch64 (uname=$(uname -m))"; fi
if command -v nvpmodel >/dev/null 2>&1; then pass "nvpmodel available"; else warn_msg "nvpmodel missing (not Jetson?)"; fi
swap_kb=$(awk '/SwapTotal/{print $2}' /proc/meminfo 2>/dev/null || echo 0)
if [[ "${swap_kb:-0}" -ge 2000000 ]]; then pass "swap=${swap_kb}kB"; else warn_msg "swap low (${swap_kb}kB) — run ./bootstrap/01_setup_swap.sh"; fi

# Ollama
HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
MODEL="${OLLAMA_MODEL:-coder-64k}"
if command -v ollama >/dev/null 2>&1; then pass "ollama CLI"; else bad "ollama not installed"; fi
if curl -fsS --max-time 3 "http://${HOST}/api/tags" >/dev/null 2>&1; then
  pass "ollama reachable at $HOST"
  if curl -fsS "http://${HOST}/api/tags" | grep -q "\"${MODEL}\""; then
    pass "model $MODEL present"
  else
    bad "model $MODEL missing — run ./ollama/create_coder_64k.sh"
  fi
else
  bad "ollama not reachable at http://${HOST}"
fi

# Hermes
if command -v hermes >/dev/null 2>&1; then
  pass "hermes on PATH ($(command -v hermes))"
else
  bad "hermes missing — run ./hermes/install_hermes.sh"
fi
[[ -f "${HERMES_CONFIG_DIR:-$HOME/.hermes}/config.yaml" ]] \
  && pass "hermes config.yaml" \
  || warn_msg "no ~/.hermes/config.yaml — run ./hermes/configure_local_primary.sh"

# GitHub
if command -v gh >/dev/null 2>&1; then
  pass "gh CLI"
  if gh auth status >/dev/null 2>&1; then pass "gh authenticated"; else bad "gh not logged in — gh auth login"; fi
else
  bad "gh missing — run ./bootstrap/03_install_gh.sh"
fi

WS="${WORKSPACE_ROOT:-$HOME/workspaces}"
if [[ -n "${WORKSPACE_REPOS:-}" ]]; then
  pass "WORKSPACE_REPOS set"
  missing_ws=0
  for url in $WORKSPACE_REPOS; do
    name="$(basename "$url" .git)"
    [[ -d "$WS/$name/.git" ]] || { warn_msg "workspace not cloned: $WS/$name"; missing_ws=1; }
  done
  [[ "$missing_ws" -eq 0 ]] && pass "workspace clones under $WS"
else
  warn_msg "WORKSPACE_REPOS empty — set in .env then ./scripts/clone_workspaces.sh"
fi

# Notion
if [[ -n "${NOTION_TOKEN:-}" && -n "${NOTION_BUILD_QUEUE_DB:-}" ]]; then
  if python3 "$ROOT/notion/client.py" doctor; then
    pass "Notion doctor"
  else
    bad "Notion doctor failed — check token + DB shares (docs/notion-setup.md)"
  fi
else
  warn_msg "Notion not configured (mock nights still work)"
fi

# Cloud delegates
CURSOR_CMD="${AUTOCODE_CURSOR_DELEGATE_CMD:-}"
GROK_CMD="${AUTOCODE_GROK_DELEGATE_CMD:-}"
if [[ -n "$CURSOR_CMD" ]]; then
  if [[ "$CURSOR_CMD" == *stub* ]]; then
    warn_msg "Cursor delegate is stub — set CURSOR_WEBHOOK_URL + ./scripts/delegate_cursor.sh"
  else
    pass "AUTOCODE_CURSOR_DELEGATE_CMD set"
  fi
else
  warn_msg "Cursor delegate unset — cloud Cursor escalations will fall through"
fi
if [[ -n "${CURSOR_WEBHOOK_URL:-}" ]]; then
  pass "CURSOR_WEBHOOK_URL set"
elif [[ -n "$CURSOR_CMD" && "$CURSOR_CMD" != *stub* ]]; then
  warn_msg "CURSOR_WEBHOOK_URL empty (ok if custom launcher needs no URL)"
fi

if [[ -n "$GROK_CMD" ]]; then
  if [[ "$GROK_CMD" == *stub* ]]; then
    warn_msg "Grok Bot delegate is stub — set GROK_BOT_WEBHOOK_URL + ./scripts/delegate_grok.sh"
  else
    pass "AUTOCODE_GROK_DELEGATE_CMD set"
  fi
else
  warn_msg "Grok Bot delegate unset"
fi
if [[ -n "${GROK_BOT_WEBHOOK_URL:-}" ]]; then
  pass "GROK_BOT_WEBHOOK_URL set"
fi

if [[ -n "${XAI_API_KEY:-}" && "${AUTOCODE_DISABLE_METERED_GROK:-1}" != "1" ]]; then
  warn_msg "XAI_API_KEY set with metered Grok enabled — costly for overnight agents"
fi

# Autopilot safety
if [[ "${AUTOCODE_AUTOPILOT_ENABLED:-0}" == "1" ]]; then
  pass "AUTOCODE_AUTOPILOT_ENABLED=1 (timer allowed)"
else
  warn_msg "AUTOCODE_AUTOPILOT_ENABLED!=1 — timer will no-op until you enable it"
fi

# Remote ops
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
  pass "Telegram configured"
else
  warn_msg "Telegram unset — no remote progress pings"
fi
if command -v tailscale >/dev/null 2>&1; then
  if tailscale status >/dev/null 2>&1; then pass "Tailscale up"; else warn_msg "Tailscale installed but not up"; fi
else
  warn_msg "Tailscale missing — run ./bootstrap/04_install_tailscale.sh for remote SSH"
fi

echo
echo "Summary: OK=$ok_n WARN=$warn_n FAIL=$fail_n"
if [[ "$fail_n" -gt 0 ]]; then
  echo "Not go-live ready. Fix FAILs then re-run: ./scripts/doctor.sh"
  exit 1
fi
echo "No hard FAILs. Review WARNs, then supervised night: docs/supervised-first-run.md"
exit 0
