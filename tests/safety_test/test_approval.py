"""Token and capability tests: single use, expiry, hash binding, tampering, forgery, audit hygiene."""

import copy
import dataclasses
import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from evaluation.oracle import HOME
from src.safety.approval import (
    ApprovalError,
    ApprovedMission,
    AuditLog,
    MissionGate,
    canonical_json,
    flight_plan,
    mission_hash,
)


def approve(gate, mission, mid="m1", home=HOME):
    r = gate.review(mid, mission, home)
    assert r.ok, r.violations
    return gate.approve(mid, mission, home, r.mission_hash, "operator-key"), r.mission_hash


def test_happy_path_mints_capability(gate, safe_mission):
    token, h = approve(gate, safe_mission)
    am = gate.redeem(token, "m1", safe_mission, HOME)
    assert ApprovedMission.require(am) is am
    assert am.mission_hash == h and am.home == HOME and len(am.waypoints) == 3


def test_token_is_single_use(gate, safe_mission):
    token, _ = approve(gate, safe_mission)
    gate.redeem(token, "m1", safe_mission, HOME)
    with pytest.raises(ApprovalError) as e:
        gate.redeem(token, "m1", safe_mission, HOME)
    assert e.value.code == "invalid_token"


def test_token_expires(gate, safe_mission, clock):
    token, _ = approve(gate, safe_mission)
    clock.t += 301
    with pytest.raises(ApprovalError) as e:
        gate.redeem(token, "m1", safe_mission, HOME)
    assert e.value.code == "expired"


def test_token_valid_just_before_expiry(gate, safe_mission, clock):
    token, _ = approve(gate, safe_mission)
    clock.t += 299
    gate.redeem(token, "m1", safe_mission, HOME)


def test_approve_requires_exact_hash(gate, safe_mission):
    r = gate.review("m1", safe_mission, HOME)
    for bad in ("0" * 64, r.mission_hash[:-1] + ("0" if r.mission_hash[-1] != "0" else "1"), "", None):
        with pytest.raises(ApprovalError) as e:
            gate.approve("m1", safe_mission, HOME, bad, "op")
        assert e.value.code == "hash_mismatch"


def test_changed_mission_after_approval_is_refused_and_burns_token(gate, safe_mission):
    token, _ = approve(gate, safe_mission)
    tampered = copy.deepcopy(safe_mission)
    tampered["waypoints"][0]["latitude"] += 0.0001            # ~11 m, still inside the envelope
    with pytest.raises(ApprovalError) as e:
        gate.redeem(token, "m1", tampered, HOME)
    assert e.value.code == "hash_mismatch"
    with pytest.raises(ApprovalError):                           # token burned even on failure
        gate.redeem(token, "m1", safe_mission, HOME)


def test_approved_in_envelope_then_swapped_out_of_envelope_is_refused(gate, safe_mission):
    token, _ = approve(gate, safe_mission)
    evil = copy.deepcopy(safe_mission)
    evil["waypoints"][0]["altitude"] = 400
    with pytest.raises(ApprovalError) as e:
        gate.redeem(token, "m1", evil, HOME)
    assert e.value.code == "envelope_violation"


def test_token_bound_to_mission_id(gate, safe_mission):
    token, _ = approve(gate, safe_mission, mid="m1")
    with pytest.raises(ApprovalError) as e:
        gate.redeem(token, "other", safe_mission, HOME)
    assert e.value.code == "wrong_mission"


def test_cannot_approve_out_of_envelope_mission(gate, safe_mission):
    safe_mission["waypoints"][0]["altitude"] = 300
    r = gate.review("m1", safe_mission, HOME)
    assert not r.ok and r.mission_hash is None
    with pytest.raises(ApprovalError) as e:
        gate.approve("m1", safe_mission, HOME, "0" * 64, "op")
    assert e.value.code == "envelope_violation"


def test_position_must_match_approved_home(gate, safe_mission):
    token, _ = approve(gate, safe_mission)
    elsewhere = (HOME[0] + 0.001, HOME[1])                       # ~111 m away
    with pytest.raises(ApprovalError) as e:
        gate.redeem(token, "m1", safe_mission, elsewhere)
    assert e.value.code == "position_mismatch"


def test_envelope_change_invalidates_approval(safe_mission, clock, envelope):
    g1 = MissionGate(envelope, clock=clock)
    token, _ = approve(g1, safe_mission)
    g1.envelope = envelope.model_copy(update={"max_altitude_m": 55.0})   # tighter limits after approval
    with pytest.raises(ApprovalError):
        g1.redeem(token, "m1", safe_mission, HOME)


@pytest.mark.parametrize("tok", [None, "", 123, "forged", b"x"])
def test_forged_or_missing_token(gate, safe_mission, tok):
    with pytest.raises(ApprovalError):
        gate.redeem(tok, "m1", safe_mission, HOME)


def test_cannot_construct_approved_mission_directly():
    with pytest.raises(ApprovalError):
        ApprovedMission("m1", "{}", "x", "y")


def test_tampered_capability_is_rejected(gate, safe_mission):
    token, _ = approve(gate, safe_mission)
    am = gate.redeem(token, "m1", safe_mission, HOME)
    forged_plan = am.plan_json.replace('"altitude":50.0', '"altitude":500.0')
    assert forged_plan != am.plan_json
    forged = dataclasses.replace(am, plan_json=forged_plan)
    with pytest.raises(ApprovalError):
        ApprovedMission.require(forged)
    with pytest.raises(ApprovalError):
        ApprovedMission.require({"waypoints": []})


def test_audit_never_records_key_or_full_token(gate, safe_mission, tmp_path):
    path = tmp_path / "audit.jsonl"
    gate.audit = AuditLog(str(path))
    token, _ = approve(gate, safe_mission)
    gate.redeem(token, "m1", safe_mission, HOME)
    with pytest.raises(ApprovalError):
        gate.redeem(token, "m1", safe_mission, HOME)
    text = path.read_text()
    assert token not in text and "operator-key" not in text
    events = [json.loads(l)["event"] for l in text.splitlines()]
    assert events == ["reviewed", "reviewed", "approved", "redeemed", "redeem_refused"]


# ---- canonical hash properties ----

def test_hash_is_order_and_int_float_invariant(envelope, safe_mission):
    fp = envelope.fingerprint()
    a = flight_plan(safe_mission, envelope)
    b = copy.deepcopy(safe_mission)
    b["waypoints"][0] = dict(reversed(list(b["waypoints"][0].items())))
    b["waypoints"][0]["altitude"] = 50.0                         # int 50 -> float 50.0
    assert mission_hash(a, HOME, fp) == mission_hash(flight_plan(b, envelope), HOME, fp)


def test_hash_ignores_non_flight_metadata(envelope, safe_mission):
    fp = envelope.fingerprint()
    a = mission_hash(flight_plan(safe_mission, envelope), HOME, fp)
    safe_mission["mission_name"] = "renamed"; safe_mission["safety_warnings"] = ["x"]
    assert a == mission_hash(flight_plan(safe_mission, envelope), HOME, fp)


@settings(max_examples=200, deadline=None)
@given(idx=st.integers(0, 2), field=st.sampled_from(["latitude", "longitude", "altitude", "duration"]),
       delta=st.floats(1e-5, 1e-2))
def test_any_flight_relevant_change_changes_hash(idx, field, delta):
    from src.safety.envelope import SafetyEnvelope
    from tests.safety_test.conftest import SAFE_MISSION
    envelope = SafetyEnvelope()
    m = copy.deepcopy(SAFE_MISSION)
    fp = envelope.fingerprint()
    base = mission_hash(flight_plan(m, envelope), HOME, fp)
    m["waypoints"][idx][field] += delta
    assert mission_hash(flight_plan(m, envelope), HOME, fp) != base


def test_canonical_json_rejects_nan(envelope):
    with pytest.raises(ValueError):
        canonical_json({"waypoints": [{"altitude": float("nan")}]}, HOME, "fp")
