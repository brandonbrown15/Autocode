#!/usr/bin/env bash
# Soft link / clone target workspaces for Hermes (ROSE, Autocode, etc.).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"

WS="${WORKSPACE_ROOT:-$HOME/workspaces}"
mkdir -p "$WS"

echo "Workspace root: $WS"
echo "Clone coding repos here, e.g.:"
echo "  git clone git@github.com:brandonbrown15/ROSE.git $WS/ROSE"
echo "  # Autocode is this repo — keep a checkout under $WS/Autocode or /opt/autocode"
