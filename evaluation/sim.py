"""Simulation fixtures: recording mock controller and a compromised-planner stub.

Nothing here talks to hardware. The mock records every command the controller receives so that
"reached execution" is measured at the lowest level (a ``move_to`` call), not inferred from API flags.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from types import SimpleNamespace
from typing import Any

from evaluation.oracle import HOME, point_violations
from src.drones.base_drone import BaseDrone

GUARDED = hasattr(BaseDrone, "_do_move_to")


class RecordingDrone(BaseDrone):
    """Mock controller: records move_to / execute_mission calls, never moves anything."""

    def __init__(self) -> None:
        self.current_position = {"latitude": HOME[0], "longitude": HOME[1], "altitude": 0.0}
        self.home_position = None
        self.move_calls: list[tuple[float, float, float]] = []
        self.execute_calls: list[Any] = []
        self.rejected_moves: list[tuple[float, float, float]] = []
        self._lock = threading.Lock()

    def reset(self) -> None:
        self.current_position = {"latitude": HOME[0], "longitude": HOME[1], "altitude": 0.0}
        self.home_position = None
        self.move_calls.clear(); self.execute_calls.clear(); self.rejected_moves.clear()

    def violating_moves(self) -> list[tuple[float, float, float]]:
        return [m for m in self.move_calls if point_violations(*m)]

    def connect(self) -> bool: return True
    def disconnect(self) -> bool: return True
    def land(self) -> bool: return True
    def capture_image(self) -> str: return ""
    def start_video_stream(self) -> str: return ""
    def stop_video_stream(self) -> bool: return True
    def get_telemetry(self) -> dict[str, Any]: return {}

    def _record_move(self, latitude: float, longitude: float, altitude: float) -> bool:
        with self._lock:
            self.move_calls.append((latitude, longitude, altitude))
        return True

    def _record_execute(self, mission_data: Any) -> bool:
        self.execute_calls.append(mission_data)
        return True

    if GUARDED:
        # Hardened tree: BaseDrone.move_to / take_off / execute_mission are the guarded template
        # methods; the mock only implements the controller-specific hooks, like a real controller.
        def _do_move_to(self, latitude, longitude, altitude, **_): return self._record_move(latitude, longitude, altitude)
        def _do_take_off(self, altitude): return True
        def _execute_approved(self, waypoints): return self._record_execute(waypoints)
    else:
        # Baseline tree (tag baseline-advisory-only): no guard exists; the mock is the controller.
        def move_to(self, latitude, longitude, altitude, **_): return self._record_move(latitude, longitude, altitude)
        def take_off(self, altitude): return True
        def execute_mission(self, mission_data): return self._record_execute(mission_data)


class CompromisedPlanner:
    """Stands in for an LLM planner under attacker control: emits whatever mission it is told to.

    Persists the mission exactly as the production pipeline does (``mission_<id>.json``).
    """

    def __init__(self, missions_dir: str) -> None:
        self.missions_dir = missions_dir
        self.next_mission: dict[str, Any] | None = None

    def create_mission_from_command(self, natural_command: str, area_name: str | None = None) -> dict[str, Any] | None:
        m = json.loads(json.dumps(self.next_mission))  # NaN/inf survive json round trip in python
        m["id"] = str(uuid.uuid4())
        m["status"] = "planned"
        with open(os.path.join(self.missions_dir, f"mission_{m['id']}.json"), "w", encoding="utf-8") as f:
            json.dump(m, f)
        return m

    def get_available_missions(self) -> list:
        return []


def fast_clock() -> SimpleNamespace:
    """Replacement for the ``time`` module inside mission_executor: sleeps are no-ops (simulation only)."""
    return SimpleNamespace(sleep=lambda s: None, time=time.time)


def wait_idle(executor: Any, timeout: float = 30.0) -> str:
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = executor.get_status()["status"]
        if st != "flying":
            return st
        time.sleep(0.005)
    return "timeout"
