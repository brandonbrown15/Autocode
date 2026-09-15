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
# edit .env — NOTION_TOKEN + NOTION_HUB_PAGE + GITHUB_TOKEN (+ repos)
./scripts/setup.sh --check
```

### On the Jetson (fully auto)

```bash
./scripts/go_live.sh --local-only --first-night --enable-autopilot
```

That bootstraps the box, provisions Notion DBs, seeds a Ready task, runs a mock night, optionally one live night, then enables the timer when doctor is green.

First overnight run: stay nearby — [docs/supervised-first-run.md](docs/supervised-first-run.md).  
Remote watch / intervene: [docs/remote-ops.md](docs/remote-ops.md).  
Full checklist: [docs/go-live.md](docs/go-live.md).

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
| `scripts/bootstrap_jetson.sh` | One-shot Jetson bootstrap |
| `scripts/doctor.sh` | Go-live health report |
| `scripts/setup.sh` | Local `.env` + hygiene check |
| `scripts/delegate_*.sh` | Cursor / Grok Bot webhook handoff |
| `bootstrap/` | Host checks, swap, MAXN, gh, Tailscale |
| `ollama/` | Ollama install + `coder-64k` Modelfile |
| `hermes/` | Real install + local Ollama config |
| `notion/` | REST helpers (token from env only) |
| `cron/` | Overnight systemd timer (gated by autopilot flag) |
| `orchestrator/` | Local-first router + cloud escalation |
| `docs/` | Guardrails, Notion schema, security, routing |

## Independent overnight loop

```bash
./scripts/demo_night.sh           # simulate full night (no Jetson/Notion needed)
./cron/overnight_run.sh --dry-run # route only against live Notion
./cron/overnight_run.sh           # live overnight
python3 orchestrator/run_night.py --mock
```

Local Hermes handles Local-safe work (with retries). Harder work goes up a **cost ladder** — **Cursor Ultra** first, then **Grok Bot**, Human last. Metered xAI keys stay off overnight. See [docs/routing.md](docs/routing.md) and [docs/go-live.md](docs/go-live.md).

## Guardrails

- Never push/merge `main` directly
- Never invent or rotate secrets
- Max 1–2 Ready tasks per night at first
- Prefer tiny PRs; escalate after two local failures

Details: [docs/guardrails.md](docs/guardrails.md) · [docs/security.md](docs/security.md)

## Docs

- [Notion setup](docs/notion-setup.md) — recreate databases in *your* workspace
- [Routing / escalation](docs/routing.md) — local vs cloud decision tree
- [Go live checklist](docs/go-live.md) — what’s left for overnight ops
- [Remote ops](docs/remote-ops.md) — Tailscale + Telegram watch / pause / abort
- [Architecture](docs/architecture.md)
- [Jetson notes](docs/jetson.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## License

[MIT](LICENSE) — contributions welcome.
