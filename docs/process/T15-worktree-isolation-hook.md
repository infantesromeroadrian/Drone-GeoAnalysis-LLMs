# T15: Worktree Isolation Enforcer Hook

**Ticket**: T15  
**Status**: Closed  
**Date**: 2026-04-25  
**Author**: @devops (ARCA)

## Background

Three consecutive incidents occurred in a single session where agents with
`isolation:worktree` executed `git commit` directly on the main project repo
instead of their assigned worktree path:

| Commit | Agent | Violation |
|---|---|---|
| `b26d8b0` | `@frontend-ai` | Committed from main repo, not worktree |
| `26e011a` | `@ai-engineer` | Committed from main repo, not worktree |
| `aa2427d` | `@python-specialist` | Committed from main repo, not worktree |

No existing hook blocked any of these operations. Post-facto manual audit was
required for all three. Ticket T15 was raised to prevent reincidence.

## Root Cause

The ARCA hook ecosystem had no mechanism to detect and block git write
operations (commit, add) executed from the main repo when the active agent
was supposed to be isolated in a worktree. The `git-commit-validator.sh` hook
validates message format but not the working directory.

## Solution

A new global hook was installed at:

```
~/.claude/hooks/worktree-isolation-enforcer.sh
```

It fires on `PreToolUse:Bash` and blocks `git commit` / `git add` when:

1. The command is a git write operation (commit or add).
2. The `cwd` is inside a known ARCA project root (Work, Personal, HTB, Kaggle).
3. The `cwd` does NOT contain `/.claude/worktrees/` — meaning the agent is
   operating from the main repo, not its assigned worktree.

### Detection logic

```
cwd contains /.claude/worktrees/  →  ALLOW (in worktree, correct)
cwd is outside known project roots →  ALLOW (unrelated repo, no false positive)
cwd is in project root, not worktree → BLOCK or DRY-RUN WARNING
```

The hook does NOT require an `isolation:worktree` field in the JSON payload
(that metadata is not forwarded by the Claude Code runtime to PreToolUse:Bash
hooks). The worktree path pattern is sufficient for detection.

### Technical constraints discovered

During implementation, two deviations from the original ticket spec were found:

1. **Hook input JSON format**: The actual field is `tool_input.command`
   (not `.input.command` as written in T15). Confirmed by reading existing
   hooks `block-dangerous.sh` and `git-commit-validator.sh`.

2. **No `agent.isolation` field**: The Claude Code runtime does NOT forward
   agent isolation metadata to `PreToolUse:Bash` hooks. The detection strategy
   was changed to infer isolation violation from the `cwd` path pattern alone,
   which is functionally equivalent for the target violation type.

## Installation

The hook is registered in `~/.claude/settings.json` under `hooks.PreToolUse`
(Bash matcher), immediately after `git-commit-validator.sh`.

## Modes

| Mode | Activation | Behavior |
|---|---|---|
| DRY-RUN (default) | `ARCA_WORKTREE_ISOLATION_ENFORCE` unset | Logs + warns, exits 0 |
| ENFORCE | `export ARCA_WORKTREE_ISOLATION_ENFORCE=1` | Logs + blocks with exit 2 |

To activate hard enforcement globally:

```bash
echo 'export ARCA_WORKTREE_ISOLATION_ENFORCE=1' >> ~/.zshrc
```

## Bypass

For legitimate main-repo commits (e.g., post-merge hotfix, CLAUDE.md update):

```bash
echo "reason" > /tmp/arca-worktree-bypass
# then retry the git operation
```

The bypass is single-use (atomically consumed) and logged.

## Test results (2026-04-25)

| Case | CWD | Command | ENFORCE | Expected | Result |
|---|---|---|---|---|---|
| 1 | `.../.claude/worktrees/agent-abc123` | `git commit -m "..."` | 1 | ALLOW (exit 0) | PASS |
| 2 | `.../Drone-GeoAnalysis-LLMs` (main) | `git commit -m "..."` | 1 | BLOCK (exit 2) | PASS |
| 3 | `/tmp/some-unrelated-project` | `git commit -m "..."` | 1 | ALLOW (exit 0) | PASS |
| 4 | `.../.claude/worktrees/agent-abc123` | `git status` | 1 | ALLOW (exit 0) | PASS |
| Extra | `.../Drone-GeoAnalysis-LLMs` (main) | `git add ...` | 1 | BLOCK (exit 2) | PASS |
| DRY | `.../Drone-GeoAnalysis-LLMs` (main) | `git commit -m "..."` | unset | DRY-RUN (exit 0) | PASS |

## Replicating in other projects / teams

Any ARCA-based team can adopt this hook by:

1. Copying `~/.claude/hooks/worktree-isolation-enforcer.sh` to their global
   hooks directory.
2. Updating the `KNOWN_ROOTS` array in the script to match their project paths.
3. Registering in their `~/.claude/settings.json`:
   ```json
   {
     "matcher": "Bash",
     "hooks": [
       {
         "type": "command",
         "command": "/path/to/hooks/worktree-isolation-enforcer.sh",
         "timeout": 5
       }
     ]
   }
   ```
4. Activating enforcement: `export ARCA_WORKTREE_ISOLATION_ENFORCE=1`.

## Audit log

Violations are written to:
```
~/.claude/logs/worktree-isolation-violations.jsonl
```

Format:
```json
{
  "ts": "2026-04-25T21:30:00Z",
  "type": "worktree_isolation_violation",
  "command": "git commit -m \"...\"",
  "cwd": "/home/.../Drone-GeoAnalysis-LLMs",
  "session": "session-uuid",
  "mode": "enforce"
}
```

## References

- `~/.claude/hooks/worktree-isolation-enforcer.sh` — hook implementation
- `~/.claude/hooks/README.md` — hook inventory and format documentation
- `~/.claude/settings.json` — hook registration (PreToolUse:Bash section)
- CLAUDE.md §Git Worktrees — worktree policy and isolation rules
