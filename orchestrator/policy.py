#!/usr/bin/env python3
"""Cost-aware, task-dependent model routing for Autocode.

Goal: maximize local/cheap work; send only heavy tasks to premium models.

Tier ladder (cheap → expensive), overridable via env:
  local → Grok Bot → Claude → Cursor Cloud → Human
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


# Default cost ladder (index 0 = cheapest cloud, 1 = mid-range, 2 = premium)
# Mid-range (Claude) is for "too hard for local, too easy for Cursor".
DEFAULT_LADDER = ("Grok Bot", "Claude", "Cursor Cloud", "Human")

# Explicit Notion Model route overrides always win.
ROUTE_ALIASES = {
    "Local Hermes": "local",
    "local": "local",
    "Grok": "Grok Bot",
    "Grok Bot": "Grok Bot",
    "Claude": "Claude",
    "Cursor Cloud": "Cursor Cloud",
    "Human": "Human",
}

HEAVY_KEYWORDS = (
    "auth",
    "oauth",
    "billing",
    "payment",
    "infra",
    "kubernetes",
    "k8s",
    "terraform",
    "security",
    "migration",
    "architecture",
    "refactor",
    "multi-repo",
    "database schema",
    "prod",
    "production",
    "incident",
)


@dataclass(frozen=True)
class RouteDecision:
    target: str
    tier: str  # local | cheap | standard | premium | human
    reason: str
    score: int


def _ladder() -> list[str]:
    raw = os.environ.get("AUTOCODE_COST_LADDER", "")
    if raw.strip():
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if parts:
            return parts
    return list(DEFAULT_LADDER)


def _available(target: str) -> bool:
    if target == "local":
        return True
    if target == "Human":
        return True
    if target == "Grok Bot":
        return bool(
            os.environ.get("AUTOCODE_GROK_DELEGATE_CMD")
            or os.environ.get("XAI_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
        )
    if target == "Claude":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if target == "Cursor Cloud":
        return bool(
            os.environ.get("AUTOCODE_CURSOR_DELEGATE_CMD")
            or os.environ.get("CURSOR_API_KEY")
        )
    return False


def _first_available(candidates: list[str], assume_keys: bool = False) -> str:
    """Pick first candidate that is configured. If assume_keys, skip availability checks (tests)."""
    for c in candidates:
        if c == "local" or c == "Human" or assume_keys or _available(c):
            return c
    return "Human"


def _text_blob(task: Any) -> str:
    parts = [
        getattr(task, "name", "") or "",
        getattr(task, "acceptance", "") or "",
        getattr(task, "notes", "") or "",
    ]
    return " ".join(parts).lower()


def score_task(task: Any) -> int:
    """Higher score ⇒ heavier / more expensive model.

    Rough scale:
      0–29  local (Jetson / Hermes)
      30–49  cheap cloud (Grok Bot)
      50–69  mid-range / standard (Claude) — hard for local, not worth Cursor
      70+    premium (Cursor Cloud)
    """
    score = 0
    complexity = (getattr(task, "complexity", "") or "").strip()
    priority = (getattr(task, "priority", "") or "").strip().upper()
    model_route = (getattr(task, "model_route", "") or "").strip()

    if complexity == "Local-safe":
        score += 10
    elif complexity == "Maybe local":
        score += 40
    elif complexity == "Cloud-only":
        # Mid by default; P0 / heavy keywords push into premium
        score += 55
    else:
        score += 35

    if priority in ("P0", "0"):
        score += 25
    elif priority in ("P1", "1"):
        score += 15
    elif priority in ("P2", "2"):
        score += 5
    # P3+: no bump

    blob = _text_blob(task)
    hits = sum(1 for kw in HEAVY_KEYWORDS if kw in blob)
    score += min(30, hits * 10)

    # Explicit cloud model route bumps floor into at least mid-range
    if model_route and model_route not in ("Local Hermes", "local"):
        score = max(score, 55)

    return score


def tier_for_score(score: int) -> str:
    if score < 30:
        return "local"
    if score < 50:
        return "cheap"
    if score < 70:
        return "standard"  # mid-range (Claude)
    return "premium"


def target_for_tier(tier: str, assume_keys: bool = False) -> str:
    ladder = _ladder()
    cheap = ladder[0]
    mid = ladder[1] if len(ladder) > 1 else cheap
    prem = ladder[2] if len(ladder) > 2 else ladder[-1]

    # Map semantic tiers onto ladder indices
    if tier == "local":
        return "local"
    if tier == "cheap":
        # Prefer Grok; only spend up if cheaper isn’t configured
        return _first_available([cheap, mid, prem, "Human"], assume_keys=assume_keys)
    if tier == "standard":
        # Mid-range first; fall *back* to cheaper before jumping to premium
        return _first_available([mid, cheap, prem, "Human"], assume_keys=assume_keys)
    if tier == "premium":
        return _first_available([prem, mid, cheap, "Human"], assume_keys=assume_keys)
    return "Human"


def decide_route(
    task: Any,
    *,
    local_failures: int = 0,
    hardware_constrained: bool = False,
    local_stack_ok: bool = True,
    assume_keys: bool = False,
    max_local_attempts: int = 2,
) -> RouteDecision:
    """Return the model/target for this task under a cost-saving policy."""
    model_route = (getattr(task, "model_route", "") or "").strip()
    complexity = (getattr(task, "complexity", "") or "").strip()

    # 1) Explicit Model route always wins (operator override)
    if model_route and model_route not in ("Local Hermes", "local"):
        target = ROUTE_ALIASES.get(model_route, model_route)
        return RouteDecision(
            target=target,
            tier="premium" if target == "Cursor Cloud" else "standard",
            reason=f"explicit Model route={model_route}",
            score=score_task(task),
        )

    score = score_task(task)
    tier = tier_for_score(score)

    # 2) Force escalate when local cannot run
    if hardware_constrained or not local_stack_ok or local_failures >= max_local_attempts:
        # Keep cost discipline: escalate to the tier the task deserves, not always premium
        if tier == "local":
            tier = "cheap"  # light task that only failed locally → cheapest cloud
        reason_bits = []
        if hardware_constrained:
            reason_bits.append("hardware constrained")
        if not local_stack_ok:
            reason_bits.append("local stack unhealthy")
        if local_failures >= max_local_attempts:
            reason_bits.append(f"local failures={local_failures}")
        target = target_for_tier(tier, assume_keys=assume_keys)
        return RouteDecision(
            target=target,
            tier=tier,
            reason=f"escalate ({', '.join(reason_bits)}); score={score}",
            score=score,
        )

    # 3) Cloud-only never stays local — usually mid-range, premium only if score says so
    if complexity == "Cloud-only":
        if tier == "local":
            tier = "standard"
        target = target_for_tier(tier, assume_keys=assume_keys)
        return RouteDecision(
            target=target,
            tier=tier,
            reason=f"Cloud-only; score={score} → {tier} (mid unless heavy)",
            score=score,
        )

    # 4) Normal cost ladder
    if tier == "local":
        return RouteDecision(
            target="local",
            tier="local",
            reason=f"Local-safe / low score={score}",
            score=score,
        )

    # Maybe-local with mid score: still try local first unless score is high
    if complexity == "Maybe local" and score < 55:
        return RouteDecision(
            target="local",
            tier="local",
            reason=f"Maybe local; try local first (score={score})",
            score=score,
        )

    target = target_for_tier(tier, assume_keys=assume_keys)
    return RouteDecision(
        target=target,
        tier=tier,
        reason=f"score={score} → tier={tier}",
        score=score,
    )


def describe_policy() -> str:
    ladder = " → ".join(["local", *_ladder()])
    return (
        "Cost policy: prefer local; escalate only as heavy as needed.\n"
        f"Ladder: {ladder}\n"
        "Score: Local-safe≈10, Maybe≈40, Cloud-only≈70; +P0/P1; +keyword bumps.\n"
        "Overrides: Notion Model route always wins."
    )
