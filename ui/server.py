#!/usr/bin/env python3
"""Local Autocode dashboard (stdlib only).

  python3 -m ui.server
  ./scripts/ui.sh

Default: 127.0.0.1:8787
Tunnel: ssh -L 8787:127.0.0.1:8787 jetson
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import threading
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import health as health_mod  # noqa: E402
from orchestrator import ops  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
STATE = ROOT / "state"
LOGS = ROOT / "logs"

HOST = os.environ.get("AUTOCODE_UI_HOST", "127.0.0.1")
PORT = int(os.environ.get("AUTOCODE_UI_PORT", "8787"))
TOKEN = secrets.token_urlsafe(24)

_demo_lock = threading.Lock()
_demo_proc: subprocess.Popen[str] | None = None
_demo_log = STATE / "ui-demo.log"
_work_lock = threading.Lock()
_work_proc: subprocess.Popen[str] | None = None
_work_log = STATE / "ui-work.log"


def load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def json_response(data: Any, code: int = 200) -> tuple[int, bytes, str]:
    return code, json.dumps(data, indent=2).encode(), "application/json; charset=utf-8"


def env_truthy(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


def has_env(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def gh_authed() -> bool:
    try:
        r = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, timeout=8, cwd=ROOT
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def readiness() -> dict[str, Any]:
    hermes_ok = False
    ollama_ok = False
    model = os.environ.get("OLLAMA_MODEL", "coder-64k")
    try:
        report = health_mod.check_local_stack()
        hermes_ok = report.hermes_ok
        ollama_ok = report.ollama_ok
        model = report.ollama_model
        details = list(report.details)
    except Exception as e:  # noqa: BLE001
        details = [f"health check error: {e}"]

    cursor_cmd = os.environ.get("AUTOCODE_CURSOR_DELEGATE_CMD", "")
    grok_cmd = os.environ.get("AUTOCODE_GROK_DELEGATE_CMD", "")
    local_only = env_truthy("AUTOCODE_LOCAL_ONLY", "1")

    checks = [
        {"id": "env", "label": ".env present", "ok": (ROOT / ".env").exists(), "hint": "Run ./start"},
        {"id": "notion", "label": "Notion connected", "ok": has_env("NOTION_TOKEN"), "hint": "./scripts/connect_notion.sh"},
        {
            "id": "hub",
            "label": "Notion hub / DBs",
            "ok": has_env("NOTION_BUILD_QUEUE_DB") or has_env("NOTION_HUB_PAGE"),
            "hint": "Share Autocode Hub page",
        },
        {
            "id": "github",
            "label": "GitHub token",
            "ok": has_env("GITHUB_TOKEN") or gh_authed(),
            "hint": "./scripts/auth_github.sh",
        },
        {"id": "hermes", "label": "Hermes CLI", "ok": hermes_ok, "hint": "./hermes/install_hermes.sh"},
        {"id": "ollama", "label": f"Ollama ({model})", "ok": ollama_ok, "hint": "./ollama/install_ollama_jetson.sh"},
        {
            "id": "cursor",
            "label": "Cursor webhook",
            "ok": local_only or (has_env("CURSOR_WEBHOOK_URL") and "stub" not in cursor_cmd),
            "hint": "Set CURSOR_WEBHOOK_URL (or keep LOCAL_ONLY=1)",
            "optional": True,
        },
        {
            "id": "grok",
            "label": "Grok Bot webhook",
            "ok": local_only or (has_env("GROK_BOT_WEBHOOK_URL") and "stub" not in grok_cmd),
            "hint": "Set GROK_BOT_WEBHOOK_URL (or keep LOCAL_ONLY=1)",
            "optional": True,
        },
        {
            "id": "autopilot",
            "label": "Autopilot enabled",
            "ok": env_truthy("AUTOCODE_AUTOPILOT_ENABLED"),
            "hint": "Set AUTOCODE_AUTOPILOT_ENABLED=1 after a supervised run",
            "optional": True,
        },
        {
            "id": "continuous",
            "label": "Always-on project autopilot",
            "ok": env_truthy("AUTOCODE_CONTINUOUS_ENABLED"),
            "hint": "Set AUTOCODE_CONTINUOUS_ENABLED=1 to keep draining Ready tasks until finished",
            "optional": True,
        },
    ]
    return {
        "ready": all(c["ok"] for c in checks if not c.get("optional")),
        "local_only": local_only,
        "autopilot": env_truthy("AUTOCODE_AUTOPILOT_ENABLED"),
        "continuous": env_truthy("AUTOCODE_CONTINUOUS_ENABLED"),
        "checks": checks,
        "details": details,
        "cost_profile": os.environ.get("AUTOCODE_COST_PROFILE", "cursor-grok"),
    }


def snapshot() -> dict[str, Any]:
    status = ops.load_status()
    control = ops.load_control()
    return {
        "status": asdict(status),
        "control": asdict(control),
        "heartbeat_age_sec": status.age_seconds(),
        "stuck": status.looks_stuck(),
        "formatted": ops.format_status(status, control),
        "token": TOKEN,
    }


def latest_log_tail(n: int = 80) -> dict[str, Any]:
    candidates: list[Path] = []
    if LOGS.is_dir():
        candidates.extend(LOGS.glob("nightly-*.log"))
        candidates.extend(LOGS.glob("*.log"))
    if _demo_log.exists():
        candidates.append(_demo_log)
    if not candidates:
        return {"path": None, "lines": [], "text": "(no logs yet — run a mock cycle)"}
    path = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        return {"path": str(path), "lines": [], "text": f"(unreadable: {e})"}
    lines = text.splitlines()[-n:]
    rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return {"path": rel, "lines": lines, "text": "\n".join(lines)}


def demo_state() -> dict[str, Any]:
    with _demo_lock:
        running = _demo_proc is not None and _demo_proc.poll() is None
        code = None if _demo_proc is None else _demo_proc.poll()
    return {
        "running": running,
        "exit_code": code,
        "log": str(_demo_log.relative_to(ROOT)) if _demo_log.exists() else None,
    }


def start_demo() -> dict[str, Any]:
    global _demo_proc
    with _demo_lock:
        if _demo_proc is not None and _demo_proc.poll() is None:
            return {"ok": False, "error": "Demo already running", **demo_state()}
        STATE.mkdir(parents=True, exist_ok=True)
        logf = _demo_log.open("w")
        script = ROOT / "scripts" / "demo_night.sh"
        cmd = (
            [str(script)]
            if script.exists()
            else [sys.executable, "-m", "orchestrator.run_night", "--mock"]
        )
        _demo_proc = subprocess.Popen(
            cmd, cwd=ROOT, stdout=logf, stderr=subprocess.STDOUT, text=True, env={**os.environ}
        )
        ops.write_status(
            phase="starting",
            detail="UI started mock demo cycle",
            night_id=f"ui-demo-{int(time.time())}",
        )
        ops.telegram_notify("Autocode UI: mock demo cycle started")
    return {"ok": True, **demo_state()}


def work_state() -> dict[str, Any]:
    with _work_lock:
        running = _work_proc is not None and _work_proc.poll() is None
        code = None if _work_proc is None else _work_proc.poll()
    return {
        "running": running,
        "exit_code": code,
        "log": str(_work_log.relative_to(ROOT)) if _work_log.exists() else None,
    }


def start_work_cycle(force: bool = True) -> dict[str, Any]:
    """Kick a live (or mock) continuous work cycle from the UI."""
    global _work_proc
    with _work_lock:
        if _work_proc is not None and _work_proc.poll() is None:
            return {"ok": False, "error": "Work cycle already running", **work_state()}
        if _demo_proc is not None and _demo_proc.poll() is None:
            return {"ok": False, "error": "Demo is running — wait or abort", **work_state()}
        STATE.mkdir(parents=True, exist_ok=True)
        logf = _work_log.open("w")
        script = ROOT / "cron" / "worker_run.sh"
        cmd = [str(script)]
        if force:
            cmd.append("--force")
        _work_proc = subprocess.Popen(
            cmd, cwd=ROOT, stdout=logf, stderr=subprocess.STDOUT, text=True, env={**os.environ}
        )
        ops.write_status(
            phase="starting",
            detail="UI started work cycle",
            night_id=f"ui-work-{int(time.time())}",
        )
        ops.telegram_notify("Autocode UI: work cycle started")
    return {"ok": True, **work_state()}


def apply_control(action: str, note: str = "", task_id: str = "") -> dict[str, Any]:
    action = action.strip().lower()
    if action == "pause":
        ops.set_control(paused=True, note=note or "paused from UI")
        ops.telegram_notify(f"Autocode PAUSED (UI): {note or 'paused from UI'}")
    elif action == "resume":
        ops.set_control(paused=False, note="")
        ops.telegram_notify("Autocode RESUMED (UI)")
    elif action == "abort":
        ops.set_control(abort=True, note=note or "abort from UI")
        ops.telegram_notify("Autocode ABORT requested from UI")
    elif action == "skip":
        if not task_id:
            return {"ok": False, "error": "task_id required for skip"}
        ops.set_control(skip_task_id=task_id)
        ops.telegram_notify(f"Autocode will SKIP {task_id} (UI)")
    elif action == "clear":
        ops.set_control(clear=True)
    elif action == "ping":
        sent = ops.telegram_notify(note or "Autocode UI ping OK")
        return {"ok": sent, "error": None if sent else "Telegram not configured", **snapshot()}
    else:
        return {"ok": False, "error": f"unknown action: {action}"}
    return {"ok": True, **snapshot()}



def _ollama_chat(message: str, system: str) -> str:
    """Call local Ollama chat API. Raises on transport/HTTP errors."""
    import json as _json
    import urllib.error
    import urllib.request

    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "coder-64k")
    body = _json.dumps(
        {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        f"http://{host}/api/chat",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = _json.loads(resp.read().decode())
    return (data.get("message") or {}).get("content") or data.get("response") or ""


def _should_escalate(message: str, local_reply: str) -> bool:
    text = f"{message}\n{local_reply}".lower()
    triggers = (
        "escalate:",
        "cannot",
        "can't",
        "too complex",
        "need a larger",
        "need cloud",
        "i am not able",
        "as a local model",
    )
    if any(t in text for t in triggers):
        return True
    # Long architectural asks → escalate
    keywords = ("architecture", "redesign", "migrate", "multi-service", "security audit")
    if len(message) > 400 or sum(1 for k in keywords if k in message.lower()) >= 2:
        return True
    if len(local_reply.strip()) < 40:
        return True
    return False


def _cloud_chat(message: str, local_reply: str) -> tuple[str, str]:
    """Escalate to Claude / OpenRouter / xAI. Returns (reply, provider)."""
    import json as _json
    import urllib.request

    prompt = (
        "You are Autocode's cloud escalator. The local Jetson model could not fully "
        "handle this operator instruction. Provide a concrete plan or answer, and if "
        "work should be queued, end with IMPROVE: <checklist item>.\n\n"
        f"Operator: {message}\n\nLocal model said:\n{local_reply[:2000]}"
    )
    if os.environ.get("ANTHROPIC_API_KEY"):
        body = {
            "model": os.environ.get("AUTOCODE_CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            "max_tokens": 1200,
            "messages": [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=_json.dumps(body).encode(),
            method="POST",
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode())
        parts = data.get("content") or []
        text = " ".join(p.get("text", "") for p in parts if isinstance(p, dict))
        return text or "(empty Claude reply)", "Claude"
    if os.environ.get("OPENROUTER_API_KEY"):
        body = {
            "model": os.environ.get("AUTOCODE_OPENROUTER_MODEL", "x-ai/grok-2"),
            "messages": [
                {"role": "system", "content": "You are Autocode cloud escalator."},
                {"role": "user", "content": prompt},
            ],
        }
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=_json.dumps(body).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"], "OpenRouter"
    if os.environ.get("XAI_API_KEY"):
        body = {
            "model": os.environ.get("AUTOCODE_GROK_MODEL", "grok-2-latest"),
            "messages": [
                {"role": "system", "content": "You are Autocode cloud escalator."},
                {"role": "user", "content": prompt},
            ],
        }
        req = urllib.request.Request(
            "https://api.x.ai/v1/chat/completions",
            data=_json.dumps(body).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {os.environ['XAI_API_KEY']}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"], "Grok"
    return (
        "No cloud provider configured (set ANTHROPIC_API_KEY, OPENROUTER_API_KEY, or XAI_API_KEY). "
        "Local reply retained.",
        "none",
    )


def handle_chat(message: str, seed_notion: bool = True) -> dict[str, Any]:
    message = (message or "").strip()
    if not message:
        return {"ok": False, "error": "message required"}
    system = (
        "You are Autocode's local co-pilot on a Jetson. Help the operator steer the "
        "Notion-driven coding autopilot. Be concise. If the request is too large for a "
        "local model, start with ESCALATE: and say why. If a durable follow-up should be "
        "queued for Autocode, end with IMPROVE: <checklist item> or BUG: <bug>."
    )
    local_reply = ""
    try:
        local_reply = _ollama_chat(message, system)
    except Exception as e:  # noqa: BLE001
        local_reply = f"(local model unavailable: {e})"
        escalated = True
    else:
        escalated = _should_escalate(message, local_reply)

    cloud_reply = ""
    provider = ""
    if escalated:
        try:
            cloud_reply, provider = _cloud_chat(message, local_reply)
        except Exception as e:  # noqa: BLE001
            cloud_reply = f"(cloud escalate failed: {e})"
            provider = "error"

    seeded_task = None
    if seed_notion:
        blob = f"{message}\n{local_reply}\n{cloud_reply}"
        try:
            from orchestrator.self_feed import feed_from_agent_output, seed_checklist_item

            pages = feed_from_agent_output(blob, mock=False)
            if pages:
                seeded_task = pages[0]
            elif any(k in message.lower() for k in ("add to checklist", "queue", "ready task", "todo")):
                seeded_task = seed_checklist_item(
                    title=f"Operator: {message[:80]}",
                    acceptance=(
                        "Queued from Autocode UI chat.\n\n"
                        f"Operator request:\n{message}\n\n"
                        f"Local reply:\n{local_reply[:1000]}\n\n"
                        f"Cloud reply:\n{(cloud_reply or '')[:1000]}"
                    ),
                    kind="improve",
                    priority="P2",
                    mock=False,
                )
        except Exception as e:  # noqa: BLE001
            print(f"[ui-chat] seed failed: {e}")

    # Persist a short transcript for remote ops
    STATE.mkdir(parents=True, exist_ok=True)
    log = STATE / "ui-chat.jsonl"
    import json as _json
    import time as _time

    log.open("a").write(
        _json.dumps(
            {
                "ts": _time.time(),
                "message": message,
                "local_reply": local_reply,
                "escalated": escalated,
                "cloud_reply": cloud_reply,
                "provider": provider,
                "seeded_task": seeded_task,
            }
        )
        + "\n"
    )
    return {
        "ok": True,
        "local_reply": local_reply,
        "escalated": escalated,
        "cloud_reply": cloud_reply,
        "provider": provider,
        "seeded_task": seeded_task,
    }



class Handler(BaseHTTPRequestHandler):
    server_version = "AutocodeUI/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write(f"[ui] {self.address_string()} {fmt % args}\n")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        try:
            data = json.loads(self.rfile.read(length).decode() or "{}")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _ok_token(self, data: dict[str, Any] | None = None) -> bool:
        hdr = self.headers.get("X-Autocode-Token", "")
        tok = hdr or (data or {}).get("token") or ""
        return secrets.compare_digest(str(tok), TOKEN)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._static("index.html", "text/html; charset=utf-8")
        if path == "/app.css":
            return self._static("app.css", "text/css; charset=utf-8")
        if path == "/app.js":
            return self._static("app.js", "application/javascript; charset=utf-8")
        if path.startswith("/brand/"):
            name = path.lstrip("/")
            ctype = "image/jpeg" if name.endswith((".jpg", ".jpeg")) else "image/png" if name.endswith(".png") else "application/octet-stream"
            return self._static(name, ctype)
        if path == "/api/status":
            return self._send(*json_response(snapshot()))
        if path == "/api/ready":
            return self._send(*json_response(readiness()))
        if path == "/api/logs":
            return self._send(*json_response(latest_log_tail()))
        if path == "/api/demo":
            return self._send(*json_response(demo_state()))
        if path == "/api/work":
            return self._send(*json_response(work_state()))
        if path == "/api/token":
            return self._send(*json_response({"token": TOKEN}))
        self._send(*json_response({"error": "not found"}, 404))

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        data = self._read_json()
        if not self._ok_token(data):
            return self._send(*json_response({"ok": False, "error": "bad token"}, 403))
        if path == "/api/control":
            return self._send(
                *json_response(
                    apply_control(
                        str(data.get("action") or ""),
                        str(data.get("note") or ""),
                        str(data.get("task_id") or ""),
                    )
                )
            )
        if path == "/api/demo":
            return self._send(*json_response(start_demo()))
        if path == "/api/work":
            force = str(data.get("force", "1")).lower() not in ("0", "false", "no")
            return self._send(*json_response(start_work_cycle(force=force)))

        if path == "/api/chat":
            return self._send(
                *json_response(
                    handle_chat(
                        str(data.get("message") or ""),
                        seed_notion=str(data.get("seed_notion", "1")).lower()
                        not in ("0", "false", "no"),
                    )
                )
            )
        self._send(*json_response({"ok": False, "error": "not found"}, 404))

    def _static(self, name: str, content_type: str) -> None:
        path = STATIC / name
        if not path.is_file() or not path.resolve().is_relative_to(STATIC.resolve()):
            return self._send(*json_response({"error": f"missing {name}"}, 404))
        body = path.read_bytes()
        if name == "index.html":
            body = body.decode("utf-8").replace("{{TOKEN}}", TOKEN).encode("utf-8")
        self._send(200, body, content_type)


def main() -> None:
    load_dotenv()
    STATE.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Autocode UI → http://{HOST}:{PORT}/")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
