"""Real-LLM measurement through the production legacy pipeline (LLMClient -> MissionDataProcessor).

Model: Ollama (default gpt-oss:120b-cloud), fixed temperature and seed. Raw per-trial records go
to ~/datasets/drone/results/ (outside the Proton-synced tree); only aggregates are committed.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

os.environ.setdefault("LLM_PROVIDER", "ollama")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import commands, oracle, pipeline, sim
from evaluation.stats import wilson
from src.models.mission_planner import LLMMissionPlanner
from src.services import mission_executor as mex
from src.services.mission_executor import MissionExecutor

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = Path.home() / "datasets" / "drone" / "results"


def model_provenance() -> dict:
    base = os.environ.get("OLLAMA_HOST_URL", "http://localhost:11434")
    name = os.environ.get("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    prov = {"model": name, "temperature": float(os.environ.get("OLLAMA_TEMPERATURE", "0.3")),
            "seed": int(os.environ.get("OLLAMA_SEED", "7")),
            "reasoning_effort": os.environ.get("OLLAMA_REASONING_EFFORT", "low"),
            "max_tokens": int(os.environ.get("OLLAMA_MAX_TOKENS", "4000"))}
    try:
        tags = json.load(urllib.request.urlopen(f"{base}/api/tags", timeout=10))
        for m in tags.get("models", []):
            if m["name"] == name:
                prov["digest"] = m.get("digest")
        prov["ollama_version"] = json.load(urllib.request.urlopen(f"{base}/api/version", timeout=10))["version"]
    except Exception as e:  # provenance is best-effort, never fatal
        prov["provenance_error"] = str(e)
    return prov


def build(stage_adapter=None):
    mex.time = sim.fast_clock()
    tmp = tempfile.mkdtemp(prefix="drone-llm-eval-")
    planner = LLMMissionPlanner()
    planner.agent = None  # production fallback path: LLMClient legacy pipeline (agent is Groq-bound)
    planner.mission_processor.missions_dir = tmp
    cart = ROOT / "cartography" / "test_tokyo.geojson"
    assert planner.load_cartography(str(cart), "test_tokyo")
    drone = sim.RecordingDrone()
    service, executor = pipeline.build_service(drone, planner, MissionExecutor, tmp)
    return service, drone, executor


def trial(service, drone, executor, command: str) -> dict:
    drone.reset()
    t0 = time.time()
    created = service.create_llm_mission(command, "test_tokyo")
    mission = created.get("mission") or {}
    if not mission and created.get("mission_id"):  # hardened tree withholds rejected missions: read the stored plan
        mission = executor.load_mission(created["mission_id"]) or {}
    viol = oracle.violations(mission) if mission else None
    att = pipeline.attempt_execution(service, executor, created)
    started = {"success": any(ok for _, ok in att["attempts"])}
    return {"command": command, "created_success": bool(created.get("success")),
            "mission_produced": bool(mission), "oracle_violations": viol,
            "out_of_envelope": bool(viol), "start_success": bool(started.get("success")),
            "reached_controller": len(drone.move_calls) > 0, "seconds": round(time.time() - t0, 1),
            "error": created.get("error")}


def main(stage: str = "baseline") -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    prov = model_provenance()
    service, drone, executor = build()
    unsafe_rows, benign_rows = [], []
    for cls, cmd in commands.UNSAFE:
        r = trial(service, drone, executor, cmd); r["requested_class"] = cls; unsafe_rows.append(r)
        print(cls, r["out_of_envelope"], r["oracle_violations"], r["reached_controller"], flush=True)
    for cmd in commands.BENIGN:
        r = trial(service, drone, executor, cmd); benign_rows.append(r)
        print("benign", r["out_of_envelope"], r["oracle_violations"], r["reached_controller"], flush=True)
    (RAW_DIR / f"llm_{stage}.json").write_text(json.dumps({"provenance": prov, "unsafe": unsafe_rows, "benign": benign_rows}, indent=1))
    def agg(rows):
        n = len(rows)
        produced_oob = sum(1 for r in rows if r["out_of_envelope"])
        reached_oob = sum(1 for r in rows if r["out_of_envelope"] and r["reached_controller"])
        return {"n": n, "mission_out_of_envelope": produced_oob, "out_of_envelope_reached_controller": reached_oob,
                "rate_reached": reached_oob / n if n else None, "wilson95": wilson(reached_oob, n)}
    out = {"provenance": prov, "operator_unsafe_request": agg(unsafe_rows),
           "benign": {**agg(benign_rows), "accepted_and_executed": sum(1 for r in benign_rows if r["reached_controller"])}}
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "baseline")
