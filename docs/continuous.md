# Continuous coding (not just overnight)

Autocode can work the Build Queue **any time**, not only at 01:00.

```text
Notion Ready tasks
        │
        ├─ continuous worker  (~every 30 min)  ← daytime / always-on
        └─ overnight batch    (01:00)          ← bigger night run
                │
                ▼
        orchestrator → Hermes/Ollama or escalate
```

## Enable

In `.env` (after one supervised run):

```bash
AUTOCODE_AUTOPILOT_ENABLED=1
AUTOCODE_CONTINUOUS_ENABLED=1
AUTOCODE_MAX_TASKS_PER_CYCLE=1   # keep daytime cycles small
AUTOCODE_MAX_TASKS_PER_NIGHT=2   # overnight batch
```

Install timers:

```bash
./cron/install_autopilot_timers.sh
```

That installs:
- `autocode-overnight.timer` — daily 01:00
- `autocode-worker.timer` — ~every 30 minutes
- `autocode-ui.service` — dashboard (set `AUTOCODE_UI_REMOTE=1` for Tailscale)

## Manual cycles

```bash
./cron/worker_run.sh --force          # one live cycle now
./cron/worker_run.sh --dry-run        # route only
./cron/worker_run.sh --mock           # no Notion/Hermes
./cron/overnight_run.sh --force       # full overnight-style batch
```

Or tap **Run work cycle** in the UI.

## Safety

- Both paths share `state/run.lock` — they never overlap.
- Timers no-op until `AUTOCODE_AUTOPILOT_ENABLED=1`.
- Continuous ticks no-op until `AUTOCODE_CONTINUOUS_ENABLED=1`.
- Pause / abort / skip still work via UI, `./scripts/control.sh`, or Telegram.

## Remote watch

See [ui.md](ui.md) and [remote-ops.md](remote-ops.md) — Tailscale + dashboard is the intended phone view.
