# ADR-003: DJIDroneController marked as simulation-only stub

**Status:** Accepted
**Date:** 2026-04-25

## Context

`src/drones/dji_controller.py` was presenting itself as a multi-vendor drone
controller alongside `ParrotAnafiController`. In reality, no DJI SDK is integrated.
All methods are simulation stubs. This is misleading marketing for the platform.

## Decision

Refactor `__init__` to require `simulation_mode=True` explicitly. Default
instantiation raises `NotImplementedError`. Each public method also guards
against accidental real-mode invocation.

## Real implementation requires
- DJI Mobile SDK (Android/iOS) — not Python-native
- DJI Onboard SDK (limited drone models with payload computer)
- Estimated effort: 4-6 weeks (depends on DJI SDK access tier)

## Consequences
- Existing tests must pass `simulation_mode=True`
- Documentation must clarify DJI is "simulation only" until integration ships
- Frontend should not offer DJI as production option
