"""Pydantic schemas for mission validation and structured output."""

from typing import Optional
from pydantic import BaseModel, field_validator


class WaypointSchema(BaseModel):
    latitude: float
    longitude: float
    altitude: float
    action: str = "navigate"
    duration: float = 0.0
    description: str = ""

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {v}")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {v}")
        return v

    @field_validator("altitude")
    @classmethod
    def validate_altitude(cls, v: float) -> float:
        if v < 0 or v > 120:
            raise ValueError(f"Altitude must be between 0 and 120m, got {v}")
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid = {"navigate", "hover", "scan", "photograph", "patrol", "land", "takeoff"}
        if v not in valid:
            raise ValueError(f"Action must be one of {valid}, got '{v}'")
        return v


class MissionSchema(BaseModel):
    mission_name: str
    description: str
    estimated_duration: float
    waypoints: list[WaypointSchema]
    safety_considerations: list[str] = []
    success_criteria: list[str] = []
    area_used: Optional[str] = None

    @field_validator("waypoints")
    @classmethod
    def validate_waypoints_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("Mission must have at least one waypoint")
        return v
