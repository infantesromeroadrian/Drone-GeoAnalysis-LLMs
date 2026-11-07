"""Shared helpers for tests that need to run missions through the approval gate."""

from src.safety.approval import ApprovalError, MissionGate
from src.safety.envelope import SafetyEnvelope


def permissive_envelope(**overrides) -> SafetyEnvelope:
    """Wide geofence/segment/endurance so legacy fixtures (tens of km apart) stay in envelope."""
    params = dict(max_distance_from_home_m=100_000.0, max_segment_m=100_000.0, endurance_s=10 * 3600.0)
    params.update(overrides)
    return SafetyEnvelope(**params)


def start_approved(executor, mission_id: str, gate: MissionGate | None = None) -> dict:
    """Operator flow in one call: review -> approve (exact hash) -> start with the token."""
    gate = gate or executor._gate
    mission = executor.load_mission(mission_id)
    pos = executor._drone.current_position
    home = (pos["latitude"], pos["longitude"])
    review = gate.review(mission_id, mission, home)
    if not review.ok:
        return {"success": False, "error": "Approval refused: envelope_violation"}
    try:
        token = gate.approve(mission_id, mission, home, review.mission_hash, "test-operator")
    except ApprovalError as e:
        return {"success": False, "error": f"Approval refused: {e.code}"}
    return executor.start(mission_id, token)
