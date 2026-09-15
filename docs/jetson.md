# Jetson Orin Nano Super notes

Target hardware for Autocode.

## Phase 0 checklist

- [ ] Boots from NVMe
- [ ] JetPack 6.x
- [ ] MAXN_SUPER mode via `nvpmodel`
- [ ] Ethernet + SSH keys
- [ ] 4–8 GB swap (`bootstrap/01_setup_swap.sh`)

## Phase 1 — local brain

- Jetson-capable Ollama / CUDA
- Tool-capable 3B–7B coder (default Modelfile base: `qwen2.5-coder:7b` — swap if VRAM forces smaller)
- `coder-64k` Modelfile with `num_ctx 65536`
- `OLLAMA_KEEP_ALIVE=24h`
- Smoke `/v1/chat/completions`

**Gotcha:** Ollama `/v1` often ignores per-request `num_ctx` (defaults ~4096). Prefer Modelfile `PARAMETER num_ctx`, `OLLAMA_CONTEXT_LENGTH`, and Hermes native `/api/chat` when available. Verify with `ollama ps`.

## Phase 2 — Hermes

- Primary = local `coder-64k`
- Fallbacks = Claude / optional Grok only after local works
- Telegram gateway + morning digest

## Phase 3 — autopilot

- Notion Build Queue via `notion/client.py` + `NOTION_TOKEN`
- systemd timer `cron/autocode-overnight.timer` (01:00 local)
- Supervised first night (`docs/supervised-first-run.md`)
