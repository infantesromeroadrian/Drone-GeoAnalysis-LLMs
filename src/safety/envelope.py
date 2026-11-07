"""Safety envelope: configuration and the pure, deterministic mission evaluator.

``evaluate`` is fail-closed: anything it cannot positively verify (wrong type, NaN/inf, unknown
key, oversized field) is a violation. It never calls an LLM and has no side effects.

Altitudes are relative to the home (take-off) point. The EU open-category limit (Implementing
Regulation (EU) 2019/947, Art. 4(1)(e)) is measured from the closest point of the surface of the
earth; relative altitude equals that only on flat terrain at the launch elevation. This prototype
does not use a terrain model.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.safety.geometry import (
    LocalFrame,
    haversine_m,
    point_in_polygon,
    segment_intersects_polygon,
    segment_point_distance,
    segments_properly_cross,
)

LatLon = tuple[float, float]

WAYPOINT_KEYS = frozenset({"latitude", "longitude", "altitude", "action", "duration", "description", "actions"})
SUBACTION_KEYS = frozenset({"type", "duration"})
GROUND_ACTIONS = frozenset({"land", "takeoff"})


class ExclusionZone(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = "zone"
    center: LatLon | None = None          # circle: (lat, lon) + radius_m
    radius_m: float | None = Field(default=None, gt=0)
    vertices: tuple[LatLon, ...] | None = None  # polygon: >= 3 (lat, lon)

    @model_validator(mode="after")
    def _shape(self) -> ExclusionZone:
        circle = self.center is not None and self.radius_m is not None
        poly = self.vertices is not None and len(self.vertices) >= 3
        if circle == poly:
            raise ValueError("zone must be exactly one of: circle (center+radius_m) or polygon (>=3 vertices)")
        return self


class SafetyEnvelope(BaseModel):
    """Operating limits. Defaults are conservative; override via JSON (SAFETY_ENVELOPE_FILE)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_altitude_m: float = Field(default=120.0, gt=0)
    min_altitude_m: float = Field(default=2.0, ge=0)
    max_distance_from_home_m: float = Field(default=500.0, gt=0)  # approximation to VLOS; operator must verify
    max_segment_m: float = Field(default=1000.0, gt=0)  # conservative; see max_distance_from_home_m
    max_speed_mps: float = Field(default=15.0, gt=0)
    max_waypoints: int = Field(default=50, gt=0)
    endurance_s: float = Field(default=1200.0, gt=0)
    battery_reserve_fraction: float = Field(default=0.30, ge=0, lt=1)
    allowed_actions: frozenset[str] = frozenset(
        {"navigate", "hover", "scan", "photograph", "patrol", "land", "takeoff"})
    allowed_subaction_types: frozenset[str] = frozenset({"capture_image", "start_video", "stop_video", "hover"})
    geofence_polygon: tuple[LatLon, ...] | None = None  # optional; default = circle around home
    exclusion_zones: tuple[ExclusionZone, ...] = ()
    home_tolerance_m: float = Field(default=10.0, gt=0)
    max_text_len: int = 500

    def fingerprint(self) -> str:
        data = self.model_dump(mode="json")
        for k in ("allowed_actions", "allowed_subaction_types"):
            data[k] = sorted(data[k])
        return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @classmethod
    def from_file(cls, path: str) -> SafetyEnvelope:
        """Load a JSON envelope; top-level keys starting with ``_`` (comments) are ignored."""
        with open(path, encoding="utf-8") as f:
            data = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
        return cls.model_validate(data)

    @classmethod
    def from_env(cls) -> SafetyEnvelope:
        path = os.environ.get("SAFETY_ENVELOPE_FILE")
        return cls.from_file(path) if path else cls()


class Violation(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: str
    message: str
    waypoint: int | None = None


class Verdict(BaseModel):
    violations: list[Violation] = []

    @property
    def ok(self) -> bool:
        return not self.violations

    def codes(self) -> set[str]:
        return {v.code for v in self.violations}


def _num(x: Any) -> float | None:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        return None
    return float(x)


def check_point(lat: float, lon: float, alt: float, home: LatLon, env: SafetyEnvelope,
                ground_ok: bool = False) -> list[Violation]:
    """Envelope checks that apply to a single commanded position (also used by controller guards)."""
    out: list[Violation] = []
    vals = (_num(lat), _num(lon), _num(alt))
    if None in vals or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return [Violation(code="malformed", message="non-finite or out-of-range coordinate")]
    if alt > env.max_altitude_m or alt < 0 or (alt < env.min_altitude_m and not ground_ok):
        out.append(Violation(code="altitude",
                             message=f"altitude {alt} outside [{env.min_altitude_m}, {env.max_altitude_m}] m"))
    frame = LocalFrame(*home)
    if haversine_m(home, (lat, lon)) > env.max_distance_from_home_m:
        out.append(Violation(code="geofence", message="beyond maximum distance from home"))
    if env.geofence_polygon is not None:
        poly = [frame.to_xy(*v) for v in env.geofence_polygon]
        if not point_in_polygon(frame.to_xy(lat, lon), poly):
            out.append(Violation(code="geofence", message="outside geofence polygon"))
    for z in env.exclusion_zones:
        if _in_zone(frame, z, frame.to_xy(lat, lon)):
            out.append(Violation(code="exclusion_zone", message=f"inside exclusion zone '{z.name}'"))
    return out


def _in_zone(frame: LocalFrame, z: ExclusionZone, p: tuple[float, float]) -> bool:
    if z.center is not None:
        c = frame.to_xy(*z.center)
        return ((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2) <= z.radius_m ** 2
    return point_in_polygon(p, [frame.to_xy(*v) for v in z.vertices])


def _segment_hits_zone(frame: LocalFrame, z: ExclusionZone, p: tuple[float, float], q: tuple[float, float]) -> bool:
    if z.center is not None:
        return segment_point_distance(p, q, frame.to_xy(*z.center)) <= z.radius_m
    return segment_intersects_polygon(p, q, [frame.to_xy(*v) for v in z.vertices])


def evaluate(mission: Any, env: SafetyEnvelope, home: LatLon,
             start: LatLon | None = None) -> Verdict:
    """Evaluate a mission against the envelope. ``start`` defaults to ``home`` (path origin)."""
    v: list[Violation] = []

    def add(code: str, msg: str, wp: int | None = None) -> None:
        v.append(Violation(code=code, message=msg, waypoint=wp))

    if not isinstance(mission, Mapping):
        return Verdict(violations=[Violation(code="malformed", message="mission is not an object")])
    hl = (_num(home[0]), _num(home[1])) if isinstance(home, (tuple, list)) and len(home) == 2 else (None, None)
    if None in hl:
        return Verdict(violations=[Violation(code="malformed", message="invalid home position")])
    wps = mission.get("waypoints")
    if not isinstance(wps, list) or not wps:
        return Verdict(violations=[Violation(code="malformed", message="missing or empty waypoint list")])
    if len(wps) > env.max_waypoints:
        return Verdict(violations=[Violation(code="malformed",
                                             message=f"{len(wps)} waypoints exceeds {env.max_waypoints}")])

    speed_raw = mission.get("speed_mps", env.max_speed_mps)
    speed = _num(speed_raw)
    if speed is None or speed <= 0:
        add("speed", "invalid speed")
        speed = env.max_speed_mps
    elif speed > env.max_speed_mps:
        add("speed", f"requested speed {speed} m/s exceeds {env.max_speed_mps} m/s")
        speed = env.max_speed_mps

    frame = LocalFrame(*home)
    pts: list[LatLon] = []
    dwell = 0.0
    for i, wp in enumerate(wps):
        if not isinstance(wp, Mapping):
            return Verdict(violations=v + [Violation(code="malformed", message="waypoint is not an object",
                                                      waypoint=i)])
        extra = set(wp) - WAYPOINT_KEYS
        if extra:
            add("malformed", f"unknown waypoint keys {sorted(map(str, extra))}", i)
        lat, lon, alt = _num(wp.get("latitude")), _num(wp.get("longitude")), _num(wp.get("altitude"))
        action = wp.get("action", "navigate")
        if not isinstance(action, str) or action not in env.allowed_actions:
            add("action", f"action {action!r} not in allow-list", i)
        if lat is None or lon is None or alt is None:
            add("malformed", "latitude/longitude/altitude must be finite numbers", i)
            continue
        v.extend(Violation(code=x.code, message=x.message, waypoint=i)
                 for x in check_point(lat, lon, alt, home, env, ground_ok=action in GROUND_ACTIONS))
        d = _num(wp.get("duration", 0.0))
        if d is None or d < 0:
            add("malformed", "duration must be a finite non-negative number", i)
        else:
            dwell += d
        desc = wp.get("description", "")
        if not isinstance(desc, str) or len(desc) > env.max_text_len:
            add("malformed", "description must be a short string", i)
        subs = wp.get("actions", [])
        if not isinstance(subs, list) or len(subs) > 20:
            add("malformed", "actions must be a short list", i)
        else:
            for s in subs:
                if not isinstance(s, Mapping) or set(s) - SUBACTION_KEYS:
                    add("malformed", "invalid sub-action", i)
                    continue
                if s.get("type") not in env.allowed_subaction_types:
                    add("action", f"sub-action {s.get('type')!r} not in allow-list", i)
                sd = _num(s.get("duration", 0.0))
                if sd is None or sd < 0:
                    add("malformed", "invalid sub-action duration", i)
                else:
                    dwell += sd
        pts.append((lat, lon))

    if len(pts) != len(wps):
        return Verdict(violations=v)  # cannot reason about the path of a malformed mission

    origin = start if start is not None else home
    chain = [origin, *pts]
    path = 0.0
    for j, (a, b) in enumerate(zip(chain, chain[1:])):
        seg = haversine_m(a, b)
        path += seg
        if seg > env.max_segment_m:
            add("segment", f"segment of {seg:.0f} m exceeds {env.max_segment_m:.0f} m", j)
        pa, pb = frame.to_xy(*a), frame.to_xy(*b)
        for z in env.exclusion_zones:
            if _segment_hits_zone(frame, z, pa, pb):
                add("exclusion_zone", f"leg {j} crosses exclusion zone '{z.name}'", j)
        if env.geofence_polygon is not None:
            poly = [frame.to_xy(*q) for q in env.geofence_polygon]
            n = len(poly)
            if j == 0 and not point_in_polygon(pa, poly):
                add("geofence", "path origin outside geofence polygon", j)
            if any(segments_properly_cross(pa, pb, poly[k], poly[(k + 1) % n]) for k in range(n)):
                add("geofence", f"leg {j} crosses the geofence boundary", j)
    path += haversine_m(pts[-1], home)  # return-to-home leg
    needed = path / speed + dwell
    budget = env.endurance_s * (1 - env.battery_reserve_fraction)
    if needed > budget:
        add("battery", f"estimated {needed:.0f} s exceeds budget {budget:.0f} s "
                       f"({env.battery_reserve_fraction:.0%} reserve of {env.endurance_s:.0f} s)")
    return Verdict(violations=v)

