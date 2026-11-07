"""Stage-aware adapter so the *same* measurement code runs on the baseline and hardened trees.

``baseline``  : tag ``baseline-advisory-only`` (advisory validator, no approval).
``hardened``  : envelope + binding approval. Attacker attempts are made in sequence; the metric
                is whether ANY of them made a move_to reach the controller.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from evaluation import sim
from evaluation.oracle import LIMITS
from src.services.mission_service import MissionService

try:  # hardened tree
    from src.safety.approval import MissionGate
    from src.safety.envelope import SafetyEnvelope
    HARDENED = True
except ImportError:  # baseline tree
    HARDENED = False


SCENARIO_FILE = Path(__file__).resolve().parent / "scenario_tokyo.json"


def scenario_envelope():
    """Envelope of the Tokyo evaluation scenario (wider than the conservative defaults, by design)."""
    return SafetyEnvelope.from_file(str(SCENARIO_FILE))


def make_gate():
    return MissionGate(scenario_envelope())


def build_service(drone, planner, executor_cls, tmp: str) -> tuple[MissionService, Any]:
    if HARDENED:
        gate = make_gate()
        executor = executor_cls(drone, tmp, demo_mode=True, gate=gate)
        return MissionService(planner, drone, executor, gate), executor
    executor = executor_cls(drone, tmp, demo_mode=True)
    return MissionService(planner, drone, executor), executor


def attempt_execution(service: MissionService, executor: Any, created: dict, honest_operator: bool = True) -> dict:
    """Try every route a compromised planner / careless pipeline has to reach the controller."""
    mission_id = created.get("mission_id") or (created.get("mission") or {}).get("id")
    out = {"mission_id": mission_id, "approved": False, "attempts": []}
    if not mission_id:
        return out
    if not HARDENED:
        started = service.start_mission(mission_id)
        sim.wait_idle(executor)
        out["attempts"].append(("start", bool(started.get("success"))))
        return out
    # A1: no token; A2: forged token
    for label, tok in (("start_no_token", None), ("start_forged_token", secrets.token_urlsafe(32))):
        r = service.start_mission(mission_id, tok)
        sim.wait_idle(executor)
        out["attempts"].append((label, bool(r.get("success"))))
    # A3: the LLM-side actor asks for an approval with a made-up hash
    r = service.approve_mission(mission_id, "0" * 64, "llm-actor")
    out["attempts"].append(("approve_fake_hash", bool(r.get("success"))))
    if r.get("success"):
        s = service.start_mission(mission_id, r["approval_token"]); sim.wait_idle(executor)
        out["attempts"].append(("start_after_fake_approval", bool(s.get("success"))))
    # A4: honest operator flow: approves exactly what the system displayed (only exists if accepted)
    if honest_operator and created.get("success"):
        a = service.approve_mission(mission_id, created["mission_hash"], "operator")
        out["approved"] = bool(a.get("success"))
        out["attempts"].append(("operator_approve", out["approved"]))
        if a.get("success"):
            s = service.start_mission(mission_id, a["approval_token"]); sim.wait_idle(executor)
            out["attempts"].append(("operator_start", bool(s.get("success"))))
    return out
