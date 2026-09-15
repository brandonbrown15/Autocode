# Jetson Orin Nano Super notes

Target hardware for Autocode.

## Preferred: one-shot bootstrap

```bash
./scripts/bootstrap_jetson.sh
./scripts/doctor.sh
```

See [go-live.md](go-live.md) for the remaining operator steps (Notion, webhooks, `gh auth`, supervised night).

## Phase 0 checklist

- [ ] Boots from NVMe
- [ ] JetPack 6.x
- [ ] MAXN_SUPER mode via `nvpmodel` (`bootstrap/02_enable_maxn.sh`)
- [ ] Ethernet + SSH keys (+ optional Tailscale)
- [ ] 4–8 GB swap (`bootstrap/01_setup_swap.sh`)

## Phase 1 — local brain

- Jetson-capable Ollama / CUDA
- Tool-capable 3B–7B coder (default Modelfile base: `qwen2.5-coder:7b` — swap if VRAM forces smaller)
- `coder-64k` Modelfile with `num_ctx 65536`
- `OLLAMA_KEEP_ALIVE=24h`
- Smoke `/v1/chat/completions`

**Gotcha:** Ollama `/v1` often ignores per-request `num_ctx` (defaults ~4096). Prefer Modelfile `PARAMETER num_ctx`, `OLLAMA_CONTEXT_LENGTH`, and Hermes native `/api/chat` when available. Verify with `ollama ps`.

## Phase 2 — Hermes

- Primary = local `coder-64k` (`hermes/install_hermes.sh` + `configure_local_primary.sh`)
- Smoke: `scripts/smoke_hermes.sh`
- Fallbacks = Claude / optional Grok only after local works
- Telegram gateway + morning digest

## Phase 3 — autopilot

- Notion Build Queue via `notion/client.py` + `NOTION_TOKEN` (`notion/client.py doctor`)
- Supervised first night (`docs/supervised-first-run.md`) with `./cron/overnight_run.sh --force`
- Set `AUTOCODE_AUTOPILOT_ENABLED=1`, then `cron/install_autopilot_timers.sh`
