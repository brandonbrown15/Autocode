# How Autocode decides local vs cloud

Autocode runs **independently overnight** and picks the **cheapest model that can handle the task**.

```text
Ready task
   │
   ├─ score task (Complexity + Priority + keywords + Model route)
   │
   ├─ score < 30  → local Hermes (Jetson / Ollama)
   ├─ score 30–49 → cheap cloud   (Grok Bot)
   ├─ score 50–69 → mid-range     (Claude)     ← too hard for local, not worth Cursor
   ├─ score 70+   → premium       (Cursor Cloud)
   │
   ├─ hardware / Hermes / Ollama unhealthy → same tier, never jump straight to premium
   └─ Notion Model route set explicitly → that target wins
```

## Why mid-range exists

A lot of overnight work is **past local Ollama** (multi-file refactors, tricky APIs) but **does not need Cursor Cloud**. Those land on **Claude** (ladder slot 1) so you save premium spend for architecture, auth, infra, and P0 fires.

| Tier | Default target | Typical tasks |
|------|----------------|---------------|
| local | Local Hermes | typos, docs, small Local-safe edits |
| cheap | Grok Bot | light cloud work / local failed once |
| **standard (mid)** | **Claude** | Maybe-local / Cloud-only without heavy signals |
| premium | Cursor Cloud | P0 + heavy keywords, big architecture, explicit route |
| human | Human | no cloud keys configured |

Override the ladder (cheap → mid → premium → human):

```bash
# .env (local only)
AUTOCODE_COST_LADDER=Grok Bot,Claude,Cursor Cloud,Human
```

## Local path

1. Claim task (`Status = Running`)
2. Health-check Hermes + Ollama (else escalate to scored tier)
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
| Grok Bot | score cheap, or Model route = Grok; keys: `AUTOCODE_GROK_DELEGATE_CMD` → `XAI_API_KEY` → `OPENROUTER_API_KEY` |
| Claude | score mid-range, or Model route = Claude; `ANTHROPIC_API_KEY` |
| Cursor Cloud | score premium, or Model route = Cursor Cloud; `AUTOCODE_CURSOR_DELEGATE_CMD` / `CURSOR_API_KEY` |
| Human | no cloud keys — digest asks you to pick it up |

If the preferred mid-range target isn’t configured, Autocode **falls back to cheaper** before spending on premium.

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

In Notion, set **Model route = Grok** (or Claude / Cursor Cloud) on a Build Queue row to force that target.

The stub reads `$AUTOCODE_DELEGATE_PAYLOAD` (JSON with acceptance criteria + context).

## Scoring cheat sheet

| Signal | Approx. points |
|--------|----------------|
| Local-safe | +10 |
| Maybe local | +40 |
| Cloud-only | +55 (mid floor; not auto-premium) |
| P0 / P1 / P2 | +25 / +15 / +5 |
| Heavy keywords (auth, billing, k8s, …) | +10 each, capped +30 |
| Explicit Model route ≠ Local | floor 55 (mid+) |

## Hardware thresholds (defaults)

Escalate instead of thrashing locally when:

- MemAvailable &lt; ~2.5 GiB
- Free disk &lt; ~5 GiB
- Load average very high vs CPU count

Escalation still respects the score ladder (a light task under low RAM goes to **Grok**, not Cursor).
