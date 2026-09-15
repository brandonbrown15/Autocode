#!/usr/bin/env bash
# Launch the Autocode local dashboard.
# Usage: ./scripts/ui.sh [--host 127.0.0.1] [--port 8787]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && set -a && source "$ROOT/.env" && set +a

HOST="${AUTOCODE_UI_HOST:-127.0.0.1}"
PORT="${AUTOCODE_UI_PORT:-8787}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--host 127.0.0.1] [--port 8787]"
      echo "Open http://\$HOST:\$PORT/ in a browser on this machine (or via Tailscale SSH -L)."
      exit 0
      ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

export AUTOCODE_UI_HOST="$HOST"
export AUTOCODE_UI_PORT="$PORT"

echo "Starting Autocode UI on http://${HOST}:${PORT}/"
echo "Tip: from your laptop via Tailscale:  ssh -L ${PORT}:127.0.0.1:${PORT} jetson"
exec python3 -m ui.server
