# Autocode local UI

Kid-simple dashboard that runs **on the Jetson** (or any Linux box).

```bash
./scripts/ui.sh
# open http://127.0.0.1:8787/
```

Keep it running in the background (recommended for remote monitoring):

```bash
# installs overnight + continuous worker timers AND the UI service
./cron/install_autopilot_timers.sh
# or UI only:
systemctl --user enable --now autocode-ui.service   # after install rewrites paths
```

## What it does

- Live phase / task / route / heartbeat (same as `./scripts/status.sh`)
- Pause · Resume · Abort · Skip task
- Ready checklist (Notion, Hermes, Ollama, GitHub, autopilot / continuous)
- **Run work cycle** — pick the next Ready Notion task now
- Mock night for dry practice
- Tail of the latest log

## Remote monitoring (phone / laptop)

### Option A — Tailscale (recommended)

Same private network as the Jetson, no public internet exposure:

```bash
# On Jetson
./bootstrap/04_install_tailscale.sh
sudo tailscale up
./scripts/ui.sh --remote
# note the http://100.x.y.z:8787/ URL printed
```

From your phone/laptop (also on Tailscale), open that URL.

Always-on:

```bash
# in .env
AUTOCODE_UI_REMOTE=1
./cron/install_autopilot_timers.sh   # enables autocode-ui.service
```

Optional: `tailscale serve` / `tailscale funnel` if you want HTTPS on your Tailnet.

### Option B — SSH tunnel (safest default)

```bash
ssh -L 8787:127.0.0.1:8787 jetson
# open http://127.0.0.1:8787/ on your laptop
```

### Option C — Public internet (optional)

Only if you need access outside Tailscale. Prefer a **Cloudflare Tunnel** (or similar) in front of localhost:8787 rather than opening a raw port. The UI CSRF token is not a full auth system.

```bash
# Example sketch — install cloudflared, then:
cloudflared tunnel --url http://127.0.0.1:8787
```

Do **not** bind `0.0.0.0` on a public IP without a tunnel + access policy.

## Env

| Variable | Default | Meaning |
|----------|---------|---------|
| `AUTOCODE_UI_HOST` | `127.0.0.1` | Bind address |
| `AUTOCODE_UI_PORT` | `8787` | Port |
| `AUTOCODE_UI_REMOTE` | `0` | `1` = prefer Tailscale IP / LAN bind |

Mutating actions require a session token injected into the page (CSRF guard).
