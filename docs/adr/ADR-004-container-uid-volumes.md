# ADR-004: Container UID fixed at 1000 for volume compatibility

**Status:** Accepted
**Date:** 2026-04-25
**Ticket:** T10 (lote 2 audit — code-critic)

## Context

Docker container user `appuser` was created without an explicit UID. In CI runners
and host systems where the host UID differs from the default assigned container UID,
the volume mount `./data:/app/data` (used by `ChatSessionStore` for SQLite persistence)
fails with `permission denied` because the container user cannot write to host-owned
files. The same issue affects any future volume-mounted directory owned by a host user
with a non-matching UID.

Additionally, `./data:/app/data` was absent from `docker-compose.yml` (expected since
commit 26e011a) and SQLite database files were not excluded from the Docker build context,
risking accidental image bloat with live production data.

## Decision

1. Pin `appuser` to UID 1000 (`useradd --uid 1000`). UID 1000 is the default first
   non-root user on Debian/Ubuntu and most Linux developer workstations, making it the
   least-surprise default across team environments.
2. Pre-create `/app/data` at build time and include it in the `chown -R appuser:appuser /app`
   chain so directory ownership is correct regardless of whether the host-side `./data`
   directory exists before first `docker-compose up`.
3. Add `./data:/app/data` volume mount to `docker-compose.yml` so SQLite state persists
   across container restarts.
4. Exclude `data/*.db`, `data/*.db-shm`, `data/*.db-wal` from `.dockerignore` to prevent
   development databases from being baked into production images.

## Consequences

**Positive:**
- Volume mounts work consistently on hosts with UID 1000 (the overwhelming majority of
  Linux developer workstations and standard GitHub Actions / GitLab CI runners).
- Pre-created `/app/data` with correct ownership avoids a first-run race where the
  container tries to write before the host directory is chowned.
- SQLite databases are never accidentally shipped inside the image layer.

**Negative:**
- Hosts where the operator user has a UID other than 1000 (e.g. multi-user servers,
  some hardened CI runners, or root-only environments) will still encounter permission
  issues. Mitigations: run with `--user $(id -u):$(id -g)` override, or configure
  user namespace remapping at the Docker daemon level.
- SELinux / AppArmor on hardened systems may require additional volume context labels
  (`:z` or `:Z` suffix on the bind mount). Documented in runbook, deferred as out of
  scope for this fix.

## Alternatives considered

- **Rootless container with user namespace remapping (--userns-remap):** More correct
  in theory — container UID 0 maps to an unprivileged host UID. Adds daemon-level
  configuration complexity and is not portable across all CI providers. Deferred.
- **Init container / entrypoint script that chowns `/app/data` at runtime:** Works but
  requires root or `CAP_CHOWN` at startup, complicates `docker-compose`, and adds
  latency. Rejected in favour of the build-time solution.
- **Run application as root:** Rejected. Violates security policy — no production
  container runs as root without explicit justification.
- **Named volume instead of bind mount:** Would fix the UID mismatch but sacrifices
  direct host access to SQLite files for backup and inspection. Deferred.
