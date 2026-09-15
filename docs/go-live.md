# What’s left to go live (Cursor + Grok Bot)

Goal: Jetson overnight loop that does local Hermes first, then delegates to
**whichever of Cursor Ultra / Grok Bot is cheaper for that rung**, and only pages you when both fail.

Recommended `.env` for your plan:

```bash
AUTOCODE_COST_PROFILE=cursor-grok
AUTOCODE_CLOUD_PREFERENCE=cursor          # swap to grok if Bot is flatter/cheaper
AUTOCODE_DISABLE_METERED_GROK=1            # block raw XAI_API_KEY overnight
AUTOCODE_CURSOR_DELEGATE_CMD='./scripts/delegate_cursor_stub.sh'   # replace with real launcher
AUTOCODE_GROK_DELEGATE_CMD='./scripts/delegate_grok_stub.sh'       # replace with real Bot webhook
# Leave empty overnight:
# XAI_API_KEY=
# ANTHROPIC_API_KEY=
```

Cheaper-first ladder: **Local → Cursor Cloud → Grok Bot → Human**.

---

## Checklist (do in order)

### A. Host (Jetson)

- [ ] JetPack / MAXN, NVMe, SSH solid (`./bootstrap/00_check_jetson.sh` or `docs/jetson.md`)
- [ ] Swap sized (`./bootstrap/01_setup_swap.sh`)
- [ ] Clone Autocode to e.g. `/opt/autocode`, copy `.env.example` → `.env`

### B. Local AI stack

- [ ] Ollama installed + `coder-64k` (or your `OLLAMA_MODEL`) pulled and answering
- [ ] **Hermes actually installed** (repo `hermes/install_hermes.sh` is docs-only today — follow official Hermes install)
- [ ] Hermes pointed at local Ollama (`hermes/configure_local_primary.sh` + interactive model setup)
- [ ] Smoke: Hermes can edit a file in a test repo with tools

### C. Notion (required for live, not mock)

- [ ] Integration created; shared on Build Queue / Agent Runs / Escalation Log
- [ ] `NOTION_TOKEN` + three DB IDs in `.env` (see `docs/notion-setup.md`)
- [ ] One tiny **Ready + Local-safe** task for first night
- [ ] Optional: set **Model route = Cursor Cloud** or **Grok** on a row to force a cloud path

### D. GitHub / workspaces

- [ ] `gh auth login` (or deploy key) on the Jetson
- [ ] `WORKSPACE_REPOS=...` filled
- [ ] `./scripts/clone_workspaces.sh` succeeded

### E. Cloud delegates (the big remaining code gap)

Stubs succeed without doing work. Replace them:

| Target | Env | What “real” looks like |
|--------|-----|-------------------------|
| Cursor Cloud | `AUTOCODE_CURSOR_DELEGATE_CMD` | Script that starts a Cursor Cloud / Background Agent (or webhook) with `$AUTOCODE_DELEGATE_PAYLOAD` |
| Grok Bot | `AUTOCODE_GROK_DELEGATE_CMD` | Your Telegram/webhook/SuperGrok bot that accepts the same JSON payload |

Keep `AUTOCODE_DISABLE_METERED_GROK=1` so overnight never hits uncapped `XAI_API_KEY`.

### F. Remote monitor / intervene (so you’re not glued to the Jetson)

- [ ] Install **Tailscale** (or similar) on the Jetson for SSH from your phone/laptop — see [remote-ops.md](remote-ops.md)
- [ ] Set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` for progress pings + digest
- [ ] Smoke: `./scripts/control.sh ping` and `./scripts/status.sh`
- [ ] Know the intervene cmds: `pause` / `resume` / `skip BLD-…` / `abort`

### G. Dry runs → supervised night → timer

1. `./scripts/setup.sh --check` (or `./scripts/demo_night.sh`) — mock night OK  
2. `./cron/overnight_run.sh --dry-run` against live Notion (route only)  
3. Supervised: one Local-safe task, stay nearby (`docs/supervised-first-run.md`)  
4. Supervised: one Cloud-only task → confirm Cursor **or** Grok Bot payload + Escalation Log  
5. Only then: `./cron/install_autopilot_timers.sh`

---

## Already done in this repo

- Cost scoring + `cursor-grok` / `cursor-ultra` profiles  
- Overnight orchestrator with local retries + health gates  
- Notion claim / escalate / agent-run helpers  
- Mock demo + unit tests  
- systemd timer unit files  
- Stub delegate scripts (shape of the handoff)  
- Remote status heartbeat + pause/abort/skip + Telegram progress hooks  

## Still on you (operator)

1. Real Hermes install + Ollama model on the Jetson  
2. Real Notion DBs + token  
3. Real Cursor launcher (not stub)  
4. Real Grok Bot webhook (not stub)  
5. Tailscale (or SSH tunnel) + Telegram for remote watch  
6. First supervised night, then enable the timer  

**Not plug-and-play:** cloning the repo onto the Jetson alone will **not** start useful overnight coding until A–E above are done. Mock mode (`./scripts/demo_night.sh`) works immediately to prove the loop.

Until E is real, cloud escalations only write payloads under `state/delegates/` and log to Notion — they won’t finish coding in Cursor/Grok unattended.
