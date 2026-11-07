"""Unit and property tests for the deterministic envelope (hypothesis)."""

import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from evaluation.oracle import HOME
from evaluation.oracle import violations as oracle_violations
from src.safety.envelope import SafetyEnvelope, evaluate
from src.safety.geometry import (
    point_in_polygon,
    segment_intersects_polygon,
    segment_point_distance,
    segments_properly_cross,
)


def codes(m, env, home=HOME):
    return evaluate(m, env, home).codes()


def test_safe_mission_accepted(safe_mission, envelope):
    assert evaluate(safe_mission, envelope, HOME).ok


@pytest.mark.parametrize("mutate,code", [
    (lambda m: m["waypoints"][0].update(altitude=121), "altitude"),
    (lambda m: m["waypoints"][0].update(altitude=-1), "altitude"),
    (lambda m: m["waypoints"][0].update(altitude=1), "altitude"),
    (lambda m: m["waypoints"][0].update(latitude=35.70), "geofence"),
    (lambda m: m["waypoints"][0].update(action="release_payload"), "action"),
    (lambda m: m.update(speed_mps=16), "speed"),
    (lambda m: m["waypoints"][0].update(altitude=float("nan")), "malformed"),
    (lambda m: m["waypoints"][0].update(latitude=float("inf")), "malformed"),
    (lambda m: m["waypoints"][0].update(altitude="50"), "malformed"),
    (lambda m: m["waypoints"][0].update(altitude=True), "malformed"),
    (lambda m: m["waypoints"][0].update(extra_key=1), "malformed"),
    (lambda m: m["waypoints"][0].update(actions=[{"type": "drop_payload"}]), "action"),
    (lambda m: m.update(waypoints=[]), "malformed"),
    (lambda m: m["waypoints"][0].update(duration=5000), "battery"),
])
def test_violations_detected(safe_mission, envelope, mutate, code):
    mutate(safe_mission)
    assert code in codes(safe_mission, envelope)


def test_land_waypoint_may_be_on_the_ground_but_navigate_may_not(safe_mission, envelope):
    assert evaluate(safe_mission, envelope, HOME).ok          # land at altitude 0
    safe_mission["waypoints"][0]["altitude"] = 0
    assert "altitude" in codes(safe_mission, envelope)


def test_exclusion_zone_segment_crossing_detected_without_vertex_inside(envelope):
    # both endpoints outside the 120 m zone 300 m north of home, the leg passes through its centre
    m = {"waypoints": [
        {"latitude": 35.6640, "longitude": 139.7634, "altitude": 50},
        {"latitude": 35.6700, "longitude": 139.7634, "altitude": 50}]}
    assert "exclusion_zone" in codes(m, envelope)


def test_polygon_exclusion_and_geofence(safe_mission):
    from src.safety.envelope import ExclusionZone
    sq = ((35.6655, 139.7625), (35.6655, 139.7645), (35.6675, 139.7645), (35.6675, 139.7625))
    env = SafetyEnvelope(exclusion_zones=(ExclusionZone(name="sq", vertices=sq),))
    m = {"waypoints": [{"latitude": 35.6640, "longitude": 139.7635, "altitude": 50},
                       {"latitude": 35.6690, "longitude": 139.7635, "altitude": 50}]}
    assert "exclusion_zone" in codes(m, env)     # leg crosses the polygon, vertices outside
    geo = SafetyEnvelope(geofence_polygon=((35.660, 139.760), (35.660, 139.768), (35.668, 139.768), (35.668, 139.760)))
    assert evaluate(safe_mission, geo, HOME).ok
    safe_mission["waypoints"][0]["latitude"] = 35.669
    assert "geofence" in codes(safe_mission, geo)


def test_envelope_fingerprint_changes_with_any_limit():
    assert SafetyEnvelope().fingerprint() != SafetyEnvelope(max_altitude_m=100).fingerprint()
    assert SafetyEnvelope().fingerprint() == SafetyEnvelope().fingerprint()


def test_rejects_non_mapping_and_bad_home(envelope):
    assert not evaluate("x", envelope, HOME).ok
    assert not evaluate({"waypoints": [{"latitude": 0, "longitude": 0, "altitude": 10}]}, envelope, (float("nan"), 0)).ok


# ---------------- property tests ----------------

wp_st = st.fixed_dictionaries({
    "latitude": st.floats(HOME[0] - 0.03, HOME[0] + 0.03),
    "longitude": st.floats(HOME[1] - 0.03, HOME[1] + 0.03),
    "altitude": st.floats(-10, 200),
    "action": st.sampled_from(["navigate", "hover", "scan", "photograph", "patrol", "land", "takeoff", "exec"]),
    "duration": st.floats(0, 900),
})
mission_st = st.fixed_dictionaries({
    "waypoints": st.lists(wp_st, min_size=1, max_size=8),
    "speed_mps": st.floats(1, 25),
})


@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(mission_st)
def test_envelope_agrees_with_independent_oracle(mission):
    """evaluate() accepts exactly the missions the independent oracle accepts (same parameters)."""
    from evaluation.pipeline import scenario_envelope
    env = scenario_envelope()
    got = evaluate(mission, env, HOME)
    want = oracle_violations(mission)
    # Two correct implementations of the same predicate may differ by float rounding exactly at a
    # limit; only those boundary cases are excused.
    if got.ok != (not want):
        assert _near_boundary(mission), (got.codes(), want)


def _near_boundary(m) -> bool:
    from evaluation.oracle import LIMITS, _seg_circle_min_dist, haversine
    z = LIMITS["exclusion_zones"][0]
    pts = [HOME] + [(w["latitude"], w["longitude"]) for w in m["waypoints"]]
    for w in m["waypoints"]:
        if min(abs(w["altitude"] - LIMITS["max_altitude_m"]), abs(w["altitude"] - LIMITS["min_altitude_m"])) < 0.01:
            return True
        if abs(haversine(HOME, (w["latitude"], w["longitude"])) - LIMITS["max_distance_from_home_m"]) < 1.0:
            return True
    for a, b in zip(pts, pts[1:]):
        if abs(haversine(a, b) - LIMITS["max_segment_m"]) < 1.0:
            return True
        # projection model difference (equirectangular vs haversine) is bounded to ~0.1 % at these ranges
        if abs(_seg_circle_min_dist(a, b, (z["lat"], z["lon"])) - z["radius_m"]) < 1.0:
            return True
    for w in m["waypoints"]:
        if abs(haversine((z["lat"], z["lon"]), (w["latitude"], w["longitude"])) - z["radius_m"]) < 1.0:
            return True
    ring = pts[1:] + [HOME]
    path = sum(haversine(a, b) for a, b in zip(pts, ring))
    t = path / min(m["speed_mps"], LIMITS["max_speed_mps"]) + sum(w["duration"] for w in m["waypoints"])
    return abs(t - LIMITS["battery_endurance_s"] * (1 - LIMITS["battery_reserve_fraction"])) < 1.0


@settings(max_examples=300, deadline=None)
@given(mission_st, st.floats(10, 120))
def test_lowering_max_altitude_never_accepts_more(mission, lower):
    base = SafetyEnvelope()
    tight = SafetyEnvelope(max_altitude_m=lower)
    if evaluate(mission, tight, HOME).ok:
        assert evaluate(mission, base, HOME).ok


json_leaf = st.none() | st.booleans() | st.integers() | st.floats(allow_nan=True, allow_infinity=True) | st.text(max_size=20)
json_st = st.recursive(json_leaf, lambda c: st.lists(c, max_size=5) | st.dictionaries(st.text(max_size=8), c, max_size=5), max_leaves=30)


@settings(max_examples=500, deadline=None)
@given(json_st)
def test_evaluate_never_raises_and_rejects_arbitrary_junk(junk):
    v = evaluate(junk, SafetyEnvelope(), HOME)
    assert not v.ok


@settings(max_examples=300, deadline=None)
@given(st.fixed_dictionaries({"waypoints": st.lists(st.dictionaries(st.sampled_from(
    ["latitude", "longitude", "altitude", "action", "duration", "x"]), json_leaf, max_size=6), max_size=4)}))
def test_evaluate_total_on_structured_junk(m):
    evaluate(m, SafetyEnvelope(), HOME)   # must not raise


# ---------------- geometry ----------------

def test_geometry_primitives():
    sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert point_in_polygon((5, 5), sq) and not point_in_polygon((11, 5), sq) and point_in_polygon((0, 5), sq)
    assert segment_intersects_polygon((-5, 5), (15, 5), sq)
    assert not segment_intersects_polygon((-5, 11), (15, 11), sq)
    assert segments_properly_cross((0, 0), (2, 2), (0, 2), (2, 0))
    assert not segments_properly_cross((0, 0), (1, 0), (1, 0), (2, 0))
    assert math.isclose(segment_point_distance((0, 0), (10, 0), (5, 3)), 3.0)
    assert math.isclose(segment_point_distance((0, 0), (10, 0), (15, 0)), 5.0)


def test_defaults_are_conservative_and_scenario_is_explicit():
    d = SafetyEnvelope()
    assert d.max_distance_from_home_m == 500 and d.max_segment_m == 1000 and d.max_altitude_m == 120
    from evaluation.oracle import LIMITS
    from evaluation.pipeline import scenario_envelope
    s = scenario_envelope()
    assert s.max_distance_from_home_m == LIMITS["max_distance_from_home_m"] == 2000
    assert s.max_segment_m == LIMITS["max_segment_m"]
    assert s.max_altitude_m == LIMITS["max_altitude_m"] and s.max_speed_mps == LIMITS["max_speed_mps"]
    assert s.endurance_s == LIMITS["battery_endurance_s"]
    z = s.exclusion_zones[0]
    assert z.center == (LIMITS["exclusion_zones"][0]["lat"], LIMITS["exclusion_zones"][0]["lon"])
    assert z.radius_m == LIMITS["exclusion_zones"][0]["radius_m"]


def test_mission_1600_m_from_home_rejected_by_defaults_accepted_by_tokyo_scenario():
    from evaluation.pipeline import scenario_envelope
    m = {"waypoints": [{"latitude": HOME[0] + 0.0144, "longitude": HOME[1], "altitude": 50}]}  # ~1.6 km north
    # keep clear of the scenario exclusion zone (300 m north, r=120) by going east-north-east instead
    m["waypoints"][0].update(latitude=HOME[0] + 0.0040, longitude=HOME[1] + 0.0160)
    from src.safety.geometry import haversine_m
    d = haversine_m(HOME, (m["waypoints"][0]["latitude"], m["waypoints"][0]["longitude"]))
    assert 1500 < d < 1750
    assert "geofence" in evaluate(m, SafetyEnvelope(), HOME).codes()
    assert evaluate(m, scenario_envelope(), HOME).ok
