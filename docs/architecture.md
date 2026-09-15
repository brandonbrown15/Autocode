# Architecture

```text
┌─────────────────────────────────────────────────────────┐
│  Notion: Local Coding Machine — Hermes Autopilot        │
│  Build Queue · Agent Runs · Escalation Log              │
└──────────────────────────▲──────────────────────────────┘
                           │ NOTION_TOKEN
┌──────────────────────────┴──────────────────────────────┐
│  Jetson Orin Nano Super (Autocode)                      │
│                                                         │
│  cron/overnight_run.sh                                  │
│       │                                                 │
│       ├─ notion/client.py  list-ready / claim / log     │
│       ├─ Hermes Agent + Ollama coder-64k (local)        │
│       ├─ git branch → tests → gh pr create              │
│       └─ scripts/send_telegram_digest.sh                │
└─────────────────────────────────────────────────────────┘
```

Success metrics (from Notion hub):

- Local absorbs ≥40% of coding turns that currently hit Grok/Claude
- Overnight ≥1 useful PR/day on queued work
- Paid overages drop; zero silent merges to `main`
