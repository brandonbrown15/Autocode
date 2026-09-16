# Two repositories

| Repo | Visibility | Product | Purpose |
|------|------------|---------|---------|
| **Autocode** | Public | Autocode | Open-source Notion/Jetson coding autopilot (Apache-2.0) |
| **Hawkeye** | **Private** | Hawkeye | Your personal fork: login, domain, free local LLM all day, Cursor/Grok escalate |

Do **not** merge Hawkeye-only config (password hashes, personal domains, webhook URLs) into Autocode `main`.

To materialize Hawkeye after creating an empty private GitHub repo:

```bash
./scripts/publish_hawkeye_private.sh git@github.com:YOUR_USER/Hawkeye.git
```

Details: [docs/hawkeye.md](docs/hawkeye.md)
