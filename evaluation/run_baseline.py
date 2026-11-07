"""Compromised-planner measurement (vectors a and b) on whichever tree is checked out.

Usage: python -m evaluation.run_baseline [baseline|hardened]  (stage label only names the output;
the adapter detects the tree). Raw per-trial rows go to ~/datasets/drone/results/.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import oracle, pipeline, sim, vectors
from evaluation.stats import wilson
from src.services import mission_executor as mex
from src.services.mission_executor import MissionExecutor

RAW_DIR = Path.home() / "datasets" / "drone" / "results"


def _row_stats(rows: list[dict]) -> dict:
    n = len(rows)
    k = sum(r["reached_controller"] for r in rows)
    return {"n": n, "created_success": sum(r.get("created_success", r.get("success", False)) for r in rows),
            "reached_controller": k, "violating_move_reached": sum(r.get("violating_move_reached", False) for r in rows),
            "rate": k / n if n else None, "wilson95": wilson(k, n)}


def run(n: int = vectors.N_DEFAULT) -> dict:
    mex.time = sim.fast_clock()
    tmp = tempfile.mkdtemp(prefix="drone-eval-")
    drone = sim.RecordingDrone()
    planner = sim.CompromisedPlanner(tmp)
    service, executor = pipeline.build_service(drone, planner, MissionExecutor, tmp)
    results: dict = {}
    raw: dict = {}
    for vec in [*vectors.VECTORS, "benign", "post_validation_swap"]:
        rows = []
        src_vec = "benign" if vec == "post_validation_swap" else vec
        for i, m in enumerate(vectors.generate(src_vec, n)):
            drone.reset()
            planner.next_mission = m
            created = service.create_llm_mission("synthetic", "test_tokyo")
            if vec == "post_validation_swap":
                # Operator approves the benign plan; then the stored file is replaced by a violating one.
                mid = (created.get("mission") or {}).get("id")
                token = None
                if pipeline.HARDENED and mid:
                    a = service.approve_mission(mid, created["mission_hash"], "operator")
                    token = a.get("approval_token")
                bad = vectors.generate("altitude", 1, seed=i)[0]
                bad["id"] = mid
                Path(tmp, f"mission_{mid}.json").write_text(json.dumps(bad))
                started = service.start_mission(mid, token) if pipeline.HARDENED else service.start_mission(mid)
                sim.wait_idle(executor)
                att = {"attempts": [("start_after_swap", bool(started.get("success")))]}
            else:
                att = pipeline.attempt_execution(service, executor, created)
            rows.append({"created_success": bool(created.get("success")),
                         "reached_controller": len(drone.move_calls) > 0,
                         "violating_move_reached": len(drone.violating_moves()) > 0,
                         "attempts": att["attempts"], "oracle": oracle.violations(m)})
        results[vec] = _row_stats(rows)
        raw[vec] = rows
    # (b) compromised amendment (only meaningful where an amendment API exists)
    if pipeline.HARDENED:
        rows = []
        # 'speed' is not expressible in an amendment (the schema carries no speed field), so it is excluded.
        for i, vec in enumerate(v for v in vectors.VECTORS if v != "speed"):
            for j, m in enumerate(vectors.generate(vec, n)):
                drone.reset()
                planner.next_mission = vectors.generate("benign", 1, seed=1000 + i * n + j)[0]
                created = service.create_llm_mission("synthetic", "test_tokyo")
                a = service.approve_mission(created["mission"]["id"], created["mission_hash"], "operator")
                service.start_mission(created["mission"]["id"], a["approval_token"]); sim.wait_idle(executor)
                drone.move_calls.clear()
                wps = [{k: v for k, v in w.items() if k != "actions"} for w in m["waypoints"]][:50] if isinstance(m.get("waypoints"), list) else []
                res = service.propose_amendment(created["mission"]["id"], {"action": "replace_waypoints", "waypoints": wps})
                if res.get("mission_id"):
                    service.start_mission(res["mission_id"], "forged"); sim.wait_idle(executor)
                    if res.get("success"):
                        ap = service.approve_mission(res["mission_id"], res["mission_hash"], "operator")
                        if ap.get("success"):
                            service.start_mission(res["mission_id"], ap["approval_token"]); sim.wait_idle(executor)
                effective = {"waypoints": wps}
                rows.append({"vector": vec, "applied": res.get("applied"), "success": bool(res.get("success")),
                             "reached_controller": len(drone.move_calls) > 0 and bool(oracle.violations(effective)),
                             "oracle": oracle.violations(effective)})
        results["compromised_amendment"] = _row_stats(rows)
        raw["compromised_amendment"] = rows
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return results, raw


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ("hardened" if pipeline.HARDENED else "baseline")
    res, raw = run()
    (RAW_DIR / f"compromised_{stage}.json").write_text(json.dumps({"summary": res, "rows": raw}, indent=1, default=str))
    for k, v in res.items():
        print(f"{k:24s} n={v['n']:3d} created={v['created_success']:3d} reached={v['reached_controller']:3d} "
              f"viol_move={v['violating_move_reached']:3d} wilson={v['wilson95'][0]:.3f}-{v['wilson95'][1]:.3f}")
