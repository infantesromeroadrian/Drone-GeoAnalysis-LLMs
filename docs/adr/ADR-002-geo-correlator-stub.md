# ADR-002: GeoCorrelator marked as stub / not implemented

**Status:** Accepted
**Date:** 2026-04-25

## Context

`src/geo/geo_correlator.py` was returning hardcoded `correlation_confidence=0.85`
and inventented coordinate corrections (`+0.0001 / -0.0002`). This is dangerous
in production — operators may trust false data.

## Decision

Mark all hardcoded-value methods as `NotImplementedError`. Surface the lack of
implementation explicitly in the public API response.

## Real implementation requires
- Sentinel-2 Hub API or Google Earth Engine API integration
- OpenCV-based image registration (ORB, SIFT, or phase correlation)
- Validation against ground truth GCPs
- Estimated effort: 2-3 weeks

## Consequences
- Frontend `geo` panel must handle `error: "correlation_not_implemented"` gracefully
- Operators alerted via UI banner that module is offline
