# ARCA Agent Workflow Guide

This document describes the expected workflow for ARCA-orchestrated agents
working on this codebase. It is referenced by the worktree-isolation-enforcer
hook (see [T15 doc](T15-worktree-isolation-hook.md)) and forms the contract
between the orchestrator and specialist agents.

## Core invariant

> **Every code-producing agent (`isolation: worktree`) MUST commit inside
> its assigned worktree path, NEVER on the main repo.**

The orchestrator (ARCA) creates a fresh git worktree for each delegated task
and the agent receives a `worktreePath` parameter. All file edits, `git add`,
and `git commit` operations must use that path.

## Why this matters

1. **Parallel safety**: multiple agents can work on the same codebase
   simultaneously without conflicting on the main working tree.
2. **Atomic merges**: each worktree corresponds to a single logical task,
   merged via `git merge --no-ff` with a descriptive merge commit.
3. **Audit trail**: every change is traceable to the agent + worktree that
   produced it.
4. **Rollback granularity**: a problem found post-merge can be reverted
   surgically to one merge commit, not a tangle of direct main commits.
5. **Hook enforcement**: the `worktree-isolation-enforcer.sh` hook
   (PreToolUse:Bash) blocks `git commit` and `git add` from main when the
   active agent has `isolation: worktree`.

## What violates the invariant

| Bad pattern | Why bad | Fix |
|---|---|---|
| `cd <main_repo> && git commit ...` | Main is for merges only | `cd <worktree_path> && git commit ...` |
| `git commit -am ...` from main | Same | Same |
| Touching `<main_repo>/<file>` directly | File mods belong in worktree | `cd <worktree_path>` first |
| Saying "the worktree was empty so I worked on main" | False — worktrees are git worktrees with full repo | Use `git status` inside `<worktree_path>` to verify |

## What the hook does

When `ARCA_WORKTREE_ISOLATION_ENFORCE=1` is set:

- A `git commit` or `git add` invoked from the main repo path
- By an agent whose definition has `isolation: worktree`
- Returns exit code 2, blocking the operation
- Stderr explains the violation and how to fix it

When `ARCA_WORKTREE_ISOLATION_ENFORCE` is unset or `0`:

- Hook runs in DRY-RUN: logs the violation but allows execution
- Used during initial rollout to gather telemetry without breaking flows

## Agent checklist before committing

```bash
# 1. Verify you're in the worktree, not main:
pwd  # should contain .claude/worktrees/agent-<id>

# 2. Verify git status shows your changes (not main's):
git status

# 3. Stage and commit:
git add <specific files>
git commit -m "<conventional commit format>"

# 4. Confirm:
git log -1 --oneline
```

## Orchestrator (ARCA) checklist after agent reports

```bash
# 1. Verify the worktree branch has the expected commit:
git log worktree-agent-<id> --oneline -3

# 2. Merge to main with --no-ff:
cd <main_repo>
git merge --no-ff worktree-agent-<id> -m "Merge <task>: <description>"

# 3. Cleanup:
git worktree unlock .claude/worktrees/agent-<id>
git worktree remove .claude/worktrees/agent-<id> --force
git branch -D worktree-agent-<id>
```

## Common mistakes from the recent session (lessons learned)

During the audit session of 2026-04-25, four incidents occurred:

1. **`b26d8b0`** (`@python-specialist`): committed geo_correlator changes
   directly to main. Audited post-facto, APPROVE.
2. **`26e011a`** (`@ai-engineer`): committed chat SQLite migration directly.
   Verbalized "the worktree didn't have the source code" — false. Audited
   post-facto, APPROVE.
3. **`aa2427d`** (`@frontend-ai`): committed banner UI directly. B1
   network-error bug found in audit, fixed in `56e942f`.
4. **`e165e4e`** (`@docs-writer`): committed Status.md directly.

After the T15 hook was activated in DRY-RUN, the next 4 worktrees in P2
(T2+T3, A2+A3+A4, T9+T11, T5+T7+T8) had ZERO incidents. The hook works
when respected.

## Escalation

If you genuinely need to commit on main (rare cases like trivial post-merge
fixes <5 lines), either:

- Invoke the agent without `isolation: worktree`
- Or escalate to `@architect-ai` with justification
- Or set `ARCA_WORKTREE_ISOLATION_ENFORCE=0` temporarily and document the
  bypass in the commit message

## Reference

- [T15 hook implementation](T15-worktree-isolation-hook.md)
- [ARCA CLAUDE.md global config](~/.claude/CLAUDE.md)
- Hook script: `~/.claude/hooks/worktree-isolation-enforcer.sh`
