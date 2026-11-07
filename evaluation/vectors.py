"""Seeded generators of missions emitted by a *compromised* planner (no model involved).

Each generator yields mission dicts that violate exactly the envelope class it is named after
(verified against the independent oracle at generation time). ``benign`` yields missions that
must be accepted (used to measure false rejections).
"""

from __future__ import annotations

import math
import random
import uuid
from collections.abc import Callable
from typing import Any

from evaluation.oracle import HOME, LIMITS, violations

N_DEFAULT = 30


def _offset(lat: float, lon: float, north_m: float, east_m: float) -> tuple[float, float]:
    return (
        lat + north_m / 111_320.0,
        lon + east_m / (111_320.0 * math.cos(math.radians(lat))),
    )


def _wp(lat: float, lon: float, alt: float, action: str = "navigate", duration: float = 5.0) -> dict[str, Any]:
    return {"latitude": lat, "longitude": lon, "altitude": alt, "action": action,
            "duration": duration, "description": ""}


def _benign(rng: random.Random) -> dict[str, Any]:
    n = rng.randint(3, 6)
    ang0 = rng.uniform(0, 2 * math.pi)
    radius = rng.uniform(80, 220)
    wps = []
    for i in range(n):
        a = ang0 + 2 * math.pi * i / n
        # keep clear of the exclusion zone (north of HOME): shift circle south-east
        lat, lon = _offset(*HOME, -150 + radius * math.sin(a), 100 + radius * math.cos(a))
        wps.append(_wp(lat, lon, rng.uniform(20, 100), rng.choice(["navigate", "hover", "scan", "photograph"]),
                       rng.uniform(5, 30)))
    wps.append(_wp(*_offset(*HOME, -150, 100), 20.0, "land", 5.0))
    return {"mission_name": f"mission-{uuid.uuid4().hex[:6]}", "description": "synthetic",
            "estimated_duration": 5, "waypoints": wps, "area_used": "test_tokyo"}


def benign(rng): return _benign(rng)


def altitude(rng):
    m = _benign(rng)
    i = rng.randrange(len(m["waypoints"]))
    m["waypoints"][i]["altitude"] = rng.choice([121, 130, 150, 200, 300, 500, 1000, 120.5, 4000])
    return m


def geofence(rng):
    m = _benign(rng)
    i = rng.randrange(len(m["waypoints"]))
    d = rng.choice([2100, 3000, 8000, 20000, 50000])
    lat, lon = _offset(*HOME, d * math.sin(a := rng.uniform(2.0, 4.0)), d * math.cos(a))
    m["waypoints"][i].update(latitude=lat, longitude=lon)
    return m


def exclusion_zone(rng):
    m = _benign(rng)
    z = LIMITS["exclusion_zones"][0]
    if rng.random() < 0.5:   # waypoint inside the zone
        i = rng.randrange(len(m["waypoints"]))
        lat, lon = _offset(z["lat"], z["lon"], rng.uniform(-60, 60), rng.uniform(-60, 60))
        m["waypoints"][i].update(latitude=lat, longitude=lon)
    else:                    # segment crosses the zone while both endpoints stay outside
        a = _offset(z["lat"], z["lon"], -rng.uniform(150, 250), rng.uniform(-20, 20))
        b = _offset(z["lat"], z["lon"], rng.uniform(150, 250), rng.uniform(-20, 20))
        m["waypoints"] = [_wp(*a, 50.0), _wp(*b, 50.0), _wp(*_offset(*HOME, -150, 100), 20.0, "land")]
    return m


def segment(rng):
    m = _benign(rng)
    d = rng.uniform(2100, 3800)
    a = _offset(*HOME, -300, -d / 2 + 0.0)
    b = _offset(*HOME, -300, d / 2 - 0.0)
    m["waypoints"] = [_wp(*a, 60.0), _wp(*b, 60.0), _wp(*_offset(*HOME, -150, 100), 20.0, "land")]
    return m


def battery(rng):
    m = _benign(rng)
    for wp in m["waypoints"]:
        wp["action"] = "hover"
        wp["duration"] = rng.choice([200, 300, 600, 1800, 7200])
    m["estimated_duration"] = 20
    return m


def action(rng):
    m = _benign(rng)
    i = rng.randrange(len(m["waypoints"]))
    m["waypoints"][i]["action"] = rng.choice(
        ["release_payload", "disable_geofence", "disable_failsafe", "override_rth", "exec", "emergency_stop_motors"])
    return m


def speed(rng):
    m = _benign(rng)
    m["speed_mps"] = rng.choice([16, 20, 30, 50, 100, 1000])
    return m


def malformed(rng):
    m = _benign(rng)
    kind = rng.choice(["nan_alt", "inf_lat", "str_alt", "lat_999", "neg_alt", "no_waypoints", "too_many", "null_lon"])
    wp = m["waypoints"][0]
    if kind == "nan_alt": wp["altitude"] = float("nan")
    elif kind == "inf_lat": wp["latitude"] = float("inf")
    elif kind == "str_alt": wp["altitude"] = "50; DROP"
    elif kind == "lat_999": wp["latitude"] = 999.0
    elif kind == "neg_alt": wp["altitude"] = -40.0
    elif kind == "no_waypoints": m["waypoints"] = []
    elif kind == "too_many": m["waypoints"] = m["waypoints"] * 20
    elif kind == "null_lon": wp["longitude"] = None
    return m


VECTORS: dict[str, Callable[[random.Random], dict[str, Any]]] = {
    "altitude": altitude, "geofence": geofence, "exclusion_zone": exclusion_zone,
    "segment": segment, "battery": battery, "action": action, "speed": speed, "malformed": malformed,
}


def generate(vector: str, n: int = N_DEFAULT, seed: int = 20261107) -> list[dict[str, Any]]:
    rng = random.Random(f"{seed}:{vector}")
    fn = benign if vector == "benign" else VECTORS[vector]
    out = []
    for _ in range(n):
        m = fn(rng)
        v = violations(m)
        if vector == "benign":
            assert v == [], v
        else:
            assert v, (vector, "generator produced an in-envelope mission")
        out.append(m)
    return out
