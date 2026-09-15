#!/usr/bin/env bash
# Install Hermes Agent (Nous Research). Prefer official installer when available.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"

echo "== Install Hermes Agent =="

if command -v hermes >/dev/null; then
  echo "hermes already installed: $(hermes --version 2>/dev/null || true)"
else
  # Official quick path when Ollama is present:
  if command -v ollama >/dev/null; then
    echo "Tip: ollama launch hermes can install + wire the local endpoint."
  fi
  echo "Install Hermes via the current official docs (pip/uv/installer)."
  echo "Then run: hermes doctor && hermes --version"
  echo "Ref: https://hermes-agent.ai/how-to/use-hermes-with-ollama"
  exit 0
fi

hermes doctor || true
echo "Next: ./hermes/configure_local_primary.sh"
