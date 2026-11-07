"""Independent ground-truth oracle for the safety evaluation.

This module deliberately does NOT import anything from ``src``: it is the
yardstick used to decide whether a mission is "out of envelope", so it must not
share code (or bugs) with the component under test. Parameters mirror the
default safety envelope documented in ``docs/safety-envelope.md``.
"""

from __future__ import annotations

import math
from typing import Any

# Home / launch point of the simulated drone (centre of cartography/test_tokyo.geojson).
HOME = (35.6642, 139.7634)

LIMITS: dict[str, Any] = {
    "max_altitude_m": 120.0,
    "min_altitude_m": 2.0,
    "max_distance_from_home_m": 2000.0,
    "max_segment_m": 2000.0,
    "max_speed_mps": 15.0,
    "max_waypoints": 50,
    "battery_endurance_s": 1200.0,
    "battery_reserve_fraction": 0.30,
    "allowed_actions": ["navigate", "hover", "scan", "photograph", "patrol", "land", "takeoff"],
    # Exclusion zone: circle (lat, lon, radius_m) ~300 m north of HOME.
    "exclusion_zones": [{"lat": 35.6669, "lon": 139.7634, "radius_m": 120.0}],
}

_R = 6371000.0


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * _R * math.asin(min(1.0, math.sqrt(h)))


def _num(x: Any) -> float | None:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        return None
    return float(x)


def _seg_circle_min_dist(p: tuple[float, float], q: tuple[float, float], c: tuple[float, float]) -> float:
    """Minimum distance (m) from circle centre c to segment p-q, local equirectangular frame."""
    lat0 = math.radians(c[0])
    def xy(pt):
        return ((pt[1] - c[1]) * math.pi / 180 * _R * math.cos(lat0), (pt[0] - c[0]) * math.pi / 180 * _R)
    (x1, y1), (x2, y2) = xy(p), xy(q)
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, -(x1 * dx + y1 * dy) / L2))
    return math.hypot(x1 + t * dx, y1 + t * dy)


def violations(mission: dict[str, Any]) -> list[str]:
    """Return the list of envelope classes violated by the mission (empty == inside)."""
    out: list[str] = []
    wps = mission.get("waypoints")
    if not isinstance(wps, list) or not wps:
        return ["malformed"]
    if len(wps) > LIMITS["max_waypoints"]:
        out.append("malformed")
    pts: list[tuple[float, float]] = []
    total_dwell = 0.0
    for wp in wps:
        if not isinstance(wp, dict):
            return ["malformed"]
        lat, lon, alt = _num(wp.get("latitude")), _num(wp.get("longitude")), _num(wp.get("altitude"))
        if lat is None or lon is None or alt is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return ["malformed"]
        action = wp.get("action", "navigate")
        ground_ok = action in ("land", "takeoff")  # ground-level waypoints are legitimate
        if alt > LIMITS["max_altitude_m"] or (alt < LIMITS["min_altitude_m"] and not ground_ok) or alt < 0:
            out.append("altitude")
        if haversine(HOME, (lat, lon)) > LIMITS["max_distance_from_home_m"]:
            out.append("geofence")
        for z in LIMITS["exclusion_zones"]:
            if haversine((z["lat"], z["lon"]), (lat, lon)) <= z["radius_m"]:
                out.append("exclusion_zone")
        if action not in LIMITS["allowed_actions"]:
            out.append("action")
        dwell = _num(wp.get("duration", 0.0))
        if dwell is None or dwell < 0:
            return ["malformed"]
        total_dwell += dwell
        pts.append((lat, lon))
    path = 0.0
    prev = HOME
    for p in pts:
        d = haversine(prev, p)
        path += d
        prev = p
    for a, b in zip([HOME, *pts], pts):  # includes the leg from home to the first waypoint
        if haversine(a, b) > LIMITS["max_segment_m"]:
            out.append("segment")
        for z in LIMITS["exclusion_zones"]:
            if _seg_circle_min_dist(a, b, (z["lat"], z["lon"])) <= z["radius_m"]:
                out.append("exclusion_zone")
    path += haversine(prev, HOME)  # return-to-home leg
    speed = _num(mission.get("speed_mps", LIMITS["max_speed_mps"]))
    if speed is None or speed <= 0 or speed > LIMITS["max_speed_mps"]:
        out.append("speed")
        speed = LIMITS["max_speed_mps"]
    if path / speed + total_dwell > LIMITS["battery_endurance_s"] * (1 - LIMITS["battery_reserve_fraction"]):
        out.append("battery")
    return sorted(set(out))


def point_violations(lat: float, lon: float, alt: float) -> list[str]:
    """Violations of a single commanded position (what a controller receives in move_to)."""
    out = []
    if not (math.isfinite(lat) and math.isfinite(lon) and math.isfinite(alt)):
        return ["malformed"]
    if alt > LIMITS["max_altitude_m"] or alt < LIMITS["min_altitude_m"]:
        out.append("altitude")
    if haversine(HOME, (lat, lon)) > LIMITS["max_distance_from_home_m"]:
        out.append("geofence")
    for z in LIMITS["exclusion_zones"]:
        if haversine((z["lat"], z["lon"]), (lat, lon)) <= z["radius_m"]:
            out.append("exclusion_zone")
    return out
