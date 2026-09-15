# Notion setup (bring your own workspace)

Autocode does **not** ship with anyone else's Notion IDs or tokens. Create these three databases in your workspace, then paste the IDs into `.env`.

## 1. Create a Notion integration

1. Open [Notion → My integrations](https://www.notion.so/my-integrations).
2. Create an internal integration (e.g. `Autocode`).
3. Copy the secret → `NOTION_TOKEN` in `.env` (local only).

## 2. Create three databases

Suggested names: **Build Queue**, **Agent Runs**, **Escalation Log**.

### Build Queue

| Property | Type | Notes |
|----------|------|--------|
| Name | Title | Task title |
| Status | Select | `Backlog`, `Ready`, `Running`, `Needs review`, `Done`, `Blocked` |
| Priority | Select | `P0`–`P3` |
| Complexity | Select | `Local-safe`, `Maybe local`, `Cloud-only` |
| Model route | Select | `Local Hermes`, `Claude`, `Grok`, `Cursor Cloud` |
| Repo | Select or Text | Which git repo to work in |
| Acceptance | Text | Definition of done |
| Branch / PR | URL | Filled by autopilot |
| Notes | Text | Optional |

### Agent Runs

| Property | Type | Notes |
|----------|------|--------|
| Name | Title | Run label |
| Outcome | Select | `Success`, `Partial`, `Failed`, `Escalated`, `Skipped` |
| Model used | Select | `Local`, `Claude`, `Grok`, `Cursor`, `Mixed` |
| Summary | Text | What happened |
| PR / commit | URL | Optional |
| Tokens / cost note | Text | Optional |

### Escalation Log

| Property | Type | Notes |
|----------|------|--------|
| Name | Title | Task / failure label |
| Status | Select | `Open`, `Assigned`, `Resolved` |
| Why escalated | Select | `Too complex`, `Tool fail`, `Tests failing`, `Needs secrets`, `Ambiguous` |
| Send to | Select | `Claude`, `Grok Bot`, `Cursor Cloud`, `Human` |
| Context | Text | Branch + failure notes |
| Related PR | URL | Optional |

## 3. Share pages with the integration

Open each database → **···** → **Connections** → add your Autocode integration.

## 4. Copy IDs into `.env`

Database ID = the 32-hex UUID in the Notion URL (with dashes).

```bash
NOTION_BUILD_QUEUE_DB=...
NOTION_AGENT_RUNS_DB=...
NOTION_ESCALATION_LOG_DB=...
NOTION_HUB_PAGE=...   # optional parent page
```

Optional: `cp notion/ids.example.yaml notion/ids.yaml` and fill IDs there too (`ids.yaml` is gitignored).

## 5. Smoke test

```bash
python3 notion/client.py list-ready
```
