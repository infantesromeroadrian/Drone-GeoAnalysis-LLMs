"""Tests for mission_executor.py -- background mission execution engine."""

import json
import logging
import os
import time
import pytest
from unittest.mock import MagicMock
from src.services.mission_executor import MissionExecutor


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
    """Demo_mode for fast test execution; realistic speeds tested separately."""
    return MissionExecutor(mock_drone, missions_dir, demo_mode=True)


def _create_mission(missions_dir, mission_id, waypoints):
    mission = {
        "id": mission_id,
        "mission_name": "Test Mission",
        "waypoints": waypoints,
    }
    path = os.path.join(missions_dir, f"mission_{mission_id}.json")
    with open(path, "w") as f:
        json.dump(mission, f)
    return mission_id


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


class TestMissionExecutorStatus:

    def test_initial_status_idle(self, executor):
        status = executor.get_status()
        assert status["status"] == "idle"

    def test_status_during_flight(self, executor, missions_dir):
        # Short hops keep total flight time bounded after MAX_SEGMENT_DURATION cap removal.
        mid = _create_mission(missions_dir, "status1", [
            {"latitude": 40.05, "longitude": -74.05, "altitude": 50, "action": "navigate", "duration": 0},
            {"latitude": 40.10, "longitude": -74.10, "altitude": 50, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        time.sleep(0.5)
        status = executor.get_status()
        assert status["status"] in ("flying", "completed")
        assert status["total_waypoints"] == 2
        assert status["mission_id"] == mid

    def test_status_completed(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "done1", [
            {"latitude": 40.01, "longitude": -74.01, "altitude": 10, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        time.sleep(8)
        status = executor.get_status()
        assert status["status"] == "completed"
        assert status["progress_pct"] == 100.0
        assert status["current_waypoint"] == 1


class TestMissionExecutorAbort:

    def test_abort_no_mission(self, executor):
        result = executor.abort()
        assert result["success"] is False

    def test_abort_during_flight(self, executor, missions_dir):
        # Short hops avoid blowing flight time without the old MAX_SEGMENT_DURATION cap.
        mid = _create_mission(missions_dir, "abort1", [
            {"latitude": 40.05, "longitude": -74.05, "altitude": 50, "action": "navigate", "duration": 0},
            {"latitude": 40.10, "longitude": -74.10, "altitude": 50, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        time.sleep(0.3)
        result = executor.abort()
        assert result["success"] is True
        time.sleep(1)
        status = executor.get_status()
        assert status["status"] == "aborted"


class TestMissionExecutorPathTraversal:
    """Sanitisation of client-supplied mission_id in _load_mission."""

    def test_load_mission_rejects_parent_dir(self, executor, missions_dir, tmp_path):
        # Create a sibling file the attacker would try to reach via traversal.
        sibling = tmp_path.parent / "secret.json"
        sibling.write_text(json.dumps({"waypoints": [{"latitude": 0, "longitude": 0, "altitude": 0}]}))
        # All four equivalent traversal payloads must resolve to None (not loaded).
        for payload in ["../secret", "..%2Fsecret", "..\\secret", "/etc/passwd"]:
            assert executor._load_mission(payload) is None

    def test_load_mission_rejects_empty_after_sanitise(self, executor):
        # Pure traversal characters collapse to empty string and must be rejected.
        assert executor._load_mission("../") is None
        assert executor._load_mission("..") is None
        assert executor._load_mission("") is None

    def test_load_mission_accepts_clean_id(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "clean_abc", [
            {"latitude": 1.0, "longitude": 2.0, "altitude": 10, "action": "navigate", "duration": 0},
        ])
        loaded = executor._load_mission(mid)
        assert loaded is not None
        assert loaded["id"] == "clean_abc"

    def test_start_returns_not_found_for_traversal(self, executor):
        # Public surface must not leak whether the file exists outside missions_dir.
        result = executor.start("../../etc/passwd")
        assert result["success"] is False
        assert "not found" in result["error"]


class TestMissionExecutorDroneInteraction:

    def test_move_to_called_for_each_waypoint(self, executor, missions_dir, mock_drone):
        # Sub-km hops keep total flight under sleep budget after MAX_SEGMENT_DURATION removal.
        mid = _create_mission(missions_dir, "move1", [
            {"latitude": 40.005, "longitude": -74.005, "altitude": 30, "action": "navigate", "duration": 0},
            {"latitude": 40.010, "longitude": -74.010, "altitude": 40, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        time.sleep(15)
        assert mock_drone.move_to.call_count == 2

    def test_position_interpolation(self, executor, missions_dir):
        mid = _create_mission(missions_dir, "interp1", [
            {"latitude": 40.05, "longitude": -74.05, "altitude": 50, "action": "navigate", "duration": 0},
        ])
        executor.start(mid)
        time.sleep(0.5)
        status = executor.get_status()
        pos = status["position"]
        assert pos["latitude"] != 40.0 or pos["longitude"] != -74.0


class TestMissionExecutorSpeedValidation:

    def test_speed_mps_zero_raises(self, mock_drone, missions_dir):
        with pytest.raises(ValueError):
            MissionExecutor(mock_drone, missions_dir, speed_mps=0)

    def test_speed_mps_negative_raises(self, mock_drone, missions_dir):
        with pytest.raises(ValueError):
            MissionExecutor(mock_drone, missions_dir, speed_mps=-5.0)

    def test_demo_mode_logs_warning(self, mock_drone, missions_dir, caplog):
        with caplog.at_level(logging.WARNING, logger="src.services.mission_executor"):
            MissionExecutor(mock_drone, missions_dir, demo_mode=True)
        assert any(
            "DEMO mode" in rec.message and "not realistic" in rec.message
            for rec in caplog.records
        )
