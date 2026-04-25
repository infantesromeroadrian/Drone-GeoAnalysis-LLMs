# ADR-006: Frontend testing framework deferred

**Status:** Accepted (deferred decision)
**Date:** 2026-04-25
**Decision makers:** Adrian Infantes (CTO)

## Context

The project's frontend is vanilla JavaScript ES modules (~850 LOC across
6 files). Backend has 91 tests with 56.13% coverage and an ARCA F5 policy
gate of 55% (incremental to 80% via ADR-001).

**Frontend has zero automated tests.** Code-critic flagged this as
structural debt (advertencia A7 in lote 2 audit, commit aa2427d).

The detect_changes flow alone has 5 logical branches (stub error / network
error / generic error / undefined response / success) which today rely on
manual browser testing only.

## Decision

**Defer adoption of a JS testing framework to a future sprint.** Document
the rationale and pre-conditions for revisiting:

### Pre-conditions to revisit (any of):

1. Frontend grows beyond 1500 LOC (~80% increase from today)
2. A frontend bug ships to production that automated tests would have caught
3. The frontend stack migrates to a framework (React, Vue, Solid) that
   bundles a test runner natively
4. Coverage gate of 80% (ARCA F5 final) blocks deploy and frontend lack
   of tests is the dragging factor

### When revisited, evaluation criteria:

1. **Vitest + happy-dom** (likely winner): ESM-native, vite-based, jest-compatible API
2. **Jest + jsdom**: mature ecosystem, ESM friction
3. **Playwright E2E from Python**: avoids Node.js but slow and not unit-coverage

## Why deferred today

1. **Stack purity**: adding Node.js + npm to a Python-pure repo is significant
   architectural weight (CI matrix doubles, maintainer cognitive load)
2. **Frequency of change**: frontend has been touched ~10 times in the
   recent session. Backend changes 5x more often.
3. **Recent JS changes have backend test coverage indirectly**: e.g.,
   `correlation_not_implemented` flow tested via `test_geo_correlator.py`
   on the Python side; the JS just relays the dict.
4. **Cost of Vitest setup vs. value today**: ~4-8 hours of setup +
   ongoing maintenance overhead. Hard to justify on a 850-LOC codebase
   with low change frequency.

## What we DO have today (manual mitigation)

- Backend integration tests cover the contract that frontend consumes
  (Flask test client could be expanded — TODO if becomes important)
- AST syntax check in CI catches JS parse errors
- Manual browser testing during PR review for any frontend change

## Consequences

**Positive:**
- 0 new infrastructure today, no Node.js in repo
- Backend tests remain authoritative for contracts

**Negative:**
- Frontend regressions caught only manually
- A7 remains open as known structural debt
- The ARCA F5 80% gate cannot be reached for full-stack coverage without
  this resolved

**Mitigation while deferred:**
- All new frontend changes require manual browser test in PR description
- Critical UX (banner, error handling) tested adversarially in code-critic
  ciclo 1/2 audits
- Backend Flask test client tests could be added to validate JSON
  contract changes that frontend depends on (cheap, no Node.js required)

## Alternatives considered

| Option | Effort | Value today | Decision |
|---|---|---|---|
| A. Vitest + happy-dom | 4-8h setup, ongoing | Low (850 LOC, slow change) | Deferred |
| B. Jest + jsdom | 8-12h setup | Same as A | Rejected (worse than A) |
| C. Playwright E2E (Python) | 12-20h setup | Medium (covers full flow) | Future consideration |
| D. Defer + document | 0 | High (no debt accumulation hidden) | **Accepted** |

## When to revisit

Quarterly review or upon any pre-condition trigger. Owner: CTO (Adrian Infantes).
Track in Status.md as open structural debt.

## Related

- Code-critic ciclo 1 audit on commit aa2427d (A7 advertencia)
- ADR-001: Coverage incremental plan (constrains the F5 gate path)
