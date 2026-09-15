# Autocode

Always-on coding autopilot for a Jetson (or any Linux + GPU box).

It reads tasks from **your** Notion project, keeps coding without waiting for you, opens GitHub PRs, runs routine health/bug checks, and can enqueue follow-up checklist items when it spots improvements — until the project is finished.

## Setup (this easy)

```bash
git clone https://github.com/brandonbrown15/Autocode.git
cd Autocode
./start
```

`./start` asks a few questions, then installs everything.

Full kid-simple checklist: **[START_HERE.md](START_HERE.md)**

## After it is running

```bash
./scripts/ui.sh              # dashboard http://127.0.0.1:8787/
./scripts/ui.sh --remote     # phone/laptop via Tailscale
./scripts/status.sh          # what is it doing?
./scripts/control.sh pause   # stop for a bit
./scripts/doctor.sh          # is anything broken?
```

Add work in Notion → **Build Queue** → Status = **Ready**.

Always-on coding: **[docs/continuous.md](docs/continuous.md)** · Dashboard: **[docs/ui.md](docs/ui.md)** · Remote: **[docs/remote-ops.md](docs/remote-ops.md)**

## How the AIs talk

Hermes only talks to **local Ollama**.  
The always-on orchestrator decides when to call Cursor / Grok / a human.  
→ [docs/how-ai-talks.md](docs/how-ai-talks.md)

## Optional later

- Notion browser sign-in: `./scripts/connect_notion.sh`
- Cursor / Grok webhooks → [docs/go-live.md](docs/go-live.md)
- Phone remote control → [docs/remote-ops.md](docs/remote-ops.md)
- Jetson + 4TB SSD → [docs/jetson.md](docs/jetson.md)

## License

[Apache-2.0](LICENSE) — free to use; please keep BrownHawke / Autocode credit
