# ADR-005: Chat session TTL based on last activity (updated_at)

**Status:** Accepted  
**Date:** 2026-04-25

## Context

Pre-SQLite implementation (in-memory dict) used `timestamp = datetime.now()` set ONLY at `store_analysis_context`. Sessions expired 2h after creation regardless of activity.

The SQLite migration (commit 26e011a) changed the schema to track both `created_at` and `updated_at`, with `cleanup_expired` comparing against `updated_at`. This was an undocumented semantic change.

## Decision

Confirm and document: TTL is measured from last activity (`updated_at`), not creation. Active conversations remain alive while operators continue chatting.

## Consequences

**Positive:**
- Long-running operator analyses are not interrupted by arbitrary timeouts
- Aligns with user expectation ("chat is alive while I'm using it")

**Negative:**
- A bursty conversation can keep a session alive for hours/days
- Combined with MAX_SESSIONS=50 LRU enforcement, very-active sessions squeeze out moderate-active ones

## Alternatives considered

- **Reset clock per `created_at`**: simpler but interrupts long workflows
- **Hybrid (cap at created_at + 24h)**: more complex, limited operational benefit

## Validation

`tests/services_test/test_chat_service.py::test_cleanup_expired_removes_old_sessions` uses `updated_at`-based fixture data, confirming the contract.
