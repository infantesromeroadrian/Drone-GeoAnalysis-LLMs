"""Tests for mission_schemas.py -- Pydantic validation."""

import pytest
from pydantic import ValidationError
from src.models.mission_schemas import WaypointSchema, MissionSchema


class TestWaypointSchema:

    def test_valid_waypoint(self):
        wp = WaypointSchema(latitude=35.6612, longitude=139.7664, altitude=40.0)
        assert wp.latitude == 35.6612
        assert wp.action == "navigate"
        assert wp.duration == 0.0

    def test_all_fields(self):
        wp = WaypointSchema(
            latitude=40.7128, longitude=-74.006, altitude=50.0,
            action="scan", duration=10.0, description="Survey point"
        )
        assert wp.action == "scan"
        assert wp.description == "Survey point"

    def test_latitude_out_of_range(self):
        with pytest.raises(ValidationError, match="Latitude"):
            WaypointSchema(latitude=91.0, longitude=0.0, altitude=10.0)

    def test_latitude_negative_out_of_range(self):
        with pytest.raises(ValidationError, match="Latitude"):
            WaypointSchema(latitude=-91.0, longitude=0.0, altitude=10.0)

    def test_longitude_out_of_range(self):
        with pytest.raises(ValidationError, match="Longitude"):
            WaypointSchema(latitude=0.0, longitude=181.0, altitude=10.0)

    def test_altitude_exceeds_legal_limit(self):
        with pytest.raises(ValidationError, match="Altitude"):
            WaypointSchema(latitude=0.0, longitude=0.0, altitude=121.0)

    def test_altitude_negative(self):
        with pytest.raises(ValidationError, match="Altitude"):
            WaypointSchema(latitude=0.0, longitude=0.0, altitude=-1.0)

    def test_altitude_zero_valid(self):
        wp = WaypointSchema(latitude=0.0, longitude=0.0, altitude=0.0)
        assert wp.altitude == 0.0

    def test_altitude_max_valid(self):
        wp = WaypointSchema(latitude=0.0, longitude=0.0, altitude=120.0)
        assert wp.altitude == 120.0

    def test_invalid_action(self):
        with pytest.raises(ValidationError, match="Action"):
            WaypointSchema(latitude=0.0, longitude=0.0, altitude=10.0, action="explode")

    def test_all_valid_actions(self):
        for action in ["navigate", "hover", "scan", "photograph", "patrol", "land", "takeoff"]:
            wp = WaypointSchema(latitude=0.0, longitude=0.0, altitude=10.0, action=action)
            assert wp.action == action


class TestMissionSchema:

    def _make_waypoint(self, **kwargs):
        defaults = {"latitude": 35.6612, "longitude": 139.7664, "altitude": 40.0}
        defaults.update(kwargs)
        return defaults

    def test_valid_mission(self):
        m = MissionSchema(
            mission_name="Test",
            description="A test mission",
            estimated_duration=15.0,
            waypoints=[self._make_waypoint()],
        )
        assert m.mission_name == "Test"
        assert len(m.waypoints) == 1
        assert m.safety_considerations == []

    def test_multiple_waypoints(self):
        m = MissionSchema(
            mission_name="Multi",
            description="Multi waypoint",
            estimated_duration=30.0,
            waypoints=[
                self._make_waypoint(latitude=35.66),
                self._make_waypoint(latitude=35.67),
                self._make_waypoint(latitude=35.68),
            ],
        )
        assert len(m.waypoints) == 3

    def test_empty_waypoints_rejected(self):
        with pytest.raises(ValidationError, match="at least one waypoint"):
            MissionSchema(
                mission_name="Empty",
                description="No waypoints",
                estimated_duration=10.0,
                waypoints=[],
            )

    def test_invalid_waypoint_in_mission_rejected(self):
        with pytest.raises(ValidationError):
            MissionSchema(
                mission_name="Bad",
                description="Invalid wp",
                estimated_duration=10.0,
                waypoints=[{"latitude": 999, "longitude": 0, "altitude": 10}],
            )

    def test_optional_fields(self):
        m = MissionSchema(
            mission_name="Opts",
            description="Optional fields",
            estimated_duration=5.0,
            waypoints=[self._make_waypoint()],
            safety_considerations=["Check wind"],
            success_criteria=["Complete all WPs"],
            area_used="Tokyo Bay",
        )
        assert m.area_used == "Tokyo Bay"
        assert len(m.safety_considerations) == 1

    def test_model_dump_roundtrip(self):
        data = {
            "mission_name": "Roundtrip",
            "description": "Test dump",
            "estimated_duration": 20.0,
            "waypoints": [self._make_waypoint()],
        }
        m = MissionSchema(**data)
        dumped = m.model_dump()
        assert dumped["mission_name"] == "Roundtrip"
        assert isinstance(dumped["waypoints"][0], dict)
