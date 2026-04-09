"""
LangGraph ReAct agent for intelligent mission planning.

Replaces the linear prompt-response pipeline with an agent that can:
- Load and reason about cartography data
- Validate missions during planning (not just after)
- Retry on malformed JSON with feedback
- Decompose complex commands into sub-tasks
- Calculate distances to verify waypoint spacing
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Annotated, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import ValidationError
from typing_extensions import TypedDict

from src.models.cartography_manager import CartographyManager
from src.models.mission_data_processor import MissionDataProcessor
from src.models.mission_schemas import MissionSchema
from src.models.mission_utils import (
    calculate_distance,
    calculate_total_mission_distance,
    generate_grid_waypoints,
)
from src.models.mission_validator import validate_mission_safety, validate_mission_duration
from src.models.prompt_generator import PromptGenerator
from src.utils.config import get_groq_config

logger = logging.getLogger(__name__)

# Module-level references set by MissionPlannerAgent.__init__
_cartography_manager: Optional[CartographyManager] = None
_data_processor: Optional[MissionDataProcessor] = None
_prompt_generator: Optional[PromptGenerator] = None


class MissionPlannerState(TypedDict):
    messages: Annotated[list, add_messages]
    natural_command: str
    area_name: Optional[str]
    mission_result: Optional[dict]
    retry_count: int


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def load_area_info(area_name: str) -> str:
    """Load geographic area information including boundaries, POIs, and center coordinates.
    Use this before planning waypoints to know what is in the area."""
    if not _cartography_manager:
        return "CartographyManager not available"

    area = _cartography_manager.get_loaded_area(area_name)
    if not area:
        available = list(_cartography_manager.get_loaded_areas().keys())
        return f"Area '{area_name}' not loaded. Available areas: {available}"

    center = None
    if _data_processor:
        center = _data_processor.get_area_center_coordinates(area)

    info = {
        "name": area.name,
        "boundaries": area.boundaries[:10],
        "points_of_interest": area.points_of_interest,
        "center": {"latitude": center[0], "longitude": center[1]} if center else None,
    }
    return json.dumps(info, indent=2)


@tool
def validate_mission(mission_json: str) -> str:
    """Validate a mission for safety: altitude limits (120m), distance between waypoints
    (10km max), GPS coordinate validity, and duration coherence.
    Pass the mission as a JSON string. Returns warnings or 'VALID'."""
    try:
        mission = json.loads(mission_json) if isinstance(mission_json, str) else mission_json
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    warnings = validate_mission_safety(mission)
    warnings.extend(validate_mission_duration(mission))

    if not warnings:
        return "VALID - No safety issues found"
    return "WARNINGS:\n" + "\n".join(f"- {w}" for w in warnings)


@tool
def generate_area_grid_waypoints(area_name: str, grid_spacing_meters: float = 100.0,
                                  altitude: float = 50.0) -> str:
    """Generate a grid scan pattern of waypoints within a loaded area.
    Useful for 'scan the entire area' or 'patrol' commands."""
    if not _cartography_manager:
        return "CartographyManager not available"

    area = _cartography_manager.get_loaded_area(area_name)
    if not area:
        return f"Area '{area_name}' not loaded"

    waypoints = generate_grid_waypoints(area, grid_spacing_meters, altitude)
    return json.dumps(waypoints, indent=2)


@tool
def calculate_waypoint_distances(waypoints_json: str) -> str:
    """Calculate total mission distance and distances between consecutive waypoints.
    Pass waypoints as a JSON string (list of objects with latitude/longitude)."""
    try:
        waypoints = json.loads(waypoints_json) if isinstance(waypoints_json, str) else waypoints_json
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    if len(waypoints) < 2:
        return "Need at least 2 waypoints to calculate distances"

    total = calculate_total_mission_distance(waypoints)
    segments = []
    for i in range(1, len(waypoints)):
        prev, curr = waypoints[i - 1], waypoints[i]
        d = calculate_distance(
            (prev["latitude"], prev["longitude"]),
            (curr["latitude"], curr["longitude"]),
        )
        segments.append(f"WP{i} -> WP{i+1}: {d:.0f}m")

    return f"Total distance: {total:.0f}m\nSegments:\n" + "\n".join(segments)


@tool
def finalize_mission(mission_json: str, natural_command: str,
                     area_name: str = "") -> str:
    """Validate, deduplicate waypoints, add metadata, and save the mission.
    Pass the COMPLETE mission as a JSON string with keys: mission_name, description,
    estimated_duration, waypoints (list with latitude/longitude/altitude/action/duration/description),
    safety_considerations, success_criteria, area_used.
    Returns the saved mission or an error for you to fix and retry."""
    try:
        mission_dict = json.loads(mission_json) if isinstance(mission_json, str) else mission_json
    except json.JSONDecodeError as e:
        return f"JSON_ERROR: {e}. Fix the JSON and call finalize_mission again."

    try:
        validated = MissionSchema(**mission_dict)
        mission_dict = validated.model_dump()
    except ValidationError as e:
        errors = "; ".join(err["msg"] for err in e.errors())
        return f"VALIDATION_ERROR: {errors}. Fix the mission and call finalize_mission again."

    if _data_processor:
        mission_dict["waypoints"] = _data_processor._deduplicate_waypoints(
            mission_dict["waypoints"]
        )

    mission_dict["id"] = str(uuid.uuid4())
    mission_dict["created_at"] = datetime.now().isoformat()
    mission_dict["status"] = "planned"
    mission_dict["area_name"] = area_name or None
    mission_dict["original_command"] = natural_command
    mission_dict["llm_provider"] = "groq"
    mission_dict["llm_model"] = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if _data_processor:
        _data_processor.save_mission(mission_dict)

    return json.dumps({"status": "SUCCESS", "mission_id": mission_dict["id"],
                        "waypoints_count": len(mission_dict["waypoints"])})


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

ALL_TOOLS = [load_area_info, validate_mission, generate_area_grid_waypoints,
             calculate_waypoint_distances, finalize_mission]


def _should_continue(state: MissionPlannerState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_mission_agent_graph(llm: ChatGroq) -> StateGraph:
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def plan_node(state: MissionPlannerState) -> dict:
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(MissionPlannerState)
    graph.add_node("plan", plan_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.set_entry_point("plan")
    graph.add_conditional_edges("plan", _should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "plan")

    return graph


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class MissionPlannerAgent:
    """LangGraph ReAct agent for mission planning."""

    MAX_ITERATIONS = 10

    def __init__(self, cartography_manager: CartographyManager,
                 data_processor: MissionDataProcessor,
                 prompt_generator: PromptGenerator):
        global _cartography_manager, _data_processor, _prompt_generator
        _cartography_manager = cartography_manager
        _data_processor = data_processor
        _prompt_generator = prompt_generator

        config = get_groq_config()
        self.llm = ChatGroq(
            model=config["model"],
            api_key=config["api_key"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
        )
        self.graph = build_mission_agent_graph(self.llm).compile()
        logger.info("MissionPlannerAgent initialized with LangGraph ReAct")

    def plan_mission(self, natural_command: str,
                     area_name: Optional[str] = None) -> dict:
        system_prompt = _prompt_generator.build_agent_system_prompt()
        user_msg = self._build_user_message(natural_command, area_name)

        initial_state: MissionPlannerState = {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_msg),
            ],
            "natural_command": natural_command,
            "area_name": area_name,
            "mission_result": None,
            "retry_count": 0,
        }

        result = self.graph.invoke(
            initial_state,
            config={"recursion_limit": self.MAX_ITERATIONS},
        )

        return self._extract_mission_from_result(result)

    def _build_user_message(self, command: str, area_name: Optional[str]) -> str:
        parts = [f"COMMAND: {command}"]
        if area_name:
            parts.append(f"AREA: {area_name}")
            parts.append("First call load_area_info to get the area details, "
                        "then plan the mission using those coordinates.")
        else:
            parts.append("No specific area loaded. Use appropriate coordinates.")
        return "\n".join(parts)

    def _extract_mission_from_result(self, result: dict) -> dict:
        for msg in reversed(result.get("messages", [])):
            if hasattr(msg, "content") and isinstance(msg.content, str):
                if "SUCCESS" in msg.content and "mission_id" in msg.content:
                    try:
                        data = json.loads(msg.content)
                        if data.get("status") == "SUCCESS":
                            mission_id = data["mission_id"]
                            return self._load_saved_mission(mission_id)
                    except (json.JSONDecodeError, KeyError):
                        continue

        raise RuntimeError("Agent did not produce a finalized mission")

    def _load_saved_mission(self, mission_id: str) -> dict:
        if not _data_processor:
            raise RuntimeError("MissionDataProcessor not available")
        missions_dir = _data_processor.missions_dir
        path = os.path.join(missions_dir, f"mission_{mission_id}.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
