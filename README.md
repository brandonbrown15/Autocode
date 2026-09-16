# Hawkeye

**Private** personal coding autopilot for BrownHawke — local Jetson LLM for free all-day use, with **Cursor** and **Grok Bot** taking over when a task is too hard. Login-gated UI on your own domain.

This is **not** the open-source Autocode repo. Autocode stays public; Hawkeye is your private fork.

Upstream (Apache-2.0, keep credit): [brandonbrown15/Autocode](https://github.com/brandonbrown15/Autocode)

## What you get

| Layer | Behavior |
|-------|----------|
| **Local Ollama** | Free all-day phone/laptop chat + easy Notion tasks |
| **Cursor / Grok Bot** | Escalate strenuous work (webhooks) |
| **Login** | Username/password session on the UI |
| **Domain** | Cloudflare Tunnel → `https://your.domain` → Jetson UI |

## Setup

```bash
# After you create the empty private GitHub repo "Hawkeye":
git clone git@github.com:YOU/Hawkeye.git
cd Hawkeye
./start
python3 scripts/set_private_password.py   # paste hash into .env
# set CURSOR_WEBHOOK_URL + GROK_BOT_WEBHOOK_URL in .env
./scripts/ui.sh --remote
```

Full personal deploy (domain + login + escalate): **[docs/hawkeye.md](docs/hawkeye.md)**

Publishing from an Autocode clone into a new private Hawkeye repo:

```bash
./scripts/publish_hawkeye_private.sh git@github.com:YOU/Hawkeye.git
```

## License

Code inherited from Autocode remains [Apache-2.0](LICENSE) with BrownHawke / Autocode credit. Keep this repository **private**; do not publish secrets (`.env`, webhooks, password hashes).
