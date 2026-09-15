#!/usr/bin/env python3
"""Autocode overnight orchestrator — local-first coding with cloud escalation."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from notion import client as notion  # noqa: E402


@dataclass
class Task:
    page_id: str
    task_id: str
    name: str
    acceptance: str
    complexity: str
    model_route: str
    repo: str
    priority: str
    notes: str = ""

    @classmethod
    def from_page(cls, page: dict[str, Any]) -> "Task":
        props = page.get("properties", {})
        tid = props.get("Task ID", {}).get("unique_id", {})
        number = tid.get("number") if isinstance(tid, dict) else None
        task_id = f"BLD-{number}" if number is not None else page["id"][:8]
        repo = (
            notion.page_prop_select(page, "Repo")
            or notion.page_prop_text(page, "Repo")
            or ""
        )
        return cls(
            page_id=page["id"],
            task_id=task_id,
            name=notion.page_title(page),
            acceptance=notion.page_prop_text(page, "Acceptance"),
            complexity=notion.page_prop_select(page, "Complexity") or "Local-safe",
            model_route=notion.page_prop_select(page, "Model route") or "Local Hermes",
            repo=repo,
            priority=notion.page_prop_select(page, "Priority") or "P2",
            notes=notion.page_prop_text(page, "Notes"),
        )


@dataclass
class HardwareSnapshot:
    mem_available_mb: int
    mem_total_mb: int
    disk_free_gb: float
    load1: float
    is_jetson: bool
    notes: list[str] = field(default_factory=list)

    def too_constrained_for_local(self) -> bool:
        if self.mem_available_mb < 2500:
            return True
        if self.disk_free_gb < 5:
            return True
        cpus = os.cpu_count() or 4
        return self.load1 > max(8.0, cpus * 2)


@dataclass
class RunResult:
    outcome: str
    summary: str
    model_used: str = "Local"
    pr_url: str | None = None
    branch: str | None = None
    escalated_to: str | None = None
    why: str | None = None


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (s or "task")[:max_len]


def probe_hardware() -> HardwareSnapshot:
    notes: list[str] = []
    mem_total = mem_avail = 0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1]) // 1024
            elif line.startswith("MemAvailable:"):
                mem_avail = int(line.split()[1]) // 1024
    except OSError:
        notes.append("no /proc/meminfo")

    disk_free = 0.0
    try:
        disk_free = shutil.disk_usage(str(ROOT)).free / (1024 ** 3)
    except OSError:
        notes.append("disk_usage failed")

    load1 = 0.0
    try:
        load1 = os.getloadavg()[0]
    except OSError:
        notes.append("no loadavg")

    is_jetson = Path("/etc/nv_tegra_release").exists()
    if is_jetson:
        notes.append("jetson detected")
    return HardwareSnapshot(mem_avail, mem_total, disk_free, load1, is_jetson, notes)


def query_ready_tasks(limit: int) -> list[Task]:
    body = {
        "filter": {"property": "Status", "select": {"equals": "Ready"}},
        "sorts": [{"property": "Priority", "direction": "ascending"}],
        "page_size": limit,
    }
    result = notion.notion_request(
        "POST", f"/databases/{notion.db_id('build_queue')}/query", body
    )
    return [Task.from_page(p) for p in result.get("results", [])]


def preferred_cloud_target(task: Task) -> str:
    mapping = {
        "Claude": "Claude",
        "Grok": "Grok Bot",
        "Cursor Cloud": "Cursor Cloud",
    }
    if task.model_route in mapping:
        return mapping[task.model_route]
    if os.environ.get("CURSOR_API_KEY") or os.environ.get("AUTOCODE_CURSOR_DELEGATE_CMD"):
        return "Cursor Cloud"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "Claude"
    if os.environ.get("OPENROUTER_API_KEY") or os.environ.get("XAI_API_KEY"):
        return "Grok Bot"
    return "Human"


def route_task(task: Task, hw: HardwareSnapshot, local_failures: int) -> str:
    if task.complexity == "Cloud-only":
        return preferred_cloud_target(task)
    if task.model_route and task.model_route != "Local Hermes":
        return preferred_cloud_target(task)
    if local_failures >= env_int("AUTOCODE_MAX_LOCAL_ATTEMPTS", 2):
        return preferred_cloud_target(task)
    if hw.too_constrained_for_local():
        return preferred_cloud_target(task)
    if task.complexity == "Maybe local" and hw.mem_available_mb < 4000:
        return preferred_cloud_target(task)
    return "local"


def workspace_for_repo(repo: str) -> Path:
    root = Path(os.environ.get("WORKSPACE_ROOT", str(Path.home() / "workspaces")))
    if not repo:
        return root / "default"
    name = repo.rstrip("/").split("/")[-1].removesuffix(".git")
    return root / name


def ensure_branch(repo_dir: Path, branch: str) -> None:
    if not (repo_dir / ".git").exists():
        raise RuntimeError(f"Not a git repo: {repo_dir}")
    subprocess.run(["git", "fetch", "--all"], cwd=repo_dir, check=False, capture_output=True)
    for base in ("main", "master"):
        r = subprocess.run(["git", "checkout", base], cwd=repo_dir, capture_output=True)
        if r.returncode == 0:
            break
    subprocess.run(["git", "checkout", "-B", branch], cwd=repo_dir, check=True)


def build_prompt(task: Task, branch: str) -> str:
    return f"""You are Autocode local Hermes working overnight.

Task: {task.task_id} — {task.name}
Priority: {task.priority}
Complexity: {task.complexity}
Branch: {branch}

Acceptance criteria:
{task.acceptance or "(none — make a minimal safe change and document assumptions)"}

Notes:
{task.notes or "(none)"}

Rules:
- Stay inside acceptance criteria.
- Never merge main. Never invent secrets.
- Prefer a small PR-ready change.
- Run available tests/linters.
- If stuck after honest attempts, stop and say ESCALATE: <reason>.
"""


def maybe_open_pr(repo_dir: Path, branch: str, task: Task) -> str | None:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True
    )
    if status.stdout.strip():
        subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=False)
        subprocess.run(
            ["git", "commit", "-m", f"{task.task_id}: {task.name}"],
            cwd=repo_dir,
            check=False,
        )
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=repo_dir, check=False)
    if not shutil.which("gh"):
        return None
    pr = subprocess.run(
        [
            "gh", "pr", "create",
            "--title", f"{task.task_id}: {task.name}",
            "--body", f"Autocode overnight run.\n\n## Acceptance\n{task.acceptance}\n",
        ],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if pr.returncode != 0:
        return None
    url = pr.stdout.strip().splitlines()[-1].strip()
    return url if url.startswith("http") else None


def run_local_hermes(task: Task, repo_dir: Path, branch: str, wall_minutes: int) -> RunResult:
    prompt = build_prompt(task, branch)
    state = ROOT / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / f"prompt-{task.task_id}.txt").write_text(prompt)

    hermes = shutil.which("hermes")
    if not hermes:
        return RunResult(
            outcome="Failed",
            summary="hermes CLI not found — install Hermes or escalate",
            branch=branch,
            why="Tool fail",
        )

    try:
        proc = subprocess.run(
            [hermes, "chat", "-q", prompt],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=wall_minutes * 60,
        )
    except subprocess.TimeoutExpired:
        return RunResult(
            outcome="Failed",
            summary=f"Local Hermes hit wall time ({wall_minutes}m)",
            branch=branch,
            why="Too complex",
        )

    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    (state / f"hermes-{task.task_id}.log").write_text(out)

    if proc.returncode != 0:
        return RunResult(
            outcome="Failed",
            summary=f"Hermes exit {proc.returncode}: {out[-500:]}",
            branch=branch,
            why="Tool fail",
        )
    if re.search(r"ESCALATE:", out, re.I):
        return RunResult(
            outcome="Failed",
            summary=out[-800:],
            branch=branch,
            why="Too complex",
        )

    pr_url = maybe_open_pr(repo_dir, branch, task)
    if pr_url:
        return RunResult(
            outcome="Success",
            summary=f"Local Hermes finished; PR {pr_url}",
            pr_url=pr_url,
            branch=branch,
        )

    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True
    )
    if dirty.stdout.strip():
        return RunResult(
            outcome="Partial",
            summary="Local changes on branch but no PR opened",
            branch=branch,
        )
    return RunResult(
        outcome="Partial",
        summary="Hermes OK but no file changes detected",
        branch=branch,
    )


def write_delegate_payload(task: Task, target: str, why: str, context: str) -> Path:
    out_dir = ROOT / "state" / "delegates"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{task.task_id}-{int(time.time())}.json"
    payload = {
        "task": asdict(task),
        "send_to": target,
        "why": why,
        "context": context,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "instructions": (
            "Cloud agent: implement acceptance criteria on a feature branch, "
            "open a PR, never merge main, never invent secrets."
        ),
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def anthropic_ping(task: Task, context: str) -> None:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    body = {
        "model": os.environ.get("AUTOCODE_CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        "max_tokens": 256,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Autocode escalation for {task.task_id}: {task.name}\n"
                    f"Acceptance: {task.acceptance}\nContext: {context[:1500]}\n"
                    "Acknowledge receipt in one short sentence."
                ),
            }
        ],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()


def model_label_for_target(target: str) -> str:
    return {
        "Claude": "Claude",
        "Grok Bot": "Grok",
        "Cursor Cloud": "Cursor",
        "Human": "Local",
    }.get(target, "Mixed")


def invoke_cloud_delegate(task: Task, target: str, why: str, context: str) -> RunResult:
    payload_path = write_delegate_payload(task, target, why, context)

    custom = os.environ.get("AUTOCODE_CURSOR_DELEGATE_CMD", "").strip()
    if target == "Cursor Cloud" and custom:
        try:
            subprocess.run(
                custom,
                shell=True,
                check=True,
                cwd=str(ROOT),
                env={**os.environ, "AUTOCODE_DELEGATE_PAYLOAD": str(payload_path)},
                timeout=env_int("AUTOCODE_DELEGATE_TIMEOUT_SEC", 120),
            )
            return RunResult(
                outcome="Escalated",
                summary=f"Delegated to Cursor via AUTOCODE_CURSOR_DELEGATE_CMD; {payload_path}",
                model_used="Cursor",
                escalated_to=target,
                why=why,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            context = f"{context}\nDelegate cmd failed: {e}"

    if target == "Claude" and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            anthropic_ping(task, context)
            return RunResult(
                outcome="Escalated",
                summary=f"Escalation logged + Anthropic notify; {payload_path}",
                model_used="Claude",
                escalated_to=target,
                why=why,
            )
        except Exception as e:  # noqa: BLE001
            context = f"{context}\nAnthropic notify failed: {e}"

    return RunResult(
        outcome="Escalated",
        summary=f"Escalated to {target}. Payload: {payload_path}. Awaiting cloud/human agent.",
        model_used=model_label_for_target(target),
        escalated_to=target,
        why=why,
    )


def process_task(task: Task, hw: HardwareSnapshot, digest: list[str]) -> RunResult:
    prefix = os.environ.get("AUTOCODE_BRANCH_PREFIX", "hermes")
    branch = f"{prefix}/{task.task_id.lower()}-{slugify(task.name)}"
    wall = env_int("AUTOCODE_MAX_WALL_MINUTES", 90)

    route = route_task(task, hw, local_failures=0)
    notion.claim_task(task.page_id)

    if route != "local":
        why = "Tool fail" if hw.too_constrained_for_local() else "Too complex"
        context = (
            f"Routed to {route} (complexity={task.complexity}, "
            f"model_route={task.model_route}, hw={asdict(hw)})"
        )
        result = invoke_cloud_delegate(task, route, why, context)
        notion.write_escalation(
            task.name, why, result.summary, send_to=result.escalated_to or route
        )
        notion.log_agent_run(
            task.name, result.outcome, result.summary, result.model_used, result.pr_url
        )
        digest.append(f"ESCALATED {task.task_id} → {route}: {task.name}")
        return result

    repo_dir = workspace_for_repo(task.repo)
    if not repo_dir.exists():
        target = preferred_cloud_target(task)
        result = invoke_cloud_delegate(
            task,
            target,
            "Tool fail",
            f"Workspace missing: {repo_dir}. Clone WORKSPACE_REPOS first.",
        )
        notion.write_escalation(task.name, "Tool fail", result.summary, send_to=target)
        notion.log_agent_run(task.name, result.outcome, result.summary, result.model_used)
        digest.append(f"ESCALATED {task.task_id} (missing repo): {task.name}")
        return result

    try:
        ensure_branch(repo_dir, branch)
    except Exception as e:  # noqa: BLE001
        result = RunResult(
            outcome="Failed",
            summary=f"git branch failed: {e}",
            why="Tool fail",
            branch=branch,
        )
        notion.write_escalation(task.name, "Tool fail", result.summary, send_to="Human")
        notion.log_agent_run(task.name, result.outcome, result.summary)
        digest.append(f"FAILED {task.task_id} git: {task.name}")
        return result

    result = run_local_hermes(task, repo_dir, branch, wall)

    if result.outcome == "Failed":
        target = preferred_cloud_target(task)
        why = result.why or "Too complex"
        esc = invoke_cloud_delegate(task, target, why, result.summary)
        notion.write_escalation(task.name, why, esc.summary, send_to=target)
        notion.log_agent_run(task.name, "Escalated", esc.summary, esc.model_used)
        digest.append(f"ESCALATED {task.task_id} after local fail → {target}")
        return esc

    if result.pr_url:
        notion.mark_needs_review(task.page_id, result.pr_url)
    notion.log_agent_run(
        task.name, result.outcome, result.summary, result.model_used, result.pr_url
    )
    digest.append(
        f"{result.outcome.upper()} {task.task_id}: {task.name} {result.pr_url or ''}".strip()
    )
    return result


def send_digest(path: Path) -> None:
    script = ROOT / "scripts" / "send_telegram_digest.sh"
    if script.exists():
        subprocess.run([str(script), str(path)], check=False)


def main() -> None:
    notion.load_dotenv()
    parser = argparse.ArgumentParser(description="Autocode overnight orchestrator")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    max_tasks = args.limit or env_int("AUTOCODE_MAX_TASKS_PER_NIGHT", 2)
    hw = probe_hardware()
    print(f"Hardware: {asdict(hw)}")

    if not os.environ.get("NOTION_TOKEN"):
        raise SystemExit("NOTION_TOKEN required (set in local .env)")

    tasks = query_ready_tasks(limit=max_tasks)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    digest_path = ROOT / "state" / f"digest-{stamp}.txt"
    digest_path.parent.mkdir(parents=True, exist_ok=True)

    if not tasks:
        print("No Ready tasks.")
        digest_path.write_text("No Ready tasks.\n")
        send_digest(digest_path)
        return

    digest: list[str] = [f"Autocode digest {datetime.now(timezone.utc).isoformat()}"]
    for task in tasks[:max_tasks]:
        route = route_task(task, hw, 0)
        print(f"Task {task.task_id} {task.name!r} → route={route}")
        if args.dry_run:
            digest.append(f"DRY-RUN {task.task_id} → {route}")
            continue
        process_task(task, hw, digest)

    digest_path.write_text("\n".join(digest) + "\n")
    print(f"Digest: {digest_path}")
    send_digest(digest_path)


if __name__ == "__main__":
    main()
