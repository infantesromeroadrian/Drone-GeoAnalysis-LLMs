"""Tests for mission_executor.py -- background mission execution engine."""

import json
import os
import pytest
from unittest.mock import MagicMock
from src.services.mission_executor import MissionExecutor
from tests.conftest import wait_for_status, wait_for_waypoint, wait_for_call_count


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_drone():
    drone = MagicMock()
    drone.current_position = {"latitude": 40.0, "longitude": -74.0, "altitude": 0.0}
    drone.move_to.return_value = True
    return drone


@pytest.fixture
def missions_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def executor(mock_drone, missions_dir):
    return MissionExecutor(mock_drone, missions_dir)


def _create_mission(missions_dir: str, mission_id: str, waypoints: list) -> str:
    mission = {
        "id": mission_id,
        "mission_name": "Test Mission",
        "waypoints": waypoints,
    }
    path = os.path.join(missions_dir, f"mission_{mission_id}.json")
    with open(path, "w") as f:
        json.dump(mission, f)
    return mission_id


# ---------------------------------------------------------------------------
# TestMissionExecutorStart
# ---------------------------------------------------------------------------

class TestMissionExecutorStart:

    def test_start_valid_mission(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "abc123", [
            {"latitude": 40.1, "longitude": -74.1, "altitude": 30, "action": "navigate", "duration": 0},
        ])
        result = executor.start(mid)
        assert result["success"] is True
        assert result["waypoints"] == 1

    def test_start_nonexistent_mission(self, executor):
        result = executor.start("nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_start_empty_waypoints(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "empty", [])
        result = executor.start(mid)
        assert result["success"] is False
        assert "no waypoints" in result["error"]

    def test_cannot_start_while_flying(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "fly1", [
            {"latitude": 40.1, "longitude": -74.1, "altitude": 30, "action": "navigate", "duration": 0},
            {"latitude": 40.2, "longitude": -74.2, "altitude": 30, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        result = executor.start(mid)
        assert result["success"] is False
        assert "already in progress" in result["error"]


# ---------------------------------------------------------------------------
# TestMissionExecutorStatus
# ---------------------------------------------------------------------------

class TestMissionExecutorStatus:

    def test_initial_status_idle(self, executor):
        status = executor.get_status()
        assert status["status"] == "idle"

    def test_status_during_flight(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "status1", [
            {"latitude": 41.0, "longitude": -75.0, "altitude": 50, "action": "navigate", "duration": 0},
            {"latitude": 42.0, "longitude": -76.0, "altitude": 50, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        # Wait until the executor is actually running rather than sleeping a fixed interval.
        assert wait_for_status(executor, "flying", timeout=2.0), "executor did not reach 'flying' in time"
        status = executor.get_status()
        assert status["status"] in ("flying", "completed")
        assert status["total_waypoints"] == 2
        assert status["mission_id"] == mid

    def test_status_completed(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "done1", [
            {"latitude": 40.01, "longitude": -74.01, "altitude": 10, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        assert wait_for_status(executor, "completed", timeout=10.0), "mission did not complete in time"
        status = executor.get_status()
        assert status["status"] == "completed"
        assert status["progress_pct"] == 100.0
        assert status["current_waypoint"] == 1


# ---------------------------------------------------------------------------
# TestMissionExecutorAbort
# ---------------------------------------------------------------------------

class TestMissionExecutorAbort:

    def test_abort_no_mission(self, executor):
        result = executor.abort()
        assert result["success"] is False

    def test_abort_during_flight(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "abort1", [
            {"latitude": 80.0, "longitude": -170.0, "altitude": 50, "action": "navigate", "duration": 0},
            {"latitude": -80.0, "longitude": 170.0, "altitude": 50, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        assert wait_for_status(executor, "flying", timeout=2.0), "executor did not reach 'flying' before abort"
        result = executor.abort()
        assert result["success"] is True
        assert wait_for_status(executor, "aborted", timeout=5.0), "executor did not reach 'aborted' in time"
        assert executor.get_status()["status"] == "aborted"


# ---------------------------------------------------------------------------
# TestMissionExecutorDroneInteraction
# ---------------------------------------------------------------------------

class TestMissionExecutorDroneInteraction:

    def test_move_to_called_for_each_waypoint(self, executor, missions_dir, mock_drone):
        mid = _create_mission(missions_dir, "move1", [
            {"latitude": 40.1, "longitude": -74.1, "altitude": 30, "action": "navigate", "duration": 0},
            {"latitude": 40.2, "longitude": -74.2, "altitude": 40, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        assert wait_for_call_count(mock_drone.move_to, 2, timeout=20.0), (
            f"move_to not called twice; got {mock_drone.move_to.call_count}"
        )
        assert mock_drone.move_to.call_count == 2

    def test_position_interpolation(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "interp1", [
            {"latitude": 41.0, "longitude": -75.0, "altitude": 50, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        # Wait until executor is running so position has been updated at least once.
        assert wait_for_status(executor, "flying", timeout=5.0), "executor did not reach 'flying' in time"
        status = executor.get_status()
        pos = status["position"]
        assert pos["latitude"] != 40.0 or pos["longitude"] != -74.0
