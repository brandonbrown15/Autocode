# Autocode

**Open-source overnight coding autopilot** for a local AI box (designed for [Jetson Orin Nano Super](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/), usable on other Linux + GPU hosts).

Runs [Hermes Agent](https://hermes-agent.ai) against a **local** Ollama coder, pulls work from **your** Notion Build Queue, opens PRs, and can send a morning Telegram digest. Hard tasks escalate. **Secrets never live in git.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Why Autocode

- **Free local coding** for small, Local-safe tasks
- **Overnight cron** so work moves while you sleep
- **Bring your own** Notion + Telegram + repos (no vendor lock-in)
- **Guardrails**: no direct `main` merges, budget caps, escalation log

## Quick start

```bash
git clone https://github.com/brandonbrown15/Autocode.git
cd Autocode
./scripts/setup.sh          # creates local .env (gitignored)
# edit .env — see docs/notion-setup.md
./scripts/setup.sh --check  # verify layout + no secrets tracked
```

### On the Jetson (or Linux aarch64/x86_64 host)

```bash
./bootstrap/00_check_jetson.sh
./ollama/install_ollama_jetson.sh
./ollama/create_coder_64k.sh
./hermes/install_hermes.sh
./hermes/configure_local_primary.sh
# optional: ./hermes/configure_fallbacks.sh
./cron/install_autopilot_timers.sh
```

First overnight run: stay nearby — [docs/supervised-first-run.md](docs/supervised-first-run.md).

## What you configure (local only)

| Variable | Purpose |
|----------|---------|
| `NOTION_TOKEN` + DB IDs | Your Build Queue / Agent Runs / Escalation Log |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Optional morning digest |
| `WORKSPACE_REPOS` | Git repos Hermes may edit |
| Paid API keys | Optional fallbacks — leave empty at first |

Templates: [`.env.example`](.env.example), [`notion/ids.example.yaml`](notion/ids.example.yaml).  
**Never commit** `.env` or `notion/ids.yaml`.

## Repo layout

| Path | Purpose |
|------|---------|
| `scripts/setup.sh` | One-command local setup + hygiene check |
| `bootstrap/` | Host checks + swap helper |
| `ollama/` | Ollama install + `coder-64k` Modelfile |
| `hermes/` | Hermes config stubs |
| `notion/` | REST helpers (token from env only) |
| `cron/` | Overnight systemd timer |
| `orchestrator/` | Local-first router + cloud escalation |
| `docs/` | Guardrails, Notion schema, security, routing |

## Independent overnight loop

```bash
./scripts/demo_night.sh           # simulate full night (no Jetson/Notion needed)
./cron/overnight_run.sh --dry-run # route only against live Notion
./cron/overnight_run.sh           # live overnight
python3 orchestrator/run_night.py --mock
```

Local Hermes handles Local-safe work (with retries). Harder work is scored and sent up a **cost ladder** — Grok (cheap) → Claude (mid-range) → Cursor Cloud (premium) — so mid tasks don’t burn premium models. See [docs/routing.md](docs/routing.md).

## Guardrails

- Never push/merge `main` directly
- Never invent or rotate secrets
- Max 1–2 Ready tasks per night at first
- Prefer tiny PRs; escalate after two local failures

Details: [docs/guardrails.md](docs/guardrails.md) · [docs/security.md](docs/security.md)

## Docs

- [Notion setup](docs/notion-setup.md) — recreate databases in *your* workspace
- [Routing / escalation](docs/routing.md) — local vs cloud decision tree
- [Architecture](docs/architecture.md)
- [Jetson notes](docs/jetson.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## License

[MIT](LICENSE) — contributions welcome.
