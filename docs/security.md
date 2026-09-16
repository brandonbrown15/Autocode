# Security

Autocode is designed so the **public git repo never holds secrets**.

## What belongs in git

- Scripts, Modelfiles, docs, `.env.example`
- Placeholder Notion schema (`notion/ids.example.yaml`)

## What must stay local

| File / value | Why |
|--------------|-----|
| `.env` | Tokens, chat IDs, API keys |
| `notion/ids.yaml` | Your private database IDs (optional) |
| `~/.hermes/`, SSH keys, `gh` auth | Machine credentials |
| `logs/`, `state/` | Runtime output |

## Rules for operators and agents

1. Never commit `.env` or paste tokens into PRs / Notion public pages.
2. Prefer `gh auth login` or deploy keys over long-lived PATs in files.
3. Keep Ollama on loopback (`127.0.0.1:11434`) unless you intentionally protect it.
4. Autopilot must not invent, rotate, or exfiltrate secrets.
5. Paid cloud fallbacks leave the machine — disable them for sensitive workspaces.
6. **Hawkeye private UI:** set a strong `AUTOCODE_PRIVATE_PASSWORD_HASH`, keep the UI on loopback behind Cloudflare Tunnel or Tailscale, and never commit the hash or webhook URLs.

## If a secret is leaked

1. Rotate the token at the provider immediately.
2. Purge it from git history if it was committed.
3. Open a GitHub security advisory if the leak affected published releases.
