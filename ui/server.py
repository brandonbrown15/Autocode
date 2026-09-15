#!/usr/bin/env python3
"""Local Autocode dashboard (stdlib only).

  python3 -m ui.server
  ./scripts/ui.sh

Default bind: 127.0.0.1:8787 (safe for Jetson + Tailscale SSH tunnel).
Set AUTOCODE_UI_HOST=0.0.0.0 only if you intentionally expose on LAN.
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
SESSION_TOKEN = secrets.token_urlsafe(24)

_demo_lock = threading.Lock()
_demo_proc: subprocess.Popen[str] | None = None
_demo_log = STATE / "ui-demo.log"


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _json(data: Any, code: int = 200) -> tuple[int, bytes, str]:
    body = json.dumps(data, indent=2).encode()
    return code, body, "application/json; charset=utf-8"


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


def _has(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def readiness() -> dict[str, Any]:
    """Non-secret readiness for the UI checklist."""
    hermes_ok = False
    ollama_ok = False
    model = os.environ.get("OLLAMA_MODEL", "coder-64k")
    try:
        report = health_mod.check_local_stack()
        hermes_ok = report.hermes_ok
        ollama_ok = report.ollama_ok
        model = report.ollama_model
    except Exception as e:  # noqa: BLE001
        details = [f"health check error: {e}"]
    else:
        details = list(report.details)

    cursor_cmd = os.environ.get("AUTOCODE_CURSOR_DELEGATE_CMD", "")
    grok_cmd = os.environ.get("AUTOCODE_GROK_DELEGATE_CMD", "")
    local_only = _env_truthy("AUTOCODE_LOCAL_ONLY", "1")

    checks = [
        {"id": "env", "label": ".env present", "ok": (ROOT / ".env").exists(), "hint": "Run ./start"},
        {"id": "notion", "label": "Notion connected", "ok": _has("NOTION_TOKEN"), "hint": "./scripts/connect_notion.sh"},
        {"id": "hub", "label": "Notion hub / DBs", "ok": _has("NOTION_BUILD_QUEUE_DB") or _has("NOTION_HUB_PAGE"), "hint": "Share Autocode Hub page"},
        {"id": "github", "label": "GitHub token", "ok": _has("GITHUB_TOKEN") or _gh_authed(), "hint": "./scripts/auth_github.sh"},
        {"id": "hermes", "label": "Hermes CLI", "ok": hermes_ok, "hint": "./hermes/install_hermes.sh"},
        {"id": "ollama", "label": f"Ollama ({model})", "ok": ollama_ok, "hint": "./ollama/install_ollama_jetson.sh"},
        {
            "id": "cursor",
            "label": "Cursor webhook",
            "ok": local_only or (_has("CURSOR_WEBHOOK_URL") and "stub" not in cursor_cmd),
            "hint": "Set CURSOR_WEBHOOK_URL (or keep LOCAL_ONLY=1)",
            "optional": True,
        },
        {
            "id": "grok",
            "label": "Grok Bot webhook",
            "ok": local_only or (_has("GROK_BOT_WEBHOOK_URL") and "stub" not in grok_cmd),
            "hint": "Set GROK_BOT_WEBHOOK_URL (or keep LOCAL_ONLY=1)",
            "optional": True,
        },
        {
            "id": "autopilot",
            "label": "Autopilot enabled",
            "ok": _env_truthy("AUTOCODE_AUTOPILOT_ENABLED"),
            "hint": "Set AUTOCODE_AUTOPILOT_ENABLED=1 after a supervised night",
            "optional": True,
        },
    ]
    required_ok = all(c["ok"] for c in checks if not c.get("optional"))
    return {
        "ready": required_ok,
        "local_only": local_only,
        "autopilot": _env_truthy("AUTOCODE_AUTOPILOT_ENABLED"),
        "checks": checks,
        "details": details,
        "cost_profile": os.environ.get("AUTOCODE_COST_PROFILE", "cursor-grok"),
    }


def _gh_authed() -> bool:
    try:
        r = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=8,
            cwd=ROOT,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def snapshot() -> dict[str, Any]:
    status = ops.load_status()
    control = ops.load_control()
    age = status.age_seconds()
    return {
        "status": asdict(status),
        "control": asdict(control),
        "heartbeat_age_sec": age,
        "stuck": status.looks_stuck(),
        "formatted": ops.format_status(status, control),
        "token": SESSION_TOKEN,
    }


def latest_log_tail(n: int = 80) -> dict[str, Any]:
    candidates: list[Path] = []
    if LOGS.is_dir():
        candidates.extend(sorted(LOGS.glob("nightly-*.log"), key=lambda p: p.stat().st_mtime))
        candidates.extend(sorted(LOGS.glob("*.log"), key=lambda p: p.stat().st_mtime))
    if _demo_log.exists():
        candidates.append(_demo_log)
    if not candidates:
        return {"path": None, "lines": [], "text": "(no logs yet — run a demo night)"}
    path = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        return {"path": str(path), "lines": [], "text": f"(unreadable: {e})"}
    lines = text.splitlines()[-n:]
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path), "lines": lines, "text": "\n".join(lines)}


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
        cmd = [str(script)] if script.exists() else [sys.executable, "-m", "orchestrator.run_night", "--mock"]
        _demo_proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ},
        )
        ops.write_status(phase="starting", detail="UI started mock demo night", night_id=f"ui-demo-{int(time.time())}")
        ops.telegram_notify("Autocode UI: mock demo night started")
    return {"ok": True, **demo_state()}


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


class Handler(BaseHTTPRequestHandler):
    server_version = "AutocodeUI/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write(f"[ui] {self.address_string()} {fmt % args}\n")

    def _cors(self) -> None:
        self.send_header("Cache-Control", "no-store")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode() or "{}")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _check_token(self, data: dict[str, Any] | None = None) -> bool:
        hdr = self.headers.get("X-Autocode-Token", "")
        tok = hdr or (data or {}).get("token") or ""
        return secrets.compare_digest(str(tok), SESSION_TOKEN)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._serve_static("index.html", "text/html; charset=utf-8")
        if path == "/app.css":
            return self._serve_static("app.css", "text/css; charset=utf-8")
        if path == "/app.js":
            return self._serve_static("app.js", "application/javascript; charset=utf-8")
        if path == "/api/status":
            return self._send(*_json(snapshot()))
        if path == "/api/ready":
            return self._send(*_json(readiness()))
        if path == "/api/logs":
            return self._send(*_json(latest_log_tail()))
        if path == "/api/demo":
            return self._send(*_json(demo_state()))
        if path == "/api/token":
            # Localhost-only convenience: page bootstraps CSRF token
            return self._send(*_json({"token": SESSION_TOKEN}))
        self._send(*_json({"error": "not found"}, 404))

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        data = self._read_json()
        if not self._check_token(data):
            return self._send(*_json({"ok": False, "error": "bad token"}, 403))
        if path == "/api/control":
            action = str(data.get("action") or "")
            note = str(data.get("note") or "")
            task_id = str(data.get("task_id") or "")
            return self._send(*_json(apply_control(action, note, task_id)))
        if path == "/api/demo":
            return self._send(*_json(start_demo()))
        self._send(*_json({"ok": False, "error": "not found"}, 404))

    def _serve_static(self, name: str, content_type: str) -> None:
        path = STATIC / name
        if not path.exists() or not path.is_file():
            return self._send(*_json({"error": f"missing {name}"}, 404))
        # Prevent path escape
        if not path.resolve().is_relative_to(STATIC.resolve()):
            return self._send(*_json({"error": "forbidden"}, 403))
        body = path.read_bytes()
        # Inject token placeholder for HTML
        if name == "index.html":
            html = body.decode("utf-8").replace("{{TOKEN}}", SESSION_TOKEN)
            body = html.encode("utf-8")
        self._send(200, body, content_type)


def main() -> None:
    _load_dotenv()
    STATE.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"Autocode UI → {url}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
