#!/usr/bin/env python3
"""Unit tests for routing — no network / secrets required."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.run_night import (  # noqa: E402
    HardwareSnapshot,
    Task,
    preferred_cloud_target,
    route_task,
)


def make_task(**kwargs) -> Task:
    base = dict(
        page_id="x",
        task_id="BLD-1",
        name="demo",
        acceptance="do a thing",
        complexity="Local-safe",
        model_route="Local Hermes",
        repo="demo",
        priority="P1",
    )
    base.update(kwargs)
    return Task(**base)


class RoutingTests(unittest.TestCase):
    def test_local_safe_goes_local(self) -> None:
        hw = HardwareSnapshot(8000, 16000, 40.0, 0.5, True)
        self.assertEqual(route_task(make_task(), hw, 0), "local")

    def test_cloud_only_escalates(self) -> None:
        hw = HardwareSnapshot(8000, 16000, 40.0, 0.5, True)
        t = make_task(complexity="Cloud-only")
        self.assertNotEqual(route_task(t, hw, 0), "local")

    def test_low_ram_escalates(self) -> None:
        hw = HardwareSnapshot(1000, 8000, 40.0, 0.5, True)
        self.assertNotEqual(route_task(make_task(), hw, 0), "local")

    def test_model_route_claude(self) -> None:
        t = make_task(model_route="Claude")
        self.assertEqual(preferred_cloud_target(t), "Claude")


if __name__ == "__main__":
    unittest.main()
