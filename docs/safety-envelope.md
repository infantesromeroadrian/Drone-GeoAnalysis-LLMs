# Safety envelope and approval flow

Reference for `src/safety/`. Rationale and evidence are in [case-study.md](case-study.md); the threat analysis is in [threat-model.md](threat-model.md).

## Principle

Nothing in `src/safety/` calls an LLM. A plan from any source is either inside the envelope and explicitly approved by a human, or it never reaches a controller. The LLM may propose; it cannot decide, approve or bypass.

## Envelope parameters

Defaults (override with `SAFETY_ENVELOPE_FILE`, see `config/safety_envelope.example.json`). All distances are metres, altitudes are relative to the home point.

| Parameter | Default | Violation code |
|---|---|---|
| `max_altitude_m` / `min_altitude_m` | 120 / 2 (no minimum for `land`/`takeoff` waypoints) | `altitude` |
| `max_distance_from_home_m` | 500 (circle around home; conservative approximation to VLOS, the operator must verify their own case); optional `geofence_polygon` | `geofence` |
| `exclusion_zones` | none by default; circles or polygons; legs are tested with segment-circle distance and segment-polygon intersection, not by sampling | `exclusion_zone` |
| `max_segment_m` | 1000 (includes home to first waypoint) | `segment` |
| `max_speed_mps` | 15; a mission requesting more is **rejected**, not clipped | `speed` |
| `endurance_s`, `battery_reserve_fraction` | 1200 s, 0.30; estimate = path (including the return leg to home) / speed + dwell times and sub-action durations | `battery` |
| `allowed_actions`, `allowed_subaction_types` | navigate, hover, scan, photograph, patrol, land, takeoff; capture_image, start_video, stop_video, hover | `action` |
| `max_waypoints`, `max_text_len` | 50, 500 | `malformed` |

Fail-closed: non-numeric, boolean, NaN/inf, unknown waypoint keys, wrong types, oversized lists or strings are violations. `evaluate()` is total (never raises) on arbitrary input; this is property-tested.

### Regulatory context (verify before relying on it)

The 120 m default corresponds to the EU "open" category rule that the unmanned aircraft is maintained within 120 metres from the closest point of the surface of the earth (Commission Implementing Regulation (EU) 2019/947, Article 4(1)(e); checked on EUR-Lex, 2026-11-07). That rule is measured against the terrain below the aircraft; this prototype uses altitude relative to the launch point and has no terrain model, so it is only equivalent on flat ground at launch elevation. The same article requires visual line of sight (4(1)(d)); the 500 m default radius is only a conservative approximation to VLOS and the operator must verify actual line of sight. The Tokyo evaluation scenario deliberately uses 2000 m (`evaluation/scenario_tokyo.json`) and is not a VLOS-compatible configuration. Other jurisdictions differ.

### Projection accuracy

Zone and geofence tests use a local equirectangular frame centred on home: `x = R * dlon * cos(lat0)`, `y = R * dlat`. The relative error is second order in distance/R and stays below roughly 0.1 % at the radii used here (a few metres at 2 km, small against 120 m zones) at mid latitudes. It is not valid near the poles or across the antimeridian; such missions are rejected by the distance limit anyway. Distances use haversine.

## Approval flow

1. `POST /api/missions/llm/create` (or an in-flight amendment). The service runs the envelope. A violation returns `success: false` with the violations and the mission is not approvable. An accepted mission returns `requires_approval: true`, the full plan and `mission_hash`.
2. The operator reviews (`GET /api/missions/<id>/review`; the dashboard shows the plan on the map with its hash).
3. `POST /api/missions/<id>/approve {"mission_hash": ...}` with header `X-Operator-Key`. The server recomputes the hash and the envelope; only an exact match yields a token (`secrets.token_urlsafe(32)`, single use, 300 s TTL). Without `OPERATOR_API_KEY` configured the endpoint answers 503.
4. `POST /api/missions/execute {"mission_id", "approval_token"}`. `MissionExecutor.start` reloads the mission from disk, and the gate re-evaluates the envelope, recomputes the hash, checks the token (unknown, used, expired, wrong mission), and that the drone is within `home_tolerance_m` (10 m) of the approved home. Any failure burns the token. Only then is an `ApprovedMission` minted and handed to the executor thread.
5. In flight, `hold`, `abort` and `return_to_base` amendments reduce risk and are applied directly. `replace_waypoints` becomes a new mission (new id, `parent_mission_id`): full envelope check against the original home, fresh hash, fresh approval. The old token is useless.

Canonical hash: SHA-256 of sorted-key, fixed-separator JSON of the flight-relevant projection (waypoints with action, duration and sub-actions; speed; home; envelope fingerprint), floats normalised to 7 decimals, `allow_nan=False`. Descriptions and other metadata are not part of the hash and are never read by an executor.

## Enforcement points

- `MissionExecutor.start` is the only producer of executable missions (needs a `MissionGate`; without one it refuses).
- `BaseDrone.execute_mission` accepts only a genuine `ApprovedMission` (HMAC-SHA256 with a per-process random key, plus a re-hash of the plan). Controllers cannot override `move_to`, `take_off` or `execute_mission` (tested); they implement `_do_*` hooks.
- `BaseDrone.move_to` / `take_off` check every command against the envelope and the recorded home, even for manual control. No home recorded means no motion command (fail-closed). Because it lives in the base class, the Olympe (real hardware) branch of the Parrot controller is guarded too.

## Limits of the guarantee

- In-process: code that already executes arbitrary Python inside the server can bypass any in-process check. The guarantee covers the LLM, its tools and accidental code paths, which is the modelled adversary.
- A restart regenerates the HMAC key and the grant store: every outstanding approval becomes invalid. This is intentional (fail-closed) and operationally visible.
- `OPERATOR_API_KEY` proves possession of a shared secret. It is not a user identity and gives no non-repudiation; the audit log stores short hashes of the key and token only. A compromised operator workstation or a careless operator who approves a harmful but in-envelope mission is outside the envelope's reach.
- The envelope bounds *where, how high, how fast, how long and which actions*. It does not know about people, buildings, weather, airspace updates, GNSS failure or radio loss.
- Altitude is relative to home; there is no terrain, obstacle or live airspace data.
