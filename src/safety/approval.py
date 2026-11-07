"""Binding human approval and the unforgeable ``ApprovedMission`` capability.

Flow: ``review`` (envelope check, hash shown to the operator) -> ``approve`` (operator supplies the
exact hash; server issues a single-use, expiring token bound to that hash) -> ``redeem`` (at
execution time the mission is reloaded, re-hashed and re-evaluated; only then is an
``ApprovedMission`` minted).

Threat boundary (be honest): the guarantee is against the LLM, its tools and accidental code paths.
Arbitrary code running inside this Python process can always bypass in-process checks; the HMAC key
is per-process, so an ``ApprovedMission`` cannot be forged from outside ``MissionGate`` without it,
and a restart invalidates every outstanding approval (fail-closed, by design).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.safety.envelope import SafetyEnvelope, Violation, evaluate
from src.safety.geometry import haversine_m

LatLon = tuple[float, float]
_PROCESS_KEY = secrets.token_bytes(32)
_MINT = object()  # capability needed to construct ApprovedMission


class ApprovalError(Exception):
    """Raised when an approval cannot be granted or redeemed. ``code`` is machine readable."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code


def _norm(x: Any) -> Any:
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return round(float(x), 7)
    if isinstance(x, Mapping):
        return {str(k): _norm(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    if isinstance(x, (list, tuple)):
        return [_norm(i) for i in x]
    return x


def flight_plan(mission: Mapping[str, Any], envelope: SafetyEnvelope) -> dict[str, Any]:
    """Projection of the mission onto the fields that can influence flight. Executors only ever read this."""
    wps = []
    for wp in mission["waypoints"]:
        w = {k: wp[k] for k in ("latitude", "longitude", "altitude", "action", "duration", "actions") if k in wp}
        w.setdefault("action", "navigate")
        w.setdefault("duration", 0.0)
        wps.append(w)
    return {"waypoints": wps, "speed_mps": mission.get("speed_mps", envelope.max_speed_mps)}


def canonical_json(plan: Mapping[str, Any], home: LatLon, env_fp: str) -> str:
    return json.dumps({"plan": _norm(plan), "home": _norm(list(home)), "envelope": env_fp},
                      sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=True)


def mission_hash(plan: Mapping[str, Any], home: LatLon, env_fp: str) -> str:
    return hashlib.sha256(canonical_json(plan, home, env_fp).encode()).hexdigest()


@dataclass(frozen=True)
class ApprovedMission:
    """Capability object. Construct only through ``MissionGate``; consumers call ``require``."""

    mission_id: str
    plan_json: str
    mission_hash: str
    mac: str
    _key: Any = None

    def __post_init__(self) -> None:
        if self._key is not _MINT:
            raise ApprovalError("forbidden", "ApprovedMission can only be minted by MissionGate")

    @staticmethod
    def _mac(mission_id: str, h: str) -> str:
        return hmac.new(_PROCESS_KEY, f"{mission_id}|{h}".encode(), hashlib.sha256).hexdigest()

    @classmethod
    def require(cls, obj: Any) -> ApprovedMission:
        """Validate that ``obj`` is a genuine, untampered ApprovedMission; raise otherwise."""
        if not isinstance(obj, cls):
            raise ApprovalError("not_approved", f"expected ApprovedMission, got {type(obj).__name__}")
        if hashlib.sha256(obj.plan_json.encode()).hexdigest() != obj.mission_hash:
            raise ApprovalError("tampered", "plan does not match approved hash")
        if not hmac.compare_digest(obj.mac, cls._mac(obj.mission_id, obj.mission_hash)):
            raise ApprovalError("tampered", "invalid MAC")
        return obj

    @property
    def waypoints(self) -> list[dict[str, Any]]:
        return json.loads(self.plan_json)["plan"]["waypoints"]

    @property
    def speed_mps(self) -> float:
        return float(json.loads(self.plan_json)["plan"]["speed_mps"])

    @property
    def home(self) -> LatLon:
        h = json.loads(self.plan_json)["home"]
        return (h[0], h[1])


@dataclass
class Review:
    ok: bool
    mission_id: str
    mission_hash: str | None
    violations: list[Violation]
    summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "mission_id": self.mission_id, "mission_hash": self.mission_hash,
                "violations": [v.model_dump() for v in self.violations], "summary": self.summary}


class AuditLog:
    """Append-only JSONL. Never records the operator key or a full token (only short hashes)."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.environ.get("SAFETY_AUDIT_LOG", "")
        self._lock = threading.Lock()

    def write(self, event: str, **fields: Any) -> None:
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
        if not self.path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with self._lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True, default=str) + "\n")


def short_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()[:12]


@dataclass
class _Grant:
    mission_id: str
    mission_hash: str
    home: LatLon
    kind: str            # "new" | "amendment"
    expires_at: float
    approver: str
    used: bool = False


class MissionGate:
    """The single mandatory control point between any plan and any controller."""

    def __init__(self, envelope: SafetyEnvelope | None = None, ttl_s: float = 300.0,
                 clock: Callable[[], float] = time.time, audit: AuditLog | None = None) -> None:
        self.envelope = envelope or SafetyEnvelope.from_env()
        self.ttl_s = ttl_s
        self._clock = clock
        self.audit = audit or AuditLog()
        self._grants: dict[str, _Grant] = {}   # key: sha256(token)
        self._lock = threading.Lock()

    # -- review -----------------------------------------------------------------------------
    def review(self, mission_id: str, mission: Any, home: LatLon, start: LatLon | None = None) -> Review:
        verdict = evaluate(mission, self.envelope, home, start)
        if not verdict.ok:
            self.audit.write("rejected", mission_id=mission_id, codes=sorted(verdict.codes()))
            return Review(False, mission_id, None, verdict.violations, {})
        plan = flight_plan(mission, self.envelope)
        h = self._hash(plan, home)
        summary = {"waypoints": plan["waypoints"], "speed_mps": plan["speed_mps"], "home": list(home),
                   "envelope_fingerprint": self.envelope.fingerprint()[:16]}
        self.audit.write("reviewed", mission_id=mission_id, mission_hash=h[:16])
        return Review(True, mission_id, h, [], summary)

    def _hash(self, plan: Mapping[str, Any], home: LatLon) -> str:
        return hashlib.sha256(canonical_json(plan, home, self.envelope.fingerprint()).encode()).hexdigest()

    # -- approve ----------------------------------------------------------------------------
    def approve(self, mission_id: str, mission: Any, home: LatLon, presented_hash: str,
                approver: str, kind: str = "new", start: LatLon | None = None) -> str:
        """Operator approval. Returns a one-time token. ``presented_hash`` must equal the server hash."""
        r = self.review(mission_id, mission, home, start)
        if not r.ok:
            raise ApprovalError("envelope_violation", "; ".join(v.message for v in r.violations))
        if not isinstance(presented_hash, str) or not hmac.compare_digest(presented_hash, r.mission_hash):
            self.audit.write("approval_refused", mission_id=mission_id, reason="hash_mismatch")
            raise ApprovalError("hash_mismatch", "presented hash does not match the mission")
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._purge()
            self._grants[hashlib.sha256(token.encode()).hexdigest()] = _Grant(
                mission_id, r.mission_hash, (float(home[0]), float(home[1])), kind,
                self._clock() + self.ttl_s, approver)
        self.audit.write("approved", mission_id=mission_id, mission_hash=r.mission_hash[:16],
                         token=short_hash(token), approver=short_hash(approver), kind=kind)
        return token

    def _purge(self) -> None:
        now = self._clock()
        for k in [k for k, g in self._grants.items() if g.used or g.expires_at < now]:
            del self._grants[k]

    # -- redeem -----------------------------------------------------------------------------
    def redeem(self, token: Any, mission_id: str, mission: Any, position: LatLon) -> ApprovedMission:
        """Verify and consume a token; return the capability. Any failure burns the token (fail-closed)."""
        if not isinstance(token, str) or not token:
            self.audit.write("redeem_refused", mission_id=mission_id, reason="no_token")
            raise ApprovalError("no_token", "approval token required")
        key = hashlib.sha256(token.encode()).hexdigest()
        with self._lock:
            g = self._grants.get(key)
            if g is None or g.used:
                self.audit.write("redeem_refused", mission_id=mission_id, reason="unknown_or_used",
                                 token=short_hash(token))
                raise ApprovalError("invalid_token", "unknown or already used token")
            g.used = True  # burn first: single use even if verification below fails
            if g.expires_at < self._clock():
                self.audit.write("redeem_refused", mission_id=mission_id, reason="expired", token=short_hash(token))
                raise ApprovalError("expired", "token expired")
        try:
            if g.mission_id != mission_id:
                raise ApprovalError("wrong_mission", "token is bound to a different mission")
            start = None if g.kind == "new" else position
            verdict = evaluate(mission, self.envelope, g.home, start)
            if not verdict.ok:
                raise ApprovalError("envelope_violation", "; ".join(v.message for v in verdict.violations))
            plan = flight_plan(mission, self.envelope)
            h = self._hash(plan, g.home)
            if not hmac.compare_digest(h, g.mission_hash):
                raise ApprovalError("hash_mismatch", "mission changed after approval")
            if g.kind == "new" and haversine_m(position, g.home) > self.envelope.home_tolerance_m:
                raise ApprovalError("position_mismatch", "drone is not at the approved home position")
        except ApprovalError as e:
            self.audit.write("redeem_refused", mission_id=mission_id, reason=e.code, token=short_hash(token))
            raise
        plan_json = canonical_json(plan, g.home, self.envelope.fingerprint())
        approved = ApprovedMission(mission_id, plan_json, hashlib.sha256(plan_json.encode()).hexdigest(),
                                   "", _MINT)
        object.__setattr__(approved, "mac", ApprovedMission._mac(mission_id, approved.mission_hash))
        self.audit.write("redeemed", mission_id=mission_id, mission_hash=h[:16], token=short_hash(token))
        return approved
