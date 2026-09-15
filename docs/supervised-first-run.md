# Supervised first overnight run

Full zero→live list: [go-live.md](go-live.md).

Before enabling unattended cron:

1. Confirm Phases 0–2 green (SSH, Ollama coder model, Hermes tool-use smoke, Telegram ping).
2. Wire **real** Cursor + Grok Bot delegate cmds (stubs only log payloads).
3. Put **one** tiny Ready + Local-safe task in Build Queue (docs or fixture).
4. Stay awake nearby for the first `overnight_run.sh` / timer fire.
5. Verify:
   - Branch created (not on `main`)
   - Checks ran
   - PR opened **or** Escalation Log written (Cursor or Grok Bot)
   - Agent Runs row exists
   - Telegram digest received
6. Second night: one Cloud-only task to confirm cheaper-first cloud handoff.
7. Only then: raise `AUTOCODE_MAX_TASKS_PER_NIGHT` and leave the timer enabled.
