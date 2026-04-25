#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the SQLite-backed chat session store.

These tests intentionally exercise :class:`ChatSessionStore` directly
rather than going through ``ChatService`` so we do not require an LLM
client. The store is the contract the rest of the chat flow depends on
for persistence; correctness here is what makes the migration safe.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest


def _load_chat_session_store():
    """Load ``chat_session_store`` directly from its file path.

    Importing through ``src.services.chat_session_store`` would trigger
    ``src/services/__init__.py``, which transitively imports heavy deps
    (cv2, ultralytics, torch) the store does not need. The store is
    stdlib-only by design and these tests assert exactly that — so we
    bypass the package init and load the module from disk.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir))
    module_path = os.path.join(project_root, "src", "services", "chat_session_store.py")
    spec = importlib.util.spec_from_file_location(
        "chat_session_store_under_test", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["chat_session_store_under_test"] = module
    spec.loader.exec_module(module)
    return module


_store_module = _load_chat_session_store()
ChatSessionStore = _store_module.ChatSessionStore


@pytest.fixture
def db_path(tmp_path) -> str:
    """Provide a tmp SQLite path that is fresh for each test."""
    return str(tmp_path / "chat_sessions.db")


@pytest.fixture
def store(db_path: str) -> ChatSessionStore:
    """Construct a store backed by the per-test temporary database."""
    inst = ChatSessionStore(db_path)
    yield inst
    inst.close()


# ----------------------------------------------------------------------
# Basic CRUD
# ----------------------------------------------------------------------
def test_store_and_get_session(store: ChatSessionStore) -> None:
    """A stored session round-trips through SQLite without losing data."""
    payload = {
        "image_filename": "drone_001.jpg",
        "geographic_analysis": {"country": "España", "confidence": 0.85},
        "yolo_detection": {"total_objects": 3, "object_summary": {"car": 2, "tree": 1}},
        "encoded_image": "base64data",
        "image_format": "jpeg",
        "chat_history": [],
    }
    store.store("session-1", **payload)

    fetched = store.get("session-1")
    assert fetched is not None
    assert fetched["image_filename"] == "drone_001.jpg"
    assert fetched["geographic_analysis"] == {"country": "España", "confidence": 0.85}
    assert fetched["yolo_detection"]["total_objects"] == 3
    assert fetched["chat_history"] == []
    # The legacy alias used by ChatService prompts must be present.
    assert "timestamp" in fetched and fetched["timestamp"] is not None


def test_get_returns_none_for_unknown(store: ChatSessionStore) -> None:
    """Unknown ``session_id`` must return ``None`` (not raise)."""
    assert store.get("does-not-exist") is None
    assert "does-not-exist" not in store


# ----------------------------------------------------------------------
# Persistence across instances — the whole point of the migration
# ----------------------------------------------------------------------
def test_chat_history_persisted_across_instances(db_path: str) -> None:
    """A new store instance must read what the previous one wrote.

    This emulates a container restart: open store, write, close,
    reopen, expect the data to be intact (and the history
    appended-via-update_field to persist as a real list, not a string).
    """
    first = ChatSessionStore(db_path)
    first.store(
        "session-restart",
        image_filename="img.jpg",
        geographic_analysis={"country": "France"},
        yolo_detection={"total_objects": 1},
        chat_history=[],
    )
    first.update_field(
        "session-restart",
        "chat_history",
        [
            {"question": "Q1", "response": "A1", "timestamp": "2026-04-25T10:00:00"},
            {"question": "Q2", "response": "A2", "timestamp": "2026-04-25T10:01:00"},
        ],
    )
    first.close()

    second = ChatSessionStore(db_path)
    try:
        fetched = second.get("session-restart")
        assert fetched is not None
        assert fetched["geographic_analysis"] == {"country": "France"}
        history = fetched["chat_history"]
        assert isinstance(history, list)
        assert len(history) == 2
        assert history[0]["question"] == "Q1"
        assert history[1]["response"] == "A2"
    finally:
        second.close()


# ----------------------------------------------------------------------
# TTL cleanup
# ----------------------------------------------------------------------
def test_cleanup_expired_removes_old_sessions(store: ChatSessionStore) -> None:
    """Sessions older than ``ttl_hours`` are deleted; recent ones survive."""
    store.store("old", image_filename="o.jpg", geographic_analysis={}, yolo_detection={})
    store.store("new", image_filename="n.jpg", geographic_analysis={}, yolo_detection={})

    # Backdate ``old`` past the TTL threshold by writing directly. We
    # bypass the public API on purpose: the goal here is to simulate
    # a row whose ``updated_at`` is genuinely in the past.
    conn = store._connection()
    past = time.time() - 3 * 3600  # 3 hours ago
    conn.execute(
        "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
        (past, "old"),
    )
    conn.commit()

    removed = store.cleanup_expired(ttl_hours=2.0)

    assert removed == 1
    assert store.get("old") is None
    assert store.get("new") is not None


# ----------------------------------------------------------------------
# LRU enforcement
# ----------------------------------------------------------------------
def test_enforce_max_sessions_removes_oldest(store: ChatSessionStore) -> None:
    """When count > max_n, the oldest sessions (by updated_at) are evicted."""
    # Insert five sessions with strictly increasing timestamps so the
    # ordering under LRU is unambiguous.
    for idx in range(5):
        store.store(
            f"sess-{idx}",
            image_filename=f"img-{idx}.jpg",
            geographic_analysis={"i": idx},
            yolo_detection={},
        )
        # Force a monotonic gap; SQLite stores REAL with sub-ms resolution
        # but we want zero ambiguity in tests.
        time.sleep(0.01)

    assert store.count() == 5

    removed = store.enforce_max_sessions(max_n=3)

    assert removed == 2
    assert store.count() == 3
    # The two oldest must be gone; the three newest must remain.
    assert store.get("sess-0") is None
    assert store.get("sess-1") is None
    assert store.get("sess-2") is not None
    assert store.get("sess-3") is not None
    assert store.get("sess-4") is not None


# ----------------------------------------------------------------------
# Concurrency
# ----------------------------------------------------------------------
def test_concurrent_access_thread_safe(db_path: str) -> None:
    """Ten concurrent writers from different threads must all succeed.

    We use a single store instance shared across threads; each thread
    obtains its own connection through ``threading.local`` and the
    write lock serialises compound writes. The test passes when every
    row is present at the end and no exception was raised.
    """
    store = ChatSessionStore(db_path)
    errors: list[BaseException] = []
    barrier = threading.Barrier(10)

    def writer(idx: int) -> None:
        try:
            # Sync all threads at the same instant to maximise contention.
            barrier.wait(timeout=5.0)
            store.store(
                f"thr-{idx}",
                image_filename=f"img-{idx}.jpg",
                geographic_analysis={"thread": idx},
                yolo_detection={"total_objects": idx},
                chat_history=[{"question": f"q{idx}", "response": f"a{idx}"}],
            )
        except BaseException as exc:  # noqa: BLE001  — collected for the assert
            errors.append(exc)

    try:
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(writer, i) for i in range(10)]
            for fut in futures:
                fut.result(timeout=10.0)

        assert not errors, f"Concurrent writers raised: {errors!r}"
        assert store.count() == 10
        for i in range(10):
            row = store.get(f"thr-{i}")
            assert row is not None, f"Missing row thr-{i}"
            assert row["geographic_analysis"] == {"thread": i}
            assert row["chat_history"][0]["question"] == f"q{i}"
    finally:
        store.close()


# ----------------------------------------------------------------------
# Image size validation
# ----------------------------------------------------------------------
def test_store_drops_oversized_encoded_image(store: ChatSessionStore, caplog) -> None:
    """Images exceeding MAX_ENCODED_IMAGE_BYTES are dropped with warning,
    session still stored without image.
    """
    MAX_ENCODED_IMAGE_BYTES = _store_module.MAX_ENCODED_IMAGE_BYTES

    oversized = "A" * (MAX_ENCODED_IMAGE_BYTES + 1)  # 1 byte over cap

    with caplog.at_level("WARNING"):
        store.store(
            "sid_big",
            image_filename="huge.jpg",
            encoded_image=oversized,
            geographic_analysis={},
            yolo_detection={},
        )

    result = store.get("sid_big")
    assert result is not None
    assert result.get("encoded_image") is None  # dropped
    assert result.get("image_filename") == "huge.jpg"  # other fields preserved
    assert any("exceeds" in record.message for record in caplog.records)


def test_concurrent_append_same_session(tmp_path) -> None:
    """Caller-level read-modify-write race on the SAME ``session_id``.

    The previous concurrency test exercised DISTINCT session_ids, where
    each writer touches its own row. The interesting failure mode that
    test does NOT cover is the TOCTOU race that happens in real use
    (e.g. user double-clicks "send"): two threads each execute

        history = store.get(sid)["chat_history"]   # read length N
        history.append(new_msg)
        store.update_field(sid, "chat_history", history)  # write N+1

    Without external serialisation per ``session_id`` at the caller, the
    second writer overwrites the first: the final history has N+1
    instead of N+2 messages. Individual ``store`` operations are atomic
    (``BEGIN IMMEDIATE`` + UPDATE), but the read-then-write at the caller
    is NOT — the store cannot, by API design, know that the two
    ``update_field`` calls are logically dependent.

    This test pins down the *current* behaviour:
    - No corruption (every entry is well-formed JSON, parsable).
    - No exceptions raised by any thread.
    - Final history length is between 1 and N (lost messages allowed).

    Lost messages are documented as caller responsibility; ``ChatService``
    must serialise per-session_id externally if exact-once semantics are
    required (e.g. a per-session lock, or a ticket: T9-future).
    """
    db_path = tmp_path / "race_test.db"
    store = ChatSessionStore(db_path=str(db_path))

    try:
        # Seed a session with empty history.
        store.store("shared_sid", image_filename="test.jpg", chat_history=[])

        n_threads = 20
        barrier = threading.Barrier(n_threads)
        errors: list[BaseException] = []

        def append_message(idx: int) -> None:
            try:
                barrier.wait(timeout=5.0)
                current = store.get("shared_sid")
                assert current is not None
                history = list(current.get("chat_history") or [])
                history.append({"q": f"Q{idx}", "a": f"A{idx}"})
                store.update_field("shared_sid", "chat_history", history)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [
            threading.Thread(target=append_message, args=(i,))
            for i in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Thread errors: {errors!r}"

        final = store.get("shared_sid")
        assert final is not None
        final_history = final["chat_history"]

        # Guarantee 1: no corruption. Every entry must be a well-formed
        # dict with the keys we wrote — no partial JSON, no truncated
        # values, no None entries.
        assert isinstance(final_history, list)
        assert all(
            isinstance(msg, dict) and "q" in msg and "a" in msg
            for msg in final_history
        ), f"Corrupted entries in history: {final_history!r}"

        # Guarantee 2: at least one append survived. With caller-level
        # serialisation the answer would be exactly ``n_threads``; without
        # it, lost messages are accepted as documented.
        assert 1 <= len(final_history) <= n_threads

        # Diagnostic: visible under ``pytest -v -s``. Quantifies the race
        # in this run so a future caller-level fix can verify it closes
        # the gap.
        print(
            f"\n[T8] Final history len: {len(final_history)}/{n_threads} appends. "
            f"Lost: {n_threads - len(final_history)} (caller-level race, documented)."
        )
    finally:
        store.close()
