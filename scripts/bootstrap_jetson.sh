#!/usr/bin/env bash
# One-shot Jetson bootstrap for Autocode overnight machine.
# Safe to re-run. Does not create Notion databases or run interactive auth for you.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SKIP_SWAP=0
SKIP_MAXN=0
SKIP_TAILSCALE=0
SKIP_CLONE=0

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap_jetson.sh [options]

Ordered Jetson setup for Autocode:
  1. Dependency check
  2. Swap (recommended 16G)
  3. MAXN SUPER power mode (Jetson)
  4. .env from .env.example (if missing)
  5. Ollama + coder-64k model
  6. Hermes install + local-primary config
  7. Hermes smoke test
  8. GitHub CLI install
  9. Optional Tailscale install
 10. Clone WORKSPACE_REPOS (if configured)
 11. Doctor report

Options:
  --skip-swap         Do not create/enable swap
  --skip-maxn         Do not change nvpmodel
  --skip-tailscale    Do not install Tailscale
  --skip-clone        Do not clone WORKSPACE_REPOS
  -y, --yes           Non-interactive (accepted for compatibility)
  -h, --help          Show help

After this script:
  - Fill Notion + webhook values in .env
  - Run: gh auth login
  - Run: sudo tailscale up   (if using Tailscale)
  - Run: scripts/demo_night.sh
  - Then one supervised live night before enabling the timer
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-swap) SKIP_SWAP=1; shift ;;
    --skip-maxn) SKIP_MAXN=1; shift ;;
    --skip-tailscale) SKIP_TAILSCALE=1; shift ;;
    --skip-clone) SKIP_CLONE=1; shift ;;
    -y|--yes) shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

step() {
  echo
  echo "============================================================"
  echo "▶ $1"
  echo "============================================================"
}

step "1/11 Dependency check"
bash "${ROOT_DIR}/scripts/setup.sh" --check || true

step "2/11 Swap"
if [[ "${SKIP_SWAP}" -eq 1 ]]; then
  echo "Skipped (--skip-swap)."
else
  bash "${ROOT_DIR}/bootstrap/01_setup_swap.sh" || {
    echo "WARN: swap step failed or needs sudo. Continuing."
  }
fi

step "3/11 MAXN SUPER"
if [[ "${SKIP_MAXN}" -eq 1 ]]; then
  echo "Skipped (--skip-maxn)."
else
  bash "${ROOT_DIR}/bootstrap/02_enable_maxn.sh" || {
    echo "WARN: MAXN step skipped/failed (normal on non-Jetson hosts)."
  }
fi

step "4/11 Environment file"
if [[ ! -f "${ROOT_DIR}/.env" ]]; then
  cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
  echo "Created .env from .env.example — edit secrets before a live night."
else
  echo ".env already exists."
fi

if ! grep -q '^AUTOCODE_AUTOPILOT_ENABLED=' "${ROOT_DIR}/.env"; then
  echo 'AUTOCODE_AUTOPILOT_ENABLED=0' >> "${ROOT_DIR}/.env"
fi

step "5/11 Ollama + coder-64k"
bash "${ROOT_DIR}/ollama/install_ollama_jetson.sh" || {
  echo "WARN: Ollama install failed. Install manually, then re-run."
}
# shellcheck disable=SC1091
source "${ROOT_DIR}/.env" 2>/dev/null || true
bash "${ROOT_DIR}/ollama/create_coder_64k.sh" || {
  echo "WARN: model create failed (Ollama may still be starting). Retry later:"
  echo "  bash ollama/create_coder_64k.sh"
}

step "6/11 Hermes install"
bash "${ROOT_DIR}/hermes/install_hermes.sh"

step "7/11 Hermes local-primary config"
bash "${ROOT_DIR}/hermes/configure_local_primary.sh"

step "8/11 Hermes smoke"
if bash "${ROOT_DIR}/scripts/smoke_hermes.sh"; then
  echo "Hermes smoke OK."
else
  echo "WARN: Hermes smoke failed. Fix before a live night."
fi

step "9/11 GitHub CLI"
bash "${ROOT_DIR}/bootstrap/03_install_gh.sh" || {
  echo "WARN: gh install failed."
}

step "10/11 Tailscale (optional)"
if [[ "${SKIP_TAILSCALE}" -eq 1 ]]; then
  echo "Skipped (--skip-tailscale)."
else
  bash "${ROOT_DIR}/bootstrap/04_install_tailscale.sh" || {
    echo "WARN: Tailscale install failed/skipped."
  }
fi

step "11/11 Clone workspaces + doctor"
if [[ "${SKIP_CLONE}" -eq 1 ]]; then
  echo "Clone skipped (--skip-clone)."
else
  bash "${ROOT_DIR}/scripts/clone_workspaces.sh" || {
    echo "WARN: clone skipped (set WORKSPACE_REPOS + gh auth)."
  }
fi

bash "${ROOT_DIR}/scripts/doctor.sh" || true

cat <<'EOF'

============================================================
Bootstrap finished (or as far as this host allows).
============================================================

Remaining operator steps (cannot be fully automated here):

  1. Edit .env — Notion token + database IDs, webhook URLs
  2. gh auth login
  3. sudo tailscale up          # if installed
  4. Create Notion DBs from docs/notion-setup.md (once)
  5. scripts/demo_night.sh      # mock end-to-end
  6. One supervised live night:
       ./cron/overnight_run.sh --force
       # or: python3 -m orchestrator.run_night --once
  7. Enable autopilot when ready:
       set AUTOCODE_AUTOPILOT_ENABLED=1 in .env
       bash cron/install_autopilot_timers.sh

Remote ops:
  scripts/status.sh
  scripts/control.sh pause|resume|abort|skip <task_id>

Docs: docs/go-live.md
EOF
