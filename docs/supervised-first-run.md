# Supervised first overnight run

Before enabling unattended cron:

1. Confirm Phases 0–2 green (SSH, Ollama `coder-64k`, Hermes tool-use smoke, Telegram ping).
2. Put **one** tiny Ready + Local-safe task in Build Queue (docs or fixture).
3. Stay awake nearby for the first `overnight_run.sh` / timer fire.
4. Verify:
   - Branch created (not on `main`)
   - Checks ran
   - PR opened **or** Escalation Log written
   - Agent Runs row exists
   - Telegram digest received
5. Only then: raise `AUTOCODE_MAX_TASKS_PER_NIGHT` carefully and leave the timer enabled.
