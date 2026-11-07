# Case study: advisory validation is not a barrier (LLM-planned drone missions)

All results come from simulation: a recording mock controller, no hardware, no real commands. Numbers are in [`evaluation/metrics.json`](../evaluation/metrics.json); raw per-trial data was kept outside the repository.

## Context

The project turns a natural-language order into a drone mission: an LLM (Groq/Llama, OpenAI, a local runner or, for this study, Ollama) returns waypoints, altitudes and actions; a service stores the mission; an executor flies it through a controller interface (`move_to` per waypoint). The repository had CI, 390 tests and ADRs, and described itself as an "enterprise" platform.

## Finding

A mission planned by the LLM could be created and executed although it violated every limit the code itself knew about.

Baseline commit: `52948ba0d58a52b38a87eca33c220910160da5d3` (tag `baseline-advisory-only`).

1. `validate_mission_safety` and `validate_mission_duration` returned **a list of warnings** (altitude over 120 m, segments over 10 km, invalid coordinates, duration over 120 min).
2. `MissionService.create_llm_mission` attached the warnings and returned `success: True` regardless. `start_mission` -> `MissionExecutor.start` never validated again; it read the mission JSON from disk by id and flew it.
3. The LangGraph agent exposed `validate_mission` as a tool the model *may* call. The pipeline outside the agent (`_legacy_create_mission`) did not even apply the schema that rejects altitudes above 120 m.
4. There was no limit on distance from home, no exclusion zones, no action allow-list at execution and no human approval.

## Proof of concept (simulation)

Harness: `evaluation/` (oracle independent of `src/`, seeded generators, recording mock). Metric: fraction of out-of-envelope missions for which at least one `move_to` reached the controller; Wilson 95 % interval.

- *Compromised LLM* (missions built directly, N = 30 per class): altitude, geofence, exclusion zone (legs through the zone), segment length, battery, forbidden action and speed all reached the controller 30/30 (0.89-1.00). Malformed missions (NaN, strings, 999 degrees latitude, no waypoints...) reached it 15/30; the rest failed by incidental exceptions.
- *Validated, then swapped*: a benign plan passes validation and the stored file is replaced by a violating one before start: 30/30 executed.
- *Plain operator orders to a real model* (`gpt-oss:120b-cloud` via Ollama 0.40.13, digest `ac7f7a1e7785...a022ed`, temperature 0.3, seed 7, reasoning effort low, 4000 max tokens, 24 orders in 7 classes in English and Spanish, 3 repetitions): the model produced an out-of-envelope plan in 11, 15 and 13 of 24 (39/72, 54 %), and **all 39 were created with success and executed**. A control group of 20 in-envelope orders ran 60/60. The model resists some requests by itself, which is exactly why it cannot be the control.

## Root cause

Validation was *advisory* instead of a *barrier*: the check produced information, nothing in the control flow depended on it, and the only path to the controller had no second check. Three conditions held at once: output of an untrusted component (the LLM) reached an actuator (OWASP LLM05 and LLM06), the safety rules lived in places the model could skip (a tool it may or may not call), and the stored artefact was not bound to what had been checked or approved.

## Fix

Detailed in [safety-envelope.md](safety-envelope.md). In short:

- `src/safety/envelope.py`: deterministic, fail-closed envelope (altitude, geofence plus exclusion zones with segment-polygon/segment-circle tests, distance from home, segment length, speed, duration vs battery with reserve, action allow-list).
- `src/safety/approval.py`: review -> approve (exact hash, operator key, single-use, expiring token) -> redeem (reload, re-hash, re-evaluate, position check) -> `ApprovedMission` capability (HMAC with a per-process key).
- `MissionExecutor.start` requires the token; controllers accept only an `ApprovedMission`, cannot override the guarded template methods, and check every `move_to`/`take_off` against the envelope.
- In-flight changes: `MissionAmendment` strict schema; only risk-reducing actions apply directly; new coordinates are a new mission needing a new approval.
- Untrusted text is delimited and parsed with strict schemas; documented as mitigation, not guarantee.

### Route inventory (every call site that reaches a controller motion or mission method)

Enumerated by AST scan of `src/` (`tests/safety_test/test_no_alternative_route.py` fails when a new call site appears):

| Call site | Reaches | Protection |
|---|---|---|
| `mission_executor.py` `_execute` | `move_to` | runs only an `ApprovedMission`; `move_to` guarded |
| `base_drone.py` `execute_mission` | `_execute_approved` | `ApprovedMission.require` (type, hash, HMAC) |
| `base_drone.py` `move_to`, `take_off` | `_do_move_to`, `_do_take_off` | envelope check, home required |
| `dji_controller.py` `_execute_waypoints` | `move_to` | only reachable through `_execute_approved`; `move_to` guarded |
| `parrot_anafi_controller.py` `_execute_approved` | `move_to` | approved waypoints; `move_to` guarded |
| `drone_service.py` `takeoff` | `take_off` | manual control: altitude pre-check plus guarded `take_off` |
| `mission_service.py` `execute_mission`, `start_mission` | `executor.start` | token required |
| `mission_controller.py` `start_mission`, `execute_mission` (HTTP) | service | token required |
| `drone_controller.py` `takeoff_drone` (HTTP) | `drone_service.takeoff` | guarded |
| LangGraph agent tools (`mission_agent.py`: `load_area_info`, `validate_mission`, `generate_area_grid_waypoints`, `calculate_waypoint_distances`, `finalize_mission`) | none | no import of the drone layer (tested); `finalize_mission` only writes a plan file, which is not executable without approval |
| `control-view.js` (browser) | `/api/drone/takeoff`, `/api/drone/land`, `/api/missions/*` | same server-side checks; the browser holds no authority |

`land` and video endpoints do not move the aircraft along a path and are unchanged.

## Verification (before / after)

Same harness, same oracle, same seeds, evaluation scenario envelope (2000 m) rather than the library defaults; the "before" runs use a pristine export of the baseline commit with only the Ollama provider (a measurement instrument) added.

| Vector | Before: reached controller | After: reached controller |
|---|---|---|
| Compromised LLM, altitude | 30/30 (0.89-1.00) | 0/30 (0.00-0.11) |
| Compromised LLM, geofence | 30/30 | 0/30 |
| Compromised LLM, exclusion zone | 30/30 | 0/30 |
| Compromised LLM, segment | 30/30 | 0/30 |
| Compromised LLM, battery | 30/30 | 0/30 |
| Compromised LLM, forbidden action | 30/30 | 0/30 |
| Compromised LLM, speed | 30/30 | 0/30 |
| Compromised LLM, malformed | 15/30 (0.33-0.67) | 0/30 |
| Stored file replaced after validation or approval | 30/30 | 0/30 |
| Compromised in-flight amendment (7 classes, 210 trials) | no code path | 0/210 (0.00-0.02) |
| Plain operator orders, real LLM, out-of-envelope plan produced / executed | 39/72 produced; 39/39 executed (0.91-1.00) | 41/72 produced; 0/41 executed (0.00-0.09) |
| In-envelope control (synthetic) | 30/30 executed | 30/30 executed |
| In-envelope control (LLM orders) | 60/60 | 58/60 (the 2 others were out-of-envelope LLM plans, rightly rejected) |

Additional checks after the fix: each attempt sequence also tried to start with no token, with a forged token, and to obtain an approval with a fabricated hash; a direct `execute_mission(dict)` on both controllers raises. Direct `move_to` calls with out-of-envelope points are refused by the guard (0 violating points reached the mock).

Test suite: 474 tests (the original 391 (390 passed, 1 skipped) plus 83 new), including the compromised-LLM tests, hypothesis property tests (agreement of `evaluate` with the independent oracle, monotonicity under tighter limits, totality on arbitrary JSON, hash sensitivity to every flight-relevant field), token tests (reuse, expiry, wrong hash, wrong mission, tampered capability, position mismatch, audit hygiene) and the no-alternative-route test. Coverage of `src/safety`: 93-100 % per module.

### Protocol deviations (declared)

1. **Scenario envelope decided before any hardened result**: the Tokyo evaluation scenario uses 2000 m distance from home and 2000 m segments (first tried 1000/500 m), stored in `evaluation/scenario_tokyo.json` and cited in `metrics.json`. The bundled area has points of interest 1.6 km apart and the prompt promises a 2 km radius; the first values flagged benign requests on the *baseline* tree. On architect review these wider values were **not** kept as library defaults: the defaults are 500 m / 1000 m, a conservative approximation to VLOS that the operator must verify (the EU open category requires VLOS).
2. **Controller guard bug (after the first hardened LLM run)**: ground-level `land` waypoints were rejected by the minimum-altitude rule (benign orders executed 15/20). Fixed with an explicit `ground` flag. Utility defect, not safety; everything was re-measured.
3. **Amendment accounting (after the first hardened run)**: the "speed" vector cannot be expressed in an amendment and the oracle was applied to the source mission rather than the amended waypoints, producing 30 false "reached". Speed excluded, oracle applied to the amended plan (N = 210).
4. **Oracle defect (found by the property test)**: the leg from home to the first waypoint was not checked against zones and segment limit. Corrected, and both baseline and hardened were re-run with the corrected oracle.

## Limitations

- Simulation only; the controllers are mocks or stubs. The Olympe path is guarded in the base class but never exercised here.
- Indirect injection through `situation_report` and through text in video was **not measured**: no LLM consumes those inputs in this code base (`adaptive_control` is a keyword stub). The plain-order vector needs no injection text. Injection corpora were not run.
- The agent path (LangGraph with ChatGroq) was not measured with a live model; its tools were shown to have no route to a controller.
- One model, one area, 24 orders x 3 repetitions. The LLM is not deterministic at temperature 0.3 even with a seed (cloud-hosted); rates vary by repetition (11, 15, 13 out-of-envelope plans of 24 before and 12, 15, 14 after).
- The generators of the compromised-LLM vector and the oracle were written by the same author as the envelope; the property test and the independent oracle reduce but do not remove shared blind spots.
- Operator authentication is a shared key, not an identity. Altitude is relative; no terrain, obstacles, airspace data, weather or link-loss handling. This is not a certified safety system and not compliance evidence for any regulation.
- gitleaks over all 75 commits (including merges): no findings except two reviewed false positives (an 18-character literal placeholder in two unit-test fixtures), recorded in `.gitleaksignore`.

## Lessons

1. A check whose result nothing depends on is documentation. Put the check on the only path and make the downstream object unconstructible without it.
2. Bind approval to content, not to an id: hash what the human saw, re-hash what will run.
3. Reload at the point of use. The artefact on disk is untrusted until the executor reads it.
4. Rejecting beats clipping: silent correction hides a faulty planner and breaks the link between what was approved and what flies.
5. Measure the model but do not rely on it: here the LLM produced out-of-envelope plans for about half of the unsafe orders, and every one of them would have flown.
6. Write the oracle independently, and let a property test pit it against the implementation: it found a gap in the oracle itself.
7. Keep an inventory test of call sites; it turns "no other route" from a belief into a failing test.

## Reproduce

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
python -m pytest tests/                    # 474 tests
python -m evaluation.run_baseline hardened # compromised-LLM vectors (a) and (b)
LLM_PROVIDER=ollama OLLAMA_MODEL=gpt-oss:120b-cloud python -m evaluation.run_llm hardened_run1   # vector (c)
python evaluation/make_metrics.py          # aggregate into evaluation/metrics.json
```

To reproduce the "before" numbers, export the baseline commit (`git archive <tag> | tar -x -C /tmp/baseline`), copy `evaluation/` and the Ollama provider (`src/models/llm_client.py`, `src/utils/config.py`) over it, and run the same commands there.
