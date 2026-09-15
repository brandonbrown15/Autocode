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
2. Create branch `hermes/<task-id>-slug`
3. Run Hermes against local Ollama `coder-64k`
4. Open PR with `gh` when possible
5. Mark **Needs review** + log **Agent Runs**

## Escalation / delegation

Writes **Escalation Log** and a JSON payload under `state/delegates/` for a cloud agent.

| Target | Trigger / config |
|--------|------------------|
| Cursor Cloud | `AUTOCODE_CURSOR_DELEGATE_CMD` or `CURSOR_API_KEY` present, or Model route |
| Claude | `ANTHROPIC_API_KEY` |
| Grok Bot | `OPENROUTER_API_KEY` / `XAI_API_KEY` |
| Human | no cloud keys — digest asks you to pick it up |

Set a Cursor handoff command, for example:

```bash
# .env (local only)
AUTOCODE_CURSOR_DELEGATE_CMD='./scripts/delegate_cursor_stub.sh'
```

The stub reads `$AUTOCODE_DELEGATE_PAYLOAD` (JSON with acceptance criteria + context).

## Hardware thresholds (defaults)

Escalate instead of thrashing locally when:

- MemAvailable &lt; ~2.5 GiB
- Free disk &lt; ~5 GiB
- Load average very high vs CPU count
