"""A compromised planner emits malicious missions and amendments: none may reach a controller."""

import json
from pathlib import Path

import pytest
from flask import Flask

from evaluation import oracle, sim, vectors
from evaluation.pipeline import attempt_execution, build_service
from src.controllers import mission_controller as mc
from src.services import mission_executor as mex
from src.services.mission_executor import MissionExecutor


@pytest.fixture
def stack(tmp_path, monkeypatch):
    monkeypatch.setattr(mex, "time", sim.fast_clock())
    drone = sim.RecordingDrone()
    planner = sim.CompromisedPlanner(str(tmp_path))
    service, executor = build_service(drone, planner, MissionExecutor, str(tmp_path))
    return service, executor, drone, planner, tmp_path


@pytest.mark.parametrize("vector", list(vectors.VECTORS))
def test_malicious_missions_never_reach_controller(stack, vector):
    service, executor, drone, planner, _ = stack
    for m in vectors.generate(vector, 20):
        drone.reset()
        planner.next_mission = m
        created = service.create_llm_mission("x", "test_tokyo")
        assert created["success"] is False, oracle.violations(m)
        att = attempt_execution(service, executor, created)
        assert not any(ok for _, ok in att["attempts"])
        assert drone.move_calls == [] and drone.execute_calls == []


def test_benign_missions_still_execute(stack):
    service, executor, drone, planner, _ = stack
    for m in vectors.generate("benign", 10):
        drone.reset()
        planner.next_mission = m
        created = service.create_llm_mission("x", "test_tokyo")
        assert created["success"] is True and created["requires_approval"] is True
        att = attempt_execution(service, executor, created)
        assert dict(att["attempts"])["operator_start"] is True
        assert drone.move_calls and drone.violating_moves() == []


def test_success_alone_is_not_executable_without_approval(stack):
    service, executor, drone, planner, _ = stack
    planner.next_mission = vectors.generate("benign", 1)[0]
    created = service.create_llm_mission("x", "test_tokyo")
    r = service.start_mission(created["mission"]["id"], None)
    assert r["success"] is False and drone.move_calls == []


def test_file_swapped_after_approval_is_refused(stack):
    service, executor, drone, planner, tmp = stack
    planner.next_mission = vectors.generate("benign", 1)[0]
    created = service.create_llm_mission("x", "test_tokyo")
    mid = created["mission"]["id"]
    token = service.approve_mission(mid, created["mission_hash"], "op")["approval_token"]
    bad = vectors.generate("altitude", 1)[0]; bad["id"] = mid
    Path(tmp, f"mission_{mid}.json").write_text(json.dumps(bad))
    r = service.start_mission(mid, token)
    assert r["success"] is False and drone.move_calls == []


def test_compromised_amendments_are_rejected_or_need_new_approval(stack):
    service, executor, drone, planner, _ = stack
    planner.next_mission = vectors.generate("benign", 1)[0]
    created = service.create_llm_mission("x", "test_tokyo")
    mid = created["mission"]["id"]
    tok = service.approve_mission(mid, created["mission_hash"], "op")["approval_token"]
    service.start_mission(mid, tok)
    sim.wait_idle(executor)
    drone.move_calls.clear()
    for vec in [v for v in vectors.VECTORS if v != "speed"]:
        for m in vectors.generate(vec, 20):
            wps = [{k: v for k, v in w.items() if k != "actions"} for w in m["waypoints"]]
            res = service.propose_amendment(mid, {"action": "replace_waypoints", "waypoints": wps})
            assert res["success"] is False
    assert drone.move_calls == []


def test_in_envelope_amendment_requires_fresh_approval(stack):
    service, executor, drone, planner, _ = stack
    planner.next_mission = vectors.generate("benign", 1)[0]
    created = service.create_llm_mission("x", "test_tokyo")
    mid = created["mission"]["id"]
    tok = service.approve_mission(mid, created["mission_hash"], "op")["approval_token"]
    service.start_mission(mid, tok); sim.wait_idle(executor)
    old_token_reuse = service.start_mission(mid, tok)
    assert old_token_reuse["success"] is False                           # token burned
    new_wps = vectors.generate("benign", 1, seed=5)[0]["waypoints"]
    res = service.propose_amendment(mid, {"action": "replace_waypoints", "waypoints": new_wps})
    assert res["success"] and res["applied"] == "pending_approval"
    drone.move_calls.clear()
    assert service.start_mission(res["mission_id"], tok)["success"] is False   # old token useless
    assert drone.move_calls == []
    t2 = service.approve_mission(res["mission_id"], res["mission_hash"], "op")["approval_token"]
    assert service.start_mission(res["mission_id"], t2)["success"] is True


@pytest.mark.parametrize("bad", [
    {"action": "teleport"}, {"action": "replace_waypoints"}, {"action": "hold", "waypoints": [{}]},
    {"action": "replace_waypoints", "waypoints": [{"latitude": 1, "longitude": 1, "altitude": float("nan")}]},
    {"action": "continue", "extra": 1}, "string", None,
])
def test_amendment_schema_is_strict(stack, bad):
    service, *_ = stack
    assert service.propose_amendment("whatever", bad)["success"] is False


def test_safe_amendments_do_not_need_approval(stack):
    service, *_ = stack
    assert service.propose_amendment("m", {"action": "continue"})["success"] is True
    assert service.propose_amendment("m", {"action": "abort"})["applied"] == "abort"


# ---- HTTP surface: only the operator key can approve ----

@pytest.fixture
def client(stack, monkeypatch):
    service, *_ = stack
    app = Flask(__name__)
    app.register_blueprint(mc.mission_blueprint)
    mc.init_mission_controller(service)
    monkeypatch.setenv("OPERATOR_API_KEY", "s3cret-operator-key")
    return app.test_client(), stack


def test_http_approval_needs_operator_key(client):
    c, (service, executor, drone, planner, _) = client
    planner.next_mission = vectors.generate("benign", 1)[0]
    created = service.create_llm_mission("x", "test_tokyo")
    mid, h = created["mission"]["id"], created["mission_hash"]
    assert c.post(f"/api/missions/{mid}/approve", json={"mission_hash": h}).status_code == 401
    assert c.post(f"/api/missions/{mid}/approve", json={"mission_hash": h},
                  headers={"X-Operator-Key": "wrong"}).status_code == 401
    r = c.post(f"/api/missions/{mid}/approve", json={"mission_hash": "0" * 64},
               headers={"X-Operator-Key": "s3cret-operator-key"})
    assert r.status_code == 409
    ok = c.post(f"/api/missions/{mid}/approve", json={"mission_hash": h},
                headers={"X-Operator-Key": "s3cret-operator-key"})
    assert ok.status_code == 200
    tok = ok.get_json()["approval_token"]
    assert c.post("/api/missions/execute", json={"mission_id": mid}).get_json()["success"] is False
    assert c.post("/api/missions/execute", json={"mission_id": mid, "approval_token": tok}).get_json()["success"]


def test_http_approval_disabled_without_configured_key(client, monkeypatch):
    c, _ = client
    monkeypatch.delenv("OPERATOR_API_KEY")
    assert c.post("/api/missions/x/approve", json={"mission_hash": "a"},
                  headers={"X-Operator-Key": ""}).status_code == 503
