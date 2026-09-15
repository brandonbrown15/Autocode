# Autocode

Overnight coding autopilot for a Jetson (or any Linux + GPU box).

It reads tasks from **your** Notion list, codes with a **local** AI, opens GitHub PRs, and can text you in the morning.

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
./scripts/ui.sh              # open http://127.0.0.1:8787/ dashboard
./scripts/status.sh          # what is it doing?
./scripts/control.sh pause   # stop for a bit
./scripts/doctor.sh          # is anything broken?
```

Add work in Notion → **Build Queue** → Status = **Ready**.

Dashboard docs: **[docs/ui.md](docs/ui.md)**

## How the AIs talk

Hermes only talks to **local Ollama**.  
The night orchestrator decides when to call Cursor / Grok / a human.  
→ [docs/how-ai-talks.md](docs/how-ai-talks.md)

## Optional later

- Notion browser sign-in: `./scripts/connect_notion.sh`
- Cursor / Grok webhooks → [docs/go-live.md](docs/go-live.md)
- Phone remote control → [docs/remote-ops.md](docs/remote-ops.md)
- Jetson + 4TB SSD → [docs/jetson.md](docs/jetson.md)

## License

[MIT](LICENSE)
