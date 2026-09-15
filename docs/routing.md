# How Autocode decides local vs cloud

Autocode runs **independently overnight**. It always tries the cheapest safe path first.

```text
Ready task
   │
   ├─ Complexity = Cloud-only ──────────────► escalate
   ├─ Model route ≠ Local Hermes ───────────► escalate
   ├─ Hardware too constrained (RAM/disk/load) ► escalate
   ├─ Local Hermes fails / times out ───────► escalate
   └─ else ─────────────────────────────────► local Hermes → branch → PR
```

## Local path

1. Claim task (`Status = Running`)
2. Health-check Hermes + Ollama (else escalate)
3. Create branch `hermes/<task-id>-slug`
4. Run Hermes against local Ollama `coder-64k` (up to `AUTOCODE_MAX_LOCAL_ATTEMPTS`)
5. Run detected repo checks (`pytest` / `npm test` / …)
6. Open PR with `gh` when possible
7. Mark **Needs review** + log **Agent Runs**

## Escalation / delegation

Writes **Escalation Log** and a JSON payload under `state/delegates/` for a cloud agent.
If the target is **Human**, the Build Queue item is marked **Blocked**.

| Target | Trigger / config |
|--------|------------------|
| Cursor Cloud | `AUTOCODE_CURSOR_DELEGATE_CMD` or `CURSOR_API_KEY` present, or Model route |
| Claude | `ANTHROPIC_API_KEY` |
| Grok Bot | Notion **Model route = Grok**, or keys below (tried in order): `AUTOCODE_GROK_DELEGATE_CMD` → `XAI_API_KEY` (api.x.ai) → `OPENROUTER_API_KEY` |
| Human | no cloud keys — digest asks you to pick it up |

Set a Cursor handoff command, for example:

```bash
# .env (local only)
AUTOCODE_CURSOR_DELEGATE_CMD='./scripts/delegate_cursor_stub.sh'
```

### Grok Bot

Tried in order when a task escalates to **Grok Bot**:

1. `AUTOCODE_GROK_DELEGATE_CMD` — your webhook / Telegram / custom bot
2. `XAI_API_KEY` — direct [xAI API](https://api.x.ai/v1)
3. `OPENROUTER_API_KEY` — OpenRouter model `x-ai/grok-2` (override with `AUTOCODE_OPENROUTER_MODEL`)

```bash
# Direct xAI
XAI_API_KEY=xai-...
AUTOCODE_GROK_MODEL=grok-2-latest

# Or your own Grok Bot webhook
AUTOCODE_GROK_DELEGATE_CMD='./scripts/delegate_grok_stub.sh'
```

In Notion, set **Model route = Grok** on a Build Queue row to force Grok Bot for that task.

The stub reads `$AUTOCODE_DELEGATE_PAYLOAD` (JSON with acceptance criteria + context).

## Hardware thresholds (defaults)

Escalate instead of thrashing locally when:

- MemAvailable &lt; ~2.5 GiB
- Free disk &lt; ~5 GiB
- Load average very high vs CPU count
