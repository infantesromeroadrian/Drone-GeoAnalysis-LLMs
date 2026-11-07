import copy

import pytest

from evaluation.oracle import HOME
from evaluation.pipeline import scenario_envelope
from src.safety.approval import MissionGate
from src.safety.envelope import SafetyEnvelope

SAFE_MISSION = {
    "mission_name": "ok",
    "waypoints": [
        {"latitude": 35.6650, "longitude": 139.7640, "altitude": 50, "action": "navigate", "duration": 5},
        {"latitude": 35.6630, "longitude": 139.7650, "altitude": 60, "action": "hover", "duration": 10},
        {"latitude": 35.6640, "longitude": 139.7630, "altitude": 0, "action": "land", "duration": 0},
    ],
}


@pytest.fixture
def safe_mission():
    return copy.deepcopy(SAFE_MISSION)


@pytest.fixture
def envelope() -> SafetyEnvelope:
    """Tokyo scenario envelope: same parameters as the independent oracle in evaluation/oracle.py."""
    return scenario_envelope()


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def gate(envelope, clock) -> MissionGate:
    return MissionGate(envelope, ttl_s=300.0, clock=clock)


@pytest.fixture
def home():
    return HOME
