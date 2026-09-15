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
./scripts/status.sh          # what is it doing?
./scripts/control.sh pause   # stop for a bit
./scripts/doctor.sh          # is anything broken?
```

Add work in Notion → **Build Queue** → Status = **Ready**.

## Optional later

- Cursor / Grok webhooks for harder tasks → [docs/go-live.md](docs/go-live.md)
- Phone remote control → [docs/remote-ops.md](docs/remote-ops.md)
- Jetson + 4TB SSD notes → [docs/jetson.md](docs/jetson.md)

## License

[MIT](LICENSE)
