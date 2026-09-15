#!/usr/bin/env bash
# Point Hermes primary model at local Ollama coder-64k.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"

MODEL="${OLLAMA_MODEL:-coder-64k}"
BASE_URL="http://${OLLAMA_HOST:-127.0.0.1:11434}/v1"
HERMES_DIR="${HERMES_CONFIG_DIR:-$HOME/.hermes}"

mkdir -p "$HERMES_DIR"
mkdir -p "$HERMES_DIR" 2>/dev/null || true

# Persist timeout for slow Jetson turns
ENV_FILE="$HERMES_DIR/.env"
touch "$ENV_FILE"
grep -q '^HERMES_API_TIMEOUT=' "$ENV_FILE" 2>/dev/null \
  || echo "HERMES_API_TIMEOUT=${HERMES_API_TIMEOUT:-1800}" >>"$ENV_FILE"

STUB="$ROOT/hermes/config.stub.yaml"
TARGET="$HERMES_DIR/autocode.stub.yaml"
cp "$STUB" "$TARGET"
echo "Wrote stub config: $TARGET"
echo "Complete interactive setup:"
echo "  hermes model"
echo "  → custom endpoint: $BASE_URL"
echo "  → model: $MODEL"
echo "  → leave API key empty"
echo
echo "Acceptance test:"
echo "  hermes chat -q \"List files here, read README.md, report the project name.\""
echo "Confirm Hermes used file/terminal tools — not just chat prose."
