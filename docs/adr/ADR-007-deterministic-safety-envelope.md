# ADR-007: Deterministic safety envelope and binding approval for LLM-planned missions

- Status: accepted
- Date: 2026-11-07

## Context

LLM-planned missions reached the (simulated) controller after only advisory validation (see [case-study](../case-study.md)). The model, its tools and the stored artefact were all inside the trust boundary.

## Decision

1. Treat LLM output as untrusted. Enforce a deterministic, fail-closed envelope (`src/safety/envelope.py`) with no LLM involvement.
2. Require a human approval bound to the SHA-256 of the canonical flight plan, delivered as a single-use expiring token; reload and re-verify at execution time.
3. Make `MissionExecutor.start` the single entry point; controllers accept only an HMAC-protected `ApprovedMission`, cannot override the guarded template methods, and check every motion command against the envelope and a recorded home.
4. Reject (never clip) out-of-envelope plans, including speed.
5. In-flight amendments: strict schema; only risk-reducing actions apply directly; new coordinates require a new mission, envelope check and approval.
6. Keep prompt-level hardening as mitigation only.

## Alternatives considered

- Keep warnings but make the LLM call `validate_mission` mandatory: still model-dependent; rejected.
- Clip values to the envelope: hides planner faults and breaks the approval-to-flight correspondence; rejected.
- Sign approvals with an asymmetric key and an external identity provider: right for production, out of proportion for a simulation prototype; listed as a next step.

## Consequences

- `BaseDrone.execute_mission/move_to/take_off` changed from abstract methods to guarded template methods (`_do_*` hooks); existing tests were rewritten.
- A restart invalidates all outstanding approvals (per-process HMAC key and in-memory grants).
- The envelope defaults (500 m radius and 1000 m segments as a conservative approximation to VLOS that the operator must verify, 20 min endurance with 30 % reserve) are prototype values; deployments must configure them. The Tokyo evaluation scenario uses a wider, explicit configuration (`evaluation/scenario_tokyo.json`).
- Residual risks (operator error, in-process compromise, shared-key authentication) are documented in [safety-envelope.md](../safety-envelope.md) and [threat-model.md](../threat-model.md).
