#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persistent SQLite-backed store for chat session context.

Replaces the previous in-memory dict so that contextual chat sessions
(image analysis + chat history) survive container restarts. The public
API mirrors the old dict semantics closely enough for a drop-in
replacement inside ``ChatService``.

Concurrency model
-----------------
SQLite is opened with one connection per thread (``threading.local``).
Each connection enables WAL journaling so multiple readers and a single
writer can progress concurrently. A module-level ``threading.Lock``
serialises only the write paths that perform compound work
(read-modify-write on JSON columns, LRU enforcement, cleanup) to keep
the queries race-free without blocking pure reads.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


# Columns persisted as JSON blobs. Lookups against this set drive the
# automatic ser/deser between Python objects and TEXT columns.
_JSON_FIELDS: frozenset[str] = frozenset(
    {"geographic_analysis", "yolo_detection", "chat_history"}
)

# Columns the caller is allowed to write through ``store`` /
# ``update_field``. Whitelisting prevents accidental SQL injection from
# arbitrary keyword arguments.
_WRITABLE_FIELDS: frozenset[str] = frozenset(
    {
        "image_filename",
        "geographic_analysis",
        "yolo_detection",
        "encoded_image",
        "image_format",
        "chat_history",
    }
)

# Max size for encoded_image field (base64 string).
# Drone 4K imagery base64-encoded is ~10MB; cap at 5MB to:
#   - prevent disk-full scenarios with MAX_SESSIONS=50 (~250MB worst case)
#   - keep individual rows under SQLite default page-cache friendly size
MAX_ENCODED_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


class ChatSessionStore:
    """SQLite-backed persistent store for chat sessions.

    The schema is intentionally narrow: one row per ``session_id`` with
    JSON-encoded payload columns for the structured analysis blobs and
    the chat history. ``created_at`` and ``updated_at`` are stored as
    UNIX timestamps (REAL) so TTL and LRU queries reduce to plain
    arithmetic.

    Parameters
    ----------
    db_path:
        Filesystem path of the SQLite database. The parent directory is
        created on initialisation if missing.
    """

    _SCHEMA: str = """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            image_filename TEXT,
            geographic_analysis TEXT,
            yolo_detection TEXT,
            encoded_image TEXT,
            image_format TEXT,
            chat_history TEXT NOT NULL DEFAULT '[]'
        );
    """

    _INDEX: str = (
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at "
        "ON chat_sessions(updated_at);"
    )

    def __init__(self, db_path: str) -> None:
        self.db_path = os.fspath(db_path)
        parent = os.path.dirname(os.path.abspath(self.db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)

        # Per-thread connection cache. SQLite forbids sharing a
        # connection across threads unless ``check_same_thread=False``
        # is explicitly set, which we deliberately avoid in favour of
        # one connection per thread (cheaper than a global lock).
        self._local = threading.local()

        # Guards compound write operations. Pure reads do not take it.
        self._write_lock = threading.Lock()

        # Initialise schema once via the bootstrap connection. The
        # connection is left for reuse by the calling thread.
        with self._write_lock:
            conn = self._connection()
            conn.executescript(self._SCHEMA)
            conn.execute(self._INDEX)
            conn.commit()
        logger.info("ChatSessionStore initialised at %s", self.db_path)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def _connection(self) -> sqlite3.Connection:
        """Return the connection bound to the current thread.

        The first call from a thread opens the database, enables WAL
        journaling and ``foreign_keys``, and registers a row factory so
        rows are returned as ``sqlite3.Row`` (dict-like access).
        """
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                self.db_path,
                isolation_level=None,  # autocommit; we manage transactions explicitly
                timeout=30.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            self._local.conn = conn
        return conn

    def close(self) -> None:
        """Close the connection bound to the current thread, if any.

        Mostly useful in tests to release file handles before tearing
        down a temporary database directory.
        """
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _encode(field: str, value: Any) -> Any:
        """Serialise ``value`` to TEXT if the column stores JSON."""
        if value is None:
            return None
        if field in _JSON_FIELDS:
            return json.dumps(value, ensure_ascii=False)
        return value

    @staticmethod
    def _decode(field: str, value: Any) -> Any:
        """Deserialise TEXT back to a Python object for JSON columns."""
        if value is None:
            return None
        if field in _JSON_FIELDS:
            # Defensive: a malformed payload (e.g. legacy row) should
            # not crash the chat flow. Log and surface an empty default.
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(
                    "Corrupted JSON in column %s; returning empty default", field
                )
                return [] if field == "chat_history" else {}
        return value

    @classmethod
    def _row_to_dict(cls, row: sqlite3.Row | None) -> dict[str, Any] | None:
        """Convert a ``sqlite3.Row`` into the legacy dict shape.

        The legacy in-memory dict exposed a ``timestamp`` ISO string
        used by callers building chat prompts; we synthesise it from
        ``created_at`` to keep callers untouched.
        """
        if row is None:
            return None
        keys = row.keys()
        out: dict[str, Any] = {}
        for key in keys:
            out[key] = cls._decode(key, row[key])
        # Backwards-compatible alias used by ChatService prompts.
        if "created_at" in out and out["created_at"] is not None:
            try:
                out["timestamp"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(float(out["created_at"]))
                )
            except (TypeError, ValueError):
                out["timestamp"] = None
        return out

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def store(self, session_id: str, **fields: Any) -> None:
        """Insert or update a session row.

        Unknown keyword arguments are rejected to keep the schema
        contract explicit. Fields not provided on update keep their
        previous value (UPSERT semantics, not full overwrite).

        Oversized ``encoded_image`` fields (exceeding MAX_ENCODED_IMAGE_BYTES)
        are dropped with a warning to prevent disk-full scenarios.
        """
        unknown = set(fields).difference(_WRITABLE_FIELDS)
        if unknown:
            raise ValueError(f"Unknown fields for ChatSessionStore.store: {sorted(unknown)}")

        # Validate encoded_image size. If oversized, drop the field and log.
        if "encoded_image" in fields and fields["encoded_image"] is not None:
            img_data = fields["encoded_image"]
            img_size = (
                len(img_data.encode("utf-8"))
                if isinstance(img_data, str)
                else len(img_data)
            )
            if img_size > MAX_ENCODED_IMAGE_BYTES:
                logger.warning(
                    "encoded_image exceeds %d bytes (got %d), dropping field for session %s",
                    MAX_ENCODED_IMAGE_BYTES,
                    img_size,
                    session_id,
                )
                fields["encoded_image"] = None

        now = time.time()
        encoded = {k: self._encode(k, v) for k, v in fields.items()}

        with self._write_lock:
            conn = self._connection()
            existing = conn.execute(
                "SELECT 1 FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if existing is None:
                # Build full INSERT, defaulting unspecified writable
                # fields to NULL (or '[]' for chat_history via column
                # default). Placeholders mirror the column order.
                columns = ["session_id", "created_at", "updated_at"] + list(encoded.keys())
                placeholders = ",".join("?" * len(columns))
                values: list[Any] = [session_id, now, now] + list(encoded.values())
                conn.execute(
                    f"INSERT INTO chat_sessions ({','.join(columns)}) VALUES ({placeholders})",
                    values,
                )
            else:
                # Patch only the supplied fields plus updated_at. Avoid
                # rewriting columns the caller did not mention.
                set_clause = ", ".join(f"{name} = ?" for name in encoded.keys())
                set_clause = (
                    f"updated_at = ?{', ' + set_clause if set_clause else ''}"
                )
                values = [now] + list(encoded.values()) + [session_id]
                conn.execute(
                    f"UPDATE chat_sessions SET {set_clause} WHERE session_id = ?",
                    values,
                )
            conn.commit()
        logger.debug("Session %s stored (fields=%s)", session_id, sorted(fields))

    def get(self, session_id: str) -> dict[str, Any] | None:
        """Return the session row as a dict, or ``None`` if missing."""
        conn = self._connection()
        row = conn.execute(
            "SELECT * FROM chat_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return self._row_to_dict(row)

    def delete(self, session_id: str) -> bool:
        """Remove a session. Returns True if a row was deleted."""
        with self._write_lock:
            conn = self._connection()
            cur = conn.execute(
                "DELETE FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def cleanup_expired(self, ttl_hours: float) -> int:
        """Delete sessions whose last activity exceeds ttl_hours.

        SEMANTICS: TTL is measured against `updated_at` (last write), NOT
        `created_at`. Active conversations (with frequent appends) extend
        their lifetime indefinitely. Inactive sessions expire after
        ttl_hours of silence.

        This differs from the pre-SQLite in-memory dict implementation,
        which used `created_at` (fixed expiration from session start).

        Args:
            ttl_hours: Inactivity threshold in hours. Sessions with
                updated_at < (now - ttl_hours) are deleted.

        Returns:
            Number of sessions deleted.
        """
        cutoff = time.time() - ttl_hours * 3600.0
        with self._write_lock:
            conn = self._connection()
            cur = conn.execute(
                "DELETE FROM chat_sessions WHERE updated_at < ?",
                (cutoff,),
            )
            conn.commit()
            removed = cur.rowcount
        if removed:
            logger.info("Cleanup removed %d expired chat session(s)", removed)
        return removed

    def enforce_max_sessions(self, max_n: int) -> int:
        """Trim the oldest sessions when the count exceeds ``max_n``.

        ``max_n`` must be a positive integer. The trimming policy is
        LRU on ``updated_at`` (oldest first), matching the legacy
        in-memory eviction.
        """
        if max_n <= 0:
            raise ValueError("max_n must be positive")

        with self._write_lock:
            conn = self._connection()
            total = conn.execute(
                "SELECT COUNT(*) FROM chat_sessions"
            ).fetchone()[0]
            if total <= max_n:
                return 0
            to_remove = total - max_n
            cur = conn.execute(
                """
                DELETE FROM chat_sessions
                WHERE session_id IN (
                    SELECT session_id FROM chat_sessions
                    ORDER BY updated_at ASC
                    LIMIT ?
                )
                """,
                (to_remove,),
            )
            conn.commit()
            removed = cur.rowcount
        logger.info("LRU enforcement removed %d session(s) (max=%d)", removed, max_n)
        return removed

    def count(self) -> int:
        """Return the total number of stored sessions."""
        conn = self._connection()
        row = conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()
        return int(row[0]) if row is not None else 0

    def update_field(self, session_id: str, field: str, value: Any) -> bool:
        """Atomically replace a single column for an existing session.

        Used for chat-history append flows where the caller has read
        the current list, mutated it, and wants to write it back. The
        compound read-modify-write is the caller's responsibility; this
        method only guarantees the write itself is atomic and bumps
        ``updated_at``.

        Returns ``True`` if a row was updated, ``False`` if the session
        does not exist.
        """
        if field not in _WRITABLE_FIELDS:
            raise ValueError(f"Field {field!r} is not writable")
        encoded = self._encode(field, value)
        now = time.time()
        with self._write_lock:
            conn = self._connection()
            cur = conn.execute(
                f"UPDATE chat_sessions SET {field} = ?, updated_at = ? WHERE session_id = ?",
                (encoded, now, session_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def __contains__(self, session_id: object) -> bool:
        """Allow ``session_id in store`` for ergonomic checks."""
        if not isinstance(session_id, str):
            return False
        conn = self._connection()
        row = conn.execute(
            "SELECT 1 FROM chat_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return row is not None
