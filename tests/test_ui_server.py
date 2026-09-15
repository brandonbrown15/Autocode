#!/usr/bin/env python3
"""Tests for Autocode local UI server helpers."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import ops  # noqa: E402
from ui import server as ui_server  # noqa: E402


class UiHelpersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="autocode-ui-"))
        self._old_status = ops.STATUS_PATH
        self._old_control = ops.CONTROL_PATH
        self._old_demo = ui_server._demo_log
        ops.STATUS_PATH = self.tmp / "status.json"
        ops.CONTROL_PATH = self.tmp / "control.json"
        ui_server._demo_log = self.tmp / "ui-demo.log"
        ui_server.STATE = self.tmp

    def tearDown(self) -> None:
        ops.STATUS_PATH = self._old_status
        ops.CONTROL_PATH = self._old_control
        ui_server._demo_log = self._old_demo

    def test_snapshot_and_control(self) -> None:
        ops.write_status(phase="running_local", task_id="BLD-1", task_name="docs", route="local")
        snap = ui_server.snapshot()
        self.assertEqual(snap["status"]["phase"], "running_local")
        self.assertIn("token", snap)

        out = ui_server.apply_control("pause", note="ui test")
        self.assertTrue(out["ok"])
        self.assertTrue(ops.load_control().paused)

        out = ui_server.apply_control("resume")
        self.assertTrue(out["ok"])
        self.assertFalse(ops.load_control().paused)

        out = ui_server.apply_control("skip", task_id="BLD-9")
        self.assertTrue(out["ok"])
        self.assertEqual(ops.load_control().skip_task_id, "BLD-9")

        out = ui_server.apply_control("skip")
        self.assertFalse(out["ok"])

    def test_readiness_shape(self) -> None:
        with mock.patch.object(ui_server.health_mod, "check_local_stack") as chk:
            chk.return_value = mock.Mock(
                hermes_ok=True,
                ollama_ok=True,
                ollama_model="coder-64k",
                details=["hermes: present", "ollama: ok"],
            )
            data = ui_server.readiness()
        self.assertIn("checks", data)
        self.assertIn("ready", data)
        ids = {c["id"] for c in data["checks"]}
        self.assertIn("hermes", ids)
        self.assertIn("notion", ids)

    def test_http_status_and_control(self) -> None:
        ops.write_status(phase="idle", detail="test")
        httpd = ui_server.ThreadingHTTPServer(("127.0.0.1", 0), ui_server.Handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5) as resp:
                snap = json.loads(resp.read().decode())
            self.assertEqual(snap["status"]["phase"], "idle")
            token = snap["token"]

            body = json.dumps({"action": "pause", "note": "http", "token": token}).encode()
            req = request.Request(
                f"http://127.0.0.1:{port}/api/control",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Autocode-Token": token,
                },
                method="POST",
            )
            with request.urlopen(req, timeout=5) as resp:
                out = json.loads(resp.read().decode())
            self.assertTrue(out["ok"])
            self.assertTrue(ops.load_control().paused)

            bad = request.Request(
                f"http://127.0.0.1:{port}/api/control",
                data=json.dumps({"action": "resume", "token": "nope"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(error.HTTPError) as ctx:
                request.urlopen(bad, timeout=5)
            self.assertEqual(ctx.exception.code, 403)

            with request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as resp:
                html = resp.read().decode()
            self.assertIn("Autocode", html)
            self.assertIn(token, html)
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
