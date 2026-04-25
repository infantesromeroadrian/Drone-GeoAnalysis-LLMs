# ADR-001: Incremental Coverage Gate Plan

**Status:** Accepted
**Date:** 2026-04-25
**Decision makers:** Adrian Infantes (CTO)

## Context

Project has 337 tests but real coverage measured at 56.13% — far from the ARCA policy of >=80% required for production deployment (F5 gate).

Major uncovered modules:
- `src/services/chat_service.py`: 0% (142 stmts)
- `src/models/mission_agent.py`: 5% (185 stmts)
- `src/main.py`: 0% (141 stmts)
- `src/controllers/*`: 35-52%

## Decision

Adopt incremental coverage gate strategy:

| Sprint | Target | Floor (CI gate) |
|---|---|---|
| Current | 55% | 55% |
| +1 sprint | 60% | 60% |
| +2 sprints | 65% | 65% |
| +3 sprints | 70% | 70% |
| +4 sprints | 75% | 75% |
| +5 sprints | **80%** (ARCA F5 policy) | 80% |

CI gate raised by +5% each sprint. PRs that drop below the floor are blocked. PRs that raise coverage are encouraged.

## Priority order for new tests (highest LOC impact)

1. `chat_service.py` — no hardware dep, mock LLM client (+114 stmts)
2. `mission_agent.py` — mock LangGraph state (+139 stmts)
3. Controllers via Flask test client (+200 stmts combined)
4. `cartography_manager.py` — file fixtures (+57 stmts)
5. `geo_analyzer.py` — mock OpenAI (+87 stmts)

## Consequences

**Positive:**
- No artificial omit of hardware-dependent files (no hidden debt).
- Forces real test writing every sprint.
- Coverage drift caught immediately by floor.

**Negative:**
- Deploy to production blocked until 80% reached (ARCA F5).
- Sprint capacity must allocate ~1-2 days/sprint to coverage debt.

## Tracking

Coverage tracked in CI report. Each sprint planning must include explicit coverage delta target.
