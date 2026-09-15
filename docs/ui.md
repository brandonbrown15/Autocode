# Autocode local UI

A kid-simple dashboard that runs **on the Jetson** (or any Linux box).

```bash
./scripts/ui.sh
# open http://127.0.0.1:8787/
```

## What it does

- Live phase / task / route / heartbeat (same data as `./scripts/status.sh`)
- Pause · Resume · Abort · Skip task
- Ready checklist (Notion, Hermes, Ollama, GitHub, autopilot)
- One-click **mock night** (`./scripts/demo_night.sh`)
- Tail of the latest night / demo log

## Remote phone / laptop

Keep the UI bound to localhost (default). Tunnel with Tailscale SSH:

```bash
ssh -L 8787:127.0.0.1:8787 jetson
# then open http://127.0.0.1:8787/ on your laptop
```

To bind on LAN intentionally: `AUTOCODE_UI_HOST=0.0.0.0 ./scripts/ui.sh`  
(Only do this on a trusted network.)

## Env

| Variable | Default | Meaning |
|----------|---------|---------|
| `AUTOCODE_UI_HOST` | `127.0.0.1` | Bind address |
| `AUTOCODE_UI_PORT` | `8787` | Port |

Mutating actions require a session token injected into the page (localhost CSRF guard).
