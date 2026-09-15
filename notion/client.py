#!/usr/bin/env python3
"""Minimal Notion helpers for Autocode overnight loop.

Uses the Notion REST API with NOTION_TOKEN from the environment.
No secrets are stored in-repo. Share Build Queue / Agent Runs / Escalation Log
with the integration before running.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"

ROOT = Path(__file__).resolve().parents[1]


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def notion_request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        raise SystemExit("NOTION_TOKEN is required (set in .env on the Jetson)")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise SystemExit(f"Notion HTTP {e.code}: {detail}") from e


def db_id(name: str) -> str:
    key = {
        "build_queue": "NOTION_BUILD_QUEUE_DB",
        "agent_runs": "NOTION_AGENT_RUNS_DB",
        "escalation_log": "NOTION_ESCALATION_LOG_DB",
    }[name]
    value = os.environ.get(key, "").strip()
    if not value:
        raise SystemExit(f"{key} missing from environment")
    return value


def rich_text(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": text[:1900]}}]


def title(text: str) -> list[dict[str, Any]]:
    return rich_text(text)


def query_ready_local_safe(limit: int = 5) -> list[dict[str, Any]]:
    """Fetch Ready + Local-safe tasks ordered for overnight pickup."""
    body = {
        "filter": {
            "and": [
                {"property": "Status", "select": {"equals": "Ready"}},
                {"property": "Complexity", "select": {"equals": "Local-safe"}},
            ]
        },
        "sorts": [{"property": "Priority", "direction": "ascending"}],
        "page_size": limit,
    }
    result = notion_request("POST", f"/databases/{db_id('build_queue')}/query", body)
    return result.get("results", [])


def page_title(page: dict[str, Any]) -> str:
    props = page.get("properties", {})
    t = props.get("Name", {}).get("title", [])
    if not t:
        return "(untitled)"
    return "".join(part.get("plain_text", "") for part in t)


def page_prop_select(page: dict[str, Any], name: str) -> str | None:
    sel = page.get("properties", {}).get(name, {}).get("select")
    return sel.get("name") if sel else None


def page_prop_text(page: dict[str, Any], name: str) -> str:
    rich = page.get("properties", {}).get(name, {}).get("rich_text", [])
    return "".join(part.get("plain_text", "") for part in rich)


def set_task_status(page_id: str, status: str, pr_url: str | None = None) -> None:
    props: dict[str, Any] = {"Status": {"select": {"name": status}}}
    if pr_url:
        props["Branch / PR"] = {"url": pr_url}
    notion_request("PATCH", f"/pages/{page_id}", {"properties": props})


def claim_task(page_id: str) -> None:
    set_task_status(page_id, "Running")


def mark_needs_review(page_id: str, pr_url: str) -> None:
    set_task_status(page_id, "Needs review", pr_url=pr_url)


def mark_blocked(page_id: str) -> None:
    set_task_status(page_id, "Blocked")


def log_agent_run(
    name: str,
    outcome: str,
    summary: str,
    model_used: str = "Local",
    pr_url: str | None = None,
) -> None:
    props: dict[str, Any] = {
        "Name": {"title": title(name)},
        "Outcome": {"select": {"name": outcome}},
        "Summary": {"rich_text": rich_text(summary)},
        "Model used": {"select": {"name": model_used}},
    }
    if pr_url:
        props["PR / commit"] = {"url": pr_url}
    notion_request(
        "POST",
        "/pages",
        {"parent": {"database_id": db_id("agent_runs")}, "properties": props},
    )


def write_escalation(
    name: str,
    why: str,
    context: str,
    send_to: str = "Human",
    related_pr: str | None = None,
) -> None:
    props: dict[str, Any] = {
        "Name": {"title": title(name)},
        "Status": {"select": {"name": "Open"}},
        "Why escalated": {"select": {"name": why}},
        "Send to": {"select": {"name": send_to}},
        "Context": {"rich_text": rich_text(context)},
    }
    if related_pr:
        props["Related PR"] = {"url": related_pr}
    notion_request(
        "POST",
        "/pages",
        {"parent": {"database_id": db_id("escalation_log")}, "properties": props},
    )


def cmd_list_ready(_: argparse.Namespace) -> None:
    pages = query_ready_local_safe(limit=int(os.environ.get("AUTOCODE_MAX_TASKS_PER_NIGHT", "2")))
    if not pages:
        print("No Ready + Local-safe tasks.")
        return
    for page in pages:
        tid = page.get("properties", {}).get("Task ID", {})
        task_id = tid.get("unique_id", {}).get("number") or "?"
        print(
            f"BLD-{task_id}\t{page_title(page)}\t"
            f"prio={page_prop_select(page, 'Priority')}\t"
            f"repo={page_prop_select(page, 'Repo')}\t"
            f"accept={page_prop_text(page, 'Acceptance')[:80]}"
        )
        print(f"  id={page['id']}")


def cmd_doctor(_: argparse.Namespace) -> None:
    """Verify token + DB access. Exit 0 only if all configured DBs respond."""
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("FAIL: NOTION_TOKEN unset")
        raise SystemExit(1)

    checks = [
        ("build_queue", "NOTION_BUILD_QUEUE_DB"),
        ("agent_runs", "NOTION_AGENT_RUNS_DB"),
        ("escalation_log", "NOTION_ESCALATION_LOG_DB"),
    ]
    failed = 0
    for name, env_key in checks:
        value = os.environ.get(env_key, "").strip()
        if not value:
            print(f"WARN: {env_key} unset — skip")
            continue
        try:
            notion_request("GET", f"/databases/{value}")
            print(f"OK   {name} ({env_key})")
        except SystemExit as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    if failed:
        raise SystemExit(1)
    if not any(os.environ.get(k, "").strip() for _, k in checks):
        print("FAIL: no Notion database IDs configured")
        raise SystemExit(1)
    print("Notion doctor passed")


def cmd_claim(args: argparse.Namespace) -> None:
    claim_task(args.page_id)
    print(f"Claimed {args.page_id} → Running")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Autocode Notion helpers")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list-ready", help="List Ready + Local-safe Build Queue items")
    p_list.set_defaults(func=cmd_list_ready)

    p_doc = sub.add_parser("doctor", help="Verify Notion token + database access")
    p_doc.set_defaults(func=cmd_doctor)

    p_claim = sub.add_parser("claim", help="Mark a Build Queue page Running")
    p_claim.add_argument("page_id")
    p_claim.set_defaults(func=cmd_claim)

    p_review = sub.add_parser("needs-review", help="Mark Needs review + set PR URL")
    p_review.add_argument("page_id")
    p_review.add_argument("pr_url")
    p_review.set_defaults(
        func=lambda a: (mark_needs_review(a.page_id, a.pr_url), print("updated"))
    )

    p_run = sub.add_parser("log-run", help="Create an Agent Runs row")
    p_run.add_argument("name")
    p_run.add_argument("outcome", choices=["Success", "Partial", "Failed", "Escalated", "Skipped"])
    p_run.add_argument("summary")
    p_run.add_argument("--pr")
    p_run.add_argument("--model", default="Local")
    p_run.set_defaults(
        func=lambda a: (
            log_agent_run(a.name, a.outcome, a.summary, a.model, a.pr),
            print("logged"),
        )
    )

    p_esc = sub.add_parser("escalate", help="Write Escalation Log row")
    p_esc.add_argument("name")
    p_esc.add_argument(
        "why",
        choices=["Too complex", "Tool fail", "Tests failing", "Needs secrets", "Ambiguous"],
    )
    p_esc.add_argument("context")
    p_esc.add_argument("--send-to", default="Human")
    p_esc.add_argument("--pr")
    p_esc.set_defaults(
        func=lambda a: (
            write_escalation(a.name, a.why, a.context, a.send_to, a.pr),
            print("escalated"),
        )
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
