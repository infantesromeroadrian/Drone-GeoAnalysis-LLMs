"""No code path reaches a controller's motion/mission methods without the gate or the envelope guard.

Static inventory (AST) + runtime structure checks. See docs/case-study.md, "Route inventory".
"""

import ast
from pathlib import Path

import pytest

from src.drones import dji_controller, parrot_anafi_controller
from src.drones.base_drone import BaseDrone
from src.safety.approval import ApprovalError
from src.services.mission_executor import MissionExecutor

SRC = Path(__file__).resolve().parents[2] / "src"
GUARDED = {"move_to", "take_off", "execute_mission", "_do_move_to", "_do_take_off", "_execute_approved"}

# (file, enclosing function) -> why this call site is legitimate
ALLOWED_CALL_SITES = {
    ("services/mission_executor.py", "_execute"): "executor thread: runs only an ApprovedMission; move_to is guarded",
    ("drones/base_drone.py", "execute_mission"): "template: ApprovedMission.require() then _execute_approved",
    ("drones/base_drone.py", "move_to"): "template: envelope check then _do_move_to",
    ("drones/base_drone.py", "take_off"): "template: envelope check then _do_take_off",
    ("drones/dji_controller.py", "_execute_waypoints"): "reached only via _execute_approved; move_to is guarded",
    ("drones/parrot_anafi_controller.py", "_execute_approved"): "approved waypoints; move_to is guarded",
    ("services/drone_service.py", "takeoff"): "manual control: altitude pre-check + guarded take_off (home = launch point)",
    ("services/mission_service.py", "execute_mission"): "service API: delegates to executor.start (token required)",
    ("services/mission_service.py", "start_mission"): "service API: delegates to execute_mission",
    ("controllers/mission_controller.py", "start_mission"): "HTTP -> service (token)",
    ("controllers/mission_controller.py", "execute_mission"): "HTTP -> service (token)",
    ("controllers/drone_controller.py", "takeoff_drone"): "HTTP -> drone_service.takeoff (guarded)",
}


def _call_sites():
    sites = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).as_posix()
        tree = ast.parse(path.read_text())
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in GUARDED:
                    sites.append((rel, fn.name, node.func.attr, node.lineno))
    return sites


def test_every_call_to_a_motion_method_is_in_the_reviewed_inventory():
    unknown = [(f, fn, attr, ln) for f, fn, attr, ln in _call_sites() if (f, fn) not in ALLOWED_CALL_SITES]
    assert unknown == [], f"new call site(s) reaching controller motion methods, review them: {unknown}"


def test_inventory_entries_are_not_stale():
    live = {(f, fn) for f, fn, *_ in _call_sites()}
    stale = set(ALLOWED_CALL_SITES) - live
    # service/controller wrappers call differently named attrs; only require that drone/executor sites exist
    assert ("services/mission_executor.py", "_execute") in live
    assert stale <= {k for k in ALLOWED_CALL_SITES if k[0].startswith(("controllers/", "services/mission_service"))}


def test_no_subclass_overrides_the_guarded_template_methods():
    for cls in (dji_controller.DJIDroneController, parrot_anafi_controller.ParrotAnafiController):
        for name in ("move_to", "take_off", "execute_mission"):
            assert getattr(cls, name) is getattr(BaseDrone, name), f"{cls.__name__} overrides {name}"
    for cls in BaseDrone.__subclasses__():
        for name in ("move_to", "take_off", "execute_mission"):
            if cls.__module__.startswith("src."):
                assert name not in vars(cls), f"{cls.__name__} overrides {name}"


def test_llm_agent_tools_cannot_reach_drone_code():
    """The LangGraph agent's tools live in src/models; none of that package may import the drone layer."""
    for path in (SRC / "models").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            assert not any(m.startswith(("src.drones", "src.services.mission_executor")) for m in mods), path.name
    from src.models import mission_agent
    names = {t.name for t in mission_agent.ALL_TOOLS}
    assert names == {"load_area_info", "validate_mission", "generate_area_grid_waypoints",
                     "calculate_waypoint_distances", "finalize_mission"}


def test_executor_without_gate_or_token_never_touches_the_drone(tmp_path):
    from unittest.mock import MagicMock
    drone = MagicMock(); drone.current_position = {"latitude": 0, "longitude": 0, "altitude": 0}
    (tmp_path / "mission_a.json").write_text('{"waypoints":[{"latitude":0,"longitude":0,"altitude":50}]}')
    assert MissionExecutor(drone, str(tmp_path), demo_mode=True).start("a", "tok")["success"] is False
    from src.safety.approval import MissionGate
    ex = MissionExecutor(drone, str(tmp_path), demo_mode=True, gate=MissionGate())
    assert ex.start("a", None)["success"] is False and ex.start("a", "forged")["success"] is False
    assert drone.move_to.call_count == 0


@pytest.mark.parametrize("cls_factory", [
    lambda: dji_controller.DJIDroneController(simulation_mode=True),
    lambda: parrot_anafi_controller.ParrotAnafiController(),
])
def test_controllers_refuse_plain_dict_missions_and_unhomed_moves(cls_factory):
    d = cls_factory()
    d.connect()
    with pytest.raises(ApprovalError):
        d.execute_mission({"waypoints": [{"latitude": 0, "longitude": 0, "altitude": 50}]})
    assert d.move_to(d.current_position["latitude"], d.current_position["longitude"], 50) is False  # no home


def test_guard_blocks_out_of_envelope_motion_even_for_manual_control():
    d = parrot_anafi_controller.ParrotAnafiController()
    d.connect()
    assert d.take_off(500.0) is False                       # altitude above envelope
    assert d.take_off(30.0) is True                         # home := launch point
    p = d.current_position
    assert d.move_to(p["latitude"], p["longitude"], 130.0) is False
    assert d.move_to(p["latitude"] + 0.05, p["longitude"], 50.0) is False   # ~5.5 km from home
    assert d.move_to(p["latitude"] + 0.001, p["longitude"], 50.0) is True


def test_route_inventory_documented_in_case_study():
    doc = (SRC.parent / "docs" / "case-study.md")
    if doc.exists():
        text = doc.read_text()
        for key, _ in ALLOWED_CALL_SITES:
            assert key.split("/")[-1] in text, f"{key} missing from the route inventory table"
