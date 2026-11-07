"""Strict pydantic schemas for outputs that originate from (or may be influenced by) an LLM."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AmendedWaypoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude: float
    action: str = "navigate"
    duration: float = Field(default=0.0, ge=0)
    description: str = Field(default="", max_length=500)


class MissionAmendment(BaseModel):
    """In-flight change proposal. Only ``replace_waypoints`` carries coordinates, and it is never
    applied directly: it becomes a new mission that must pass the envelope and be approved again."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    action: Literal["continue", "hold", "abort", "return_to_base", "replace_waypoints"]
    reason: str = Field(default="", max_length=500)
    waypoints: list[AmendedWaypoint] | None = Field(default=None, max_length=50)

    def waypoints_as_dicts(self) -> list[dict[str, Any]]:
        return [w.model_dump() for w in (self.waypoints or [])]

    def model_post_init(self, _ctx: Any) -> None:
        if (self.action == "replace_waypoints") != bool(self.waypoints):
            raise ValueError("waypoints are required for, and only allowed with, replace_waypoints")
