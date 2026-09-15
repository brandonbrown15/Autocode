# Remote monitoring & intervention

**Short answer:** Autocode is not plug-and-play on a fresh Jetson yet (see [go-live.md](go-live.md)). Once a night is running, you *can* watch and intervene remotely.

## How to watch (cloud + SSH)

| Channel | What you see | Setup |
|---------|--------------|--------|
| **Notion** | Build Queue status, Agent Runs, Escalation Log | Required for live nights |
| **Telegram** | Night start / per-task route / pause-abort / digest | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` |
| **Tailscale SSH** | Live heartbeat, logs, pause/abort/skip | Install Tailscale on Jetson + phone/laptop |

Recommended: **Tailscale** on the Jetson (always-on SSH from your phone). Notion is the task board; Telegram is the pager; **`./scripts/ui.sh`** is the live control panel ([ui.md](ui.md)).

```bash
# On Jetson (one-time)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Then from anywhere:

```bash
ssh jetson
cd /opt/autocode   # or your clone path
./scripts/ui.sh                 # dashboard on the Jetson
# or tunnel from your laptop:
#   ssh -L 8787:127.0.0.1:8787 jetson
./scripts/status.sh
tail -f logs/nightly-*.log
```

## Live status

```bash
./scripts/status.sh
# or
python3 -m orchestrator.ops status
```

Writes/reads `state/status.json`:

- `phase` — idle / starting / routing / running_local / escalating / paused / done / aborted  
- `task_id` / `route` / `detail`  
- `heartbeat_at` — if older than `AUTOCODE_STUCK_SECONDS` (default 900) while running → **stuck?**

## Intervene

```bash
./scripts/control.sh pause --note "checking PR"
./scripts/control.sh resume
./scripts/control.sh skip BLD-12          # skip when loop reaches it
./scripts/control.sh abort                # stop after current step
./scripts/control.sh clear
./scripts/control.sh ping                 # test Telegram
```

Pause blocks **between** tasks (and while waiting). Abort finishes the current step then stops the night.

## Telegram progress

With tokens set, Autocode pings on:

- night start / finish  
- each task route  
- pause / resume / abort / skip  
- morning digest (existing)

Disable chatter: `AUTOCODE_TELEGRAM_PROGRESS=0`

## Stuck / not working

1. `./scripts/status.sh` — is heartbeat fresh? `stuck?: YES`?  
2. `tail -f logs/nightly-*.log` — Hermes hung? Ollama down?  
3. `./scripts/control.sh pause` then SSH in and inspect the branch/repo  
4. Notion Escalation Log — did it escalate to Cursor/Grok/Human?  
5. If local is thrashing: `./scripts/control.sh abort`, mark the Notion row Blocked / re-route Model route to Cursor Cloud

## Honest “can I start tonight?”

| Mode | Ready now? |
|------|------------|
| `./scripts/demo_night.sh` (mock) | Yes — no Jetson AI / Notion needed |
| Live overnight coding | **Not yet** until go-live checklist (Hermes, Notion, real Cursor/Grok delegates) |
| Remote monitor once live | Yes — this doc + Tailscale + Telegram + Notion |
