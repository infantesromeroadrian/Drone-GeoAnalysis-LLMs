"""Tests for mission_agent.py -- LangGraph ReAct agent tools and graph."""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

try:
    from src.models.mission_agent import (
        _DepsRegistry,
        load_area_info,
        validate_mission,
        calculate_waypoint_distances,
        finalize_mission,
        build_mission_agent_graph,
        MissionPlannerState,
    )
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False

from src.models.mission_models import MissionArea

pytestmark = pytest.mark.skipif(not AGENT_AVAILABLE, reason="LangGraph/langchain-groq not installed")


@pytest.fixture(autouse=True)
def setup_deps(tmp_path):
    """Set up mock dependencies for all tools."""
    cm = MagicMock()
    dp = MagicMock()
    dp.missions_dir = str(tmp_path)
    dp._deduplicate_waypoints = lambda wps: wps
    pg = MagicMock()
    _DepsRegistry.set(cm, dp, pg)
    yield cm, dp, pg


class TestLoadAreaInfoTool:

    def test_area_not_loaded(self, setup_deps):
        cm, _, _ = setup_deps
        cm.get_loaded_area.return_value = None
        cm.get_loaded_areas.return_value = {}
        result = load_area_info.invoke({"area_name": "unknown"})
        assert "not loaded" in result

    def test_area_loaded(self, setup_deps):
        cm, dp, _ = setup_deps
        area = MissionArea(name="Tokyo", boundaries=[(35.6, 139.7)],
                          points_of_interest=[{"name": "Tower", "coordinates": (35.66, 139.76), "type": "poi"}])
        cm.get_loaded_area.return_value = area
        dp.get_area_center_coordinates.return_value = (35.66, 139.76)
        result = load_area_info.invoke({"area_name": "Tokyo"})
        data = json.loads(result)
        assert data["name"] == "Tokyo"
        assert data["center"]["latitude"] == 35.66


class TestValidateMissionTool:

    def test_valid_mission(self):
        mission = {
            "waypoints": [
                {"latitude": 35.66, "longitude": 139.76, "altitude": 40, "duration": 300},
                {"latitude": 35.67, "longitude": 139.77, "altitude": 40, "duration": 300},
            ],
            "estimated_duration": 10,
        }
        result = validate_mission.invoke({"mission_json": json.dumps(mission)})
        assert "VALID" in result

    def test_altitude_violation(self):
        mission = {
            "waypoints": [{"latitude": 35.66, "longitude": 139.76, "altitude": 200}],
        }
        result = validate_mission.invoke({"mission_json": json.dumps(mission)})
        assert "WARNINGS" in result
        assert "120m" in result

    def test_invalid_json(self):
        result = validate_mission.invoke({"mission_json": "not json{{"})
        assert "Invalid JSON" in result


class TestCalculateDistancesTool:

    def test_two_waypoints(self):
        wps = [
            {"latitude": 35.66, "longitude": 139.76},
            {"latitude": 35.67, "longitude": 139.77},
        ]
        result = calculate_waypoint_distances.invoke({"waypoints_json": json.dumps(wps)})
        assert "Total distance" in result
        assert "WP1 -> WP2" in result

    def test_single_waypoint(self):
        result = calculate_waypoint_distances.invoke({"waypoints_json": json.dumps([{"latitude": 0, "longitude": 0}])})
        assert "at least 2" in result


class TestFinalizeMissionTool:

    def test_valid_finalize(self, setup_deps):
        _, dp, _ = setup_deps
        mission = {
            "mission_name": "Test",
            "description": "A test",
            "estimated_duration": 10,
            "waypoints": [{"latitude": 35.66, "longitude": 139.76, "altitude": 40,
                          "action": "navigate", "duration": 0, "description": "WP1"}],
            "safety_considerations": [],
            "success_criteria": [],
        }
        result = finalize_mission.invoke({
            "mission_json": json.dumps(mission),
            "natural_command": "test cmd",
            "area_name": "tokyo",
        })
        data = json.loads(result)
        assert data["status"] == "SUCCESS"
        assert dp.save_mission.called

    def test_invalid_schema_returns_error(self):
        mission = {"mission_name": "Bad", "description": "x", "estimated_duration": 1, "waypoints": []}
        result = finalize_mission.invoke({
            "mission_json": json.dumps(mission),
            "natural_command": "test",
        })
        assert "VALIDATION_ERROR" in result

    def test_bad_json_returns_error(self):
        result = finalize_mission.invoke({
            "mission_json": "broken{{",
            "natural_command": "test",
        })
        assert "JSON_ERROR" in result


class TestGraphConstruction:

    def test_graph_compiles(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        graph = build_mission_agent_graph(mock_llm)
        compiled = graph.compile()
        assert compiled is not None
