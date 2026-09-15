#!/usr/bin/env bash
# Example Grok Bot handoff. Replace with your Telegram/webhook/agent launcher.
# Receives AUTOCODE_DELEGATE_PAYLOAD pointing at a JSON escalation file.
set -euo pipefail

PAYLOAD="${AUTOCODE_DELEGATE_PAYLOAD:-}"
if [[ -z "$PAYLOAD" || ! -f "$PAYLOAD" ]]; then
  echo "AUTOCODE_DELEGATE_PAYLOAD missing"
  exit 1
fi

echo "Would hand off to Grok Bot with payload:"
head -c 800 "$PAYLOAD"
echo
echo "(stub) Point AUTOCODE_GROK_DELEGATE_CMD at your real Grok Bot webhook, e.g.:"
echo "  curl -X POST \"\$GROK_BOT_WEBHOOK_URL\" -H 'Content-Type: application/json' -d @\"\$AUTOCODE_DELEGATE_PAYLOAD\""
exit 0
