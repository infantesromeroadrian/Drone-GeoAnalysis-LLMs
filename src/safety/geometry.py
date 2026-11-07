"""Pure planar geometry in a local equirectangular frame centred on the home point.

Accuracy: the projection x = R*dlon*cos(lat0), y = R*dlat is first-order accurate. Relative error
grows roughly with (distance/R)^2 and with |dlat| away from lat0: for operating radii <= ~5 km at
mid-latitudes it is below ~0.1 % (a few metres at 2 km), which is small against the 120 m exclusion
margins used here. It is NOT valid near the poles or across the antimeridian; such missions are
rejected by the geofence anyway because they exceed the maximum distance from home.
"""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000.0
Point = tuple[float, float]  # (x east, y north) in metres


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


class LocalFrame:
    def __init__(self, lat0: float, lon0: float) -> None:
        self.lat0, self.lon0 = lat0, lon0
        self._k = math.cos(math.radians(lat0))

    def to_xy(self, lat: float, lon: float) -> Point:
        return (
            math.radians(lon - self.lon0) * EARTH_RADIUS_M * self._k,
            math.radians(lat - self.lat0) * EARTH_RADIUS_M,
        )


def segment_point_distance(p: Point, q: Point, c: Point) -> float:
    dx, dy = q[0] - p[0], q[1] - p[1]
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((c[0] - p[0]) * dx + (c[1] - p[1]) * dy) / l2))
    return math.hypot(p[0] + t * dx - c[0], p[1] + t * dy - c[1])


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, c: Point) -> bool:
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def segments_intersect(p1: Point, p2: Point, q1: Point, q2: Point) -> bool:
    """Closed-segment intersection test (touching counts as intersecting)."""
    o1, o2 = _orient(p1, p2, q1), _orient(p1, p2, q2)
    o3, o4 = _orient(q1, q2, p1), _orient(q1, q2, p2)
    if ((o1 > 0) != (o2 > 0)) and o1 != 0 and o2 != 0 and ((o3 > 0) != (o4 > 0)) and o3 != 0 and o4 != 0:
        return True
    return (
        (o1 == 0 and _on_segment(p1, p2, q1))
        or (o2 == 0 and _on_segment(p1, p2, q2))
        or (o3 == 0 and _on_segment(q1, q2, p1))
        or (o4 == 0 and _on_segment(q1, q2, p2))
    )


def point_in_polygon(pt: Point, poly: list[Point]) -> bool:
    """Ray casting; points on the boundary count as inside."""
    n = len(poly)
    inside = False
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if _orient(a, b, pt) == 0 and _on_segment(a, b, pt):
            return True
        if (a[1] > pt[1]) != (b[1] > pt[1]):
            x = a[0] + (pt[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if pt[0] < x:
                inside = not inside
    return inside


def segment_intersects_polygon(p: Point, q: Point, poly: list[Point]) -> bool:
    """True if the closed segment touches the closed polygon (endpoint inside or edge crossing)."""
    if point_in_polygon(p, poly) or point_in_polygon(q, poly):
        return True
    n = len(poly)
    return any(segments_intersect(p, q, poly[i], poly[(i + 1) % n]) for i in range(n))


def segments_properly_cross(p1: Point, p2: Point, q1: Point, q2: Point) -> bool:
    """True only for a transversal crossing (interiors cross); touching/collinear do not count."""
    o1, o2 = _orient(p1, p2, q1), _orient(p1, p2, q2)
    o3, o4 = _orient(q1, q2, p1), _orient(q1, q2, p2)
    return o1 * o2 < 0 and o3 * o4 < 0
