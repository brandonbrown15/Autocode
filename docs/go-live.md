# What’s left to go live (Cursor + Grok Bot)

Goal: Jetson overnight loop that does local Hermes first, then delegates to
**whichever of Cursor Ultra / Grok Bot is cheaper for that rung**, and only pages you when both fail.

## Fast path on the Jetson

```bash
git clone https://github.com/brandonbrown15/Autocode.git /opt/autocode
cd /opt/autocode
./scripts/bootstrap_jetson.sh          # swap, MAXN, Ollama, Hermes, gh, Tailscale, doctor
# edit .env — Notion + CURSOR_WEBHOOK_URL + GROK_BOT_WEBHOOK_URL
gh auth login
sudo tailscale up                      # optional remote SSH
./scripts/demo_night.sh                # mock loop
./scripts/doctor.sh                    # fix FAILs
./cron/overnight_run.sh --force        # one supervised live night
# then:
#   AUTOCODE_AUTOPILOT_ENABLED=1
#   ./cron/install_autopilot_timers.sh
```

Recommended `.env` for your plan:

```bash
AUTOCODE_AUTOPILOT_ENABLED=0           # flip to 1 only after supervised night
AUTOCODE_COST_PROFILE=cursor-grok
AUTOCODE_CLOUD_PREFERENCE=cursor       # swap to grok if Bot is flatter/cheaper
AUTOCODE_DISABLE_METERED_GROK=1        # block raw XAI_API_KEY overnight
AUTOCODE_CURSOR_DELEGATE_CMD=./scripts/delegate_cursor.sh
AUTOCODE_GROK_DELEGATE_CMD=./scripts/delegate_grok.sh
CURSOR_WEBHOOK_URL=https://…           # your Cursor Cloud / Background Agent hook
GROK_BOT_WEBHOOK_URL=https://…         # your Bot / Telegram bridge
# Leave empty overnight:
# XAI_API_KEY=
# ANTHROPIC_API_KEY=
```

Cheaper-first ladder: **Local → Cursor Cloud → Grok Bot → Human**.

---

## Checklist (do in order)

### A. Host (Jetson)

- [ ] JetPack / MAXN, NVMe, SSH solid (`./bootstrap/00_check_jetson.sh` or `docs/jetson.md`)
- [ ] Swap sized (`./bootstrap/01_setup_swap.sh`) — or use `./scripts/bootstrap_jetson.sh`
- [ ] Clone Autocode to e.g. `/opt/autocode`, copy `.env.example` → `.env`

### B. Local AI stack

- [ ] Ollama installed + `coder-64k` pulled (`./ollama/install_ollama_jetson.sh` + `create_coder_64k.sh`)
- [ ] Hermes installed (`./hermes/install_hermes.sh` — real installer, fails if missing)
- [ ] Hermes pointed at local Ollama (`./hermes/configure_local_primary.sh`)
- [ ] Smoke: `./scripts/smoke_hermes.sh`

### C. Notion (required for live, not mock)

- [ ] Integration created; shared on Build Queue / Agent Runs / Escalation Log
- [ ] `NOTION_TOKEN` + three DB IDs in `.env` (see `docs/notion-setup.md`)
- [ ] `python3 notion/client.py doctor` passes
- [ ] One tiny **Ready + Local-safe** task for first night
- [ ] Optional: set **Model route = Cursor Cloud** or **Grok** on a row to force a cloud path

### D. GitHub / workspaces

- [ ] `gh` installed (`./bootstrap/03_install_gh.sh`) + `gh auth login`
- [ ] `WORKSPACE_REPOS=...` filled
- [ ] `./scripts/clone_workspaces.sh` succeeded

### E. Cloud delegates

| Target | Env | Script |
|--------|-----|--------|
| Cursor Cloud | `CURSOR_WEBHOOK_URL` (+ optional token) | `./scripts/delegate_cursor.sh` |
| Grok Bot | `GROK_BOT_WEBHOOK_URL` (+ optional token) | `./scripts/delegate_grok.sh` |

Both scripts POST `$AUTOCODE_DELEGATE_PAYLOAD` JSON and **exit non-zero** if the URL is unset or HTTP is not 2xx. Stubs (`*_stub.sh`) are for mock demos only.

Keep `AUTOCODE_DISABLE_METERED_GROK=1` so overnight never hits uncapped `XAI_API_KEY`.

### F. Remote monitor / intervene

- [ ] Tailscale (`./bootstrap/04_install_tailscale.sh` then `sudo tailscale up`) — [remote-ops.md](remote-ops.md)
- [ ] `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` for progress pings + digest
- [ ] Smoke: `./scripts/control.sh ping` and `./scripts/status.sh`
- [ ] Intervene: `pause` / `resume` / `skip <id>` / `abort`

### G. Dry runs → supervised night → timer

1. `./scripts/setup.sh --check` and `./scripts/demo_night.sh` — mock night OK  
2. `./scripts/doctor.sh` — no FAILs  
3. `./cron/overnight_run.sh --dry-run` against live Notion (route only)  
4. Supervised: `./cron/overnight_run.sh --force` (`docs/supervised-first-run.md`)  
5. Set `AUTOCODE_AUTOPILOT_ENABLED=1`, then `./cron/install_autopilot_timers.sh`  

The timer **no-ops** while `AUTOCODE_AUTOPILOT_ENABLED` is not `1` (exit 0, no work).

---

## Already done in this repo

- One-shot `./scripts/bootstrap_jetson.sh` + `./scripts/doctor.sh`
- Real Hermes install + local Ollama config writers + smoke
- Webhook delegates (honest failure without URL)
- Cost scoring + `cursor-grok` / `cursor-ultra` profiles  
- Overnight orchestrator with local retries + health gates + autopilot safety flag  
- Notion claim / escalate / agent-run / doctor helpers  
- Mock demo + unit tests  
- systemd timer unit files  
- Remote status heartbeat + pause/abort/skip + Telegram progress hooks  

## Still on you (operator)

1. Run bootstrap on the Jetson (this cloud agent cannot SSH your device)  
2. Notion DBs + token + share the integration  
3. Your Cursor / Grok Bot webhook endpoints + credentials  
4. `gh auth login` + workspace clones  
5. First supervised night, then enable the timer  

**Mock mode** (`./scripts/demo_night.sh`) works immediately to prove the loop without Jetson hardware.
