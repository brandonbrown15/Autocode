# Hawkeye — private personal deploy

Hawkeye is your **private** fork of Autocode:

- **Free local LLM** (Ollama on Jetson) for all-day phone/laptop use  
- **Cursor + Grok Bot** escalate when the ask is too strenuous  
- **Login** on the UI before anything useful loads  
- **Your domain** via Cloudflare Tunnel (or Tailscale)

Open-source Autocode stays a separate public repo. Do not merge Hawkeye-only secrets or personal branding into Autocode `main`.

## 1. Create the private GitHub repo

The cloud agent cannot create private repos with the current GitHub token. On GitHub:

1. **New repository** → name `Hawkeye` → **Private** → create **empty** (no README).  
2. From this tree:

```bash
chmod +x scripts/publish_hawkeye_private.sh
./scripts/publish_hawkeye_private.sh git@github.com:YOUR_USER/Hawkeye.git
```

## 2. Turn on login + product name

```bash
python3 scripts/set_private_password.py
```

Paste into `.env`:

```bash
AUTOCODE_PRODUCT_NAME=Hawkeye
AUTOCODE_PRIVATE_MODE=1
AUTOCODE_PRIVATE_USER=brown
AUTOCODE_PRIVATE_PASSWORD_HASH=pbkdf2_sha256$...
AUTOCODE_PERSONAL_LOCAL_ONLY=0
AUTOCODE_LOCAL_ONLY=0
AUTOCODE_COST_PROFILE=cursor-grok
AUTOCODE_CLOUD_PREFERENCE=cursor
CURSOR_WEBHOOK_URL=https://…
GROK_BOT_WEBHOOK_URL=https://…
AUTOCODE_UI_REMOTE=1
```

`AUTOCODE_PERSONAL_LOCAL_ONLY=1` only if you want to **disable** premium escalate (rare).

## 3. Link your domain

Pick a domain (examples checked available on GoDaddy):

- [brownhawke.ai](https://www.godaddy.com/domainsearch/find?domainToCheck=brownhawke.ai&key=gd_mcp_server&itc=gd_mcp_server)
- [brownhawke.app](https://www.godaddy.com/domainsearch/find?domainToCheck=brownhawke.app&key=gd_mcp_server&itc=gd_mcp_server)
- [personalautocode.com](https://www.godaddy.com/domainsearch/find?domainToCheck=personalautocode.com&key=gd_mcp_server&itc=gd_mcp_server)
- [myautocode.app](https://www.godaddy.com/domainsearch/find?domainToCheck=myautocode.app&key=gd_mcp_server&itc=gd_mcp_server)

Recommended path: **Cloudflare Tunnel** in front of localhost UI (HTTPS + no open Jetson ports):

```bash
# On Jetson — UI on loopback
AUTOCODE_UI_HOST=127.0.0.1 ./scripts/ui.sh

# Install cloudflared, create a named tunnel, route DNS:
#   https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
cloudflared tunnel create hawkeye
cloudflared tunnel route dns hawkeye chat.brownhawke.ai   # example hostname
# config.yml service: http://127.0.0.1:8787
cloudflared tunnel run hawkeye
```

Set `AUTOCODE_UI_SECURE=1` (or rely on `X-Forwarded-Proto: https` from the tunnel) so the login cookie is `Secure`.

Alternative: Tailscale only (`./scripts/ui.sh --remote`) — no public domain required.

## 4. Phone use

1. Open `https://your.domain`  
2. Sign in  
3. Chat hits **local** Ollama first  
4. Hard asks POST to **Cursor** then **Grok Bot** (or reverse if `AUTOCODE_CLOUD_PREFERENCE=grok`)

Same Notion autopilot / continuous drain as Autocode when you enable those flags.

## Env reference

| Variable | Default (Hawkeye) | Meaning |
|----------|-------------------|---------|
| `AUTOCODE_PRODUCT_NAME` | `Hawkeye` | Brand in UI |
| `AUTOCODE_PRIVATE_MODE` | `1` | Require login |
| `AUTOCODE_PRIVATE_USER` | `brown` | Login username |
| `AUTOCODE_PRIVATE_PASSWORD_HASH` | _(required)_ | From `set_private_password.py` |
| `AUTOCODE_PERSONAL_LOCAL_ONLY` | `0` | `1` = never call Cursor/Grok/APIs |
| `AUTOCODE_LOCAL_ONLY` | `0` | Task router: allow cloud delegates |
| `CURSOR_WEBHOOK_URL` | | Premium escalate |
| `GROK_BOT_WEBHOOK_URL` | | Premium escalate |
| `AUTOCODE_UI_SECURE` | `0` | Force Secure cookies |
