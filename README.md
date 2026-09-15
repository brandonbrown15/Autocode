# Autocode

BrownHawke **Local Coding Machine** — always-on Jetson Orin Nano Super + [Hermes Agent](https://hermes-agent.ai) overnight coding autopilot.

Local models handle simple coding for free. Hard work escalates to Claude / Grok / Cursor Cloud. Progress is tracked in Notion (Build Queue → Agent Runs → Escalation Log).

Notion hub: [Local Coding Machine — Hermes Autopilot](https://app.notion.com/p/3dc9daf596d781d39a62cad3a994e4a4)

## North-star loop

```text
Build Queue (Ready + Local-safe)
  → overnight cron on Jetson
  → Hermes + local Ollama coder-64k
  → branch + tests + PR  |  Escalation Log if stuck
  → morning Telegram digest
  → you review / merge / re-queue
```

## Repo layout

| Path | Purpose |
|------|---------|
| `bootstrap/` | Jetson first-boot: JetPack checks, SSH, MAXN_SUPER, swap |
| `ollama/` | CUDA Ollama install, `coder-64k` Modelfile, keep-alive |
| `hermes/` | Hermes Agent config stubs (local primary + cloud fallbacks) |
| `notion/` | Build Queue / Agent Runs / Escalation Log IDs + API helpers |
| `cron/` | Overnight autopilot unit + digest timer |
| `docs/` | Guardrails, Local-safe definition, Jetson notes |
| `scripts/` | Thin wrappers invoked by cron / systemd |

## Quick start (on the Jetson)

1. Clone this repo onto the Orin Nano Super (NVMe recommended).
2. Copy `.env.example` → `.env` and fill secrets locally (never commit).
3. Run phases in order:

```bash
./bootstrap/00_check_jetson.sh
./ollama/install_ollama_jetson.sh
./ollama/create_coder_64k.sh
./hermes/install_hermes.sh
./hermes/configure_local_primary.sh
# optional: ./hermes/configure_fallbacks.sh
./cron/install_autopilot_timers.sh
```

4. Seed / confirm Ready + Local-safe tasks in Notion Build Queue.
5. First overnight run: supervised (`docs/supervised-first-run.md`).

## Guardrails (non-negotiable)

- Never push or merge `main` directly.
- Never invent or rotate secrets without a human.
- Max **1–2** Ready tasks per night at first.
- Max wall time per task (~45–90 min) and tool iterations (~40).
- Prefer tiny reviewable PRs over unfinished hero branches.
- Local first; paid models only on Cloud-only route, explicit Model route, or two local failures.

## Status

Scaffold for Build Queue **BLD-9**. Hardware install (Phases 0–2) and live cron wiring (Phase 3) land on the Jetson after this repo is cloned there.
