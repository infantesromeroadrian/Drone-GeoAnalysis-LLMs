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


# ----------------------------------------------------------------------
# T9: caller-level fix in ChatService — per-session_id lock
# ----------------------------------------------------------------------
def _load_chat_service():
    """Load ``ChatService`` with heavy package init bypassed.

    ``src/services/__init__.py`` imports ``cv2`` / ``ultralytics`` /
    ``torch`` which are unrelated to the concurrency contract under test.
    We import the module by path with its real name so that
    ``from src.services.chat_session_store import ChatSessionStore`` inside
    the module is satisfied without going through the package __init__.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Pre-stub heavy package init so ``src.services`` imports cheaply.
    import types

    services_pkg = types.ModuleType("src.services")
    services_pkg.__path__ = [os.path.join(project_root, "src", "services")]
    sys.modules.setdefault("src", types.ModuleType("src"))
    sys.modules["src"].__path__ = [os.path.join(project_root, "src")]
    sys.modules.setdefault("src.services", services_pkg)

    # Minimal stub for ``src.utils.config.get_llm_config`` so we can
    # construct ChatService without env vars or real provider config.
    utils_pkg = types.ModuleType("src.utils")
    utils_pkg.__path__ = [os.path.join(project_root, "src", "utils")]
    sys.modules.setdefault("src.utils", utils_pkg)

    config_stub = types.ModuleType("src.utils.config")

    def _stub_get_llm_config():
        return {"provider": "openai", "config": {"api_key": None, "model": "stub"}}

    def _stub_get_openai_config():
        return {"model": "stub"}

    config_stub.get_llm_config = _stub_get_llm_config
    config_stub.get_openai_config = _stub_get_openai_config
    sys.modules["src.utils.config"] = config_stub

    # Stub ``openai.OpenAI`` to avoid network/credentials at import time.
    openai_stub = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

    openai_stub.OpenAI = _StubOpenAI
    sys.modules.setdefault("openai", openai_stub)

    # Now load the chat_session_store first (needed by chat_service).
    store_path = os.path.join(project_root, "src", "services", "chat_session_store.py")
    spec = importlib.util.spec_from_file_location(
        "src.services.chat_session_store", store_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load store spec for {store_path}")
    store_mod = importlib.util.module_from_spec(spec)
    sys.modules["src.services.chat_session_store"] = store_mod
    spec.loader.exec_module(store_mod)

    # Finally load chat_service itself.
    cs_path = os.path.join(project_root, "src", "services", "chat_service.py")
    spec = importlib.util.spec_from_file_location("src.services.chat_service", cs_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load chat_service spec for {cs_path}")
    cs_mod = importlib.util.module_from_spec(spec)
    sys.modules["src.services.chat_service"] = cs_mod
    spec.loader.exec_module(cs_mod)
    return cs_mod


class _FakeLLMResponse:
    """Minimal duck-type for ``client.chat.completions.create`` return."""

    def __init__(self, content: str) -> None:
        self.choices = [
            type("Choice", (), {"message": type("Msg", (), {"content": content})()})()
        ]


class _FakeLLMClient:
    """Stand-in for the OpenAI client whose ``create`` sleeps then returns.

    The sleep is the whole point: it widens the window between the
    pre-LLM read and the post-LLM append, which is exactly the gap where
    the T8 race manifests in production. A correct ``ChatService`` with
    a per-session lock must serialise the appends so no message is lost.
    """

    def __init__(self, latency_seconds: float) -> None:
        self._latency = latency_seconds
        self.chat = self  # ``client.chat.completions.create``
        self.completions = self
        self._counter = 0
        self._counter_lock = threading.Lock()

    def create(self, *, model, messages, temperature, max_tokens):  # noqa: ARG002
        with self._counter_lock:
            self._counter += 1
            n = self._counter
        time.sleep(self._latency)
        return _FakeLLMResponse(f"answer-{n}")


def test_ask_question_concurrent_same_session_no_message_loss(tmp_path) -> None:
    """T9 fix: ``ChatService.ask_question`` must NOT lose messages when
    called concurrently on the same ``session_id``.

    This exercises the exact failure mode T8 documented at the store
    level. With the per-session lock in ``_append_history``, every append
    re-reads the latest persisted history inside the critical section,
    so concurrent appends serialise into a strict order and the final
    history contains all ``n_threads`` entries.

    We deliberately use a non-trivial LLM latency so the pre-LLM context
    snapshot is stale by construction when each thread reaches the
    append step. If the lock were absent, this test would fail the same
    way T8 does (lost messages).
    """
    cs_mod = _load_chat_service()
    ChatService = cs_mod.ChatService

    db_path = str(tmp_path / "chat_t9.db")
    service = ChatService(db_path=db_path)

    # Inject a fake LLM client so we don't need credentials. Latency is
    # small but non-zero — enough to interleave threads reliably.
    service.client = _FakeLLMClient(latency_seconds=0.05)
    service.config = {"model": "stub"}

    # Seed a session so ``ask_question`` has context to load.
    service.store_analysis_context(
        session_id="t9_shared",
        analysis_results={"country": "ES"},
        yolo_results={"total_objects": 0, "object_summary": {}},
        image_filename="t9.jpg",
    )

    n_threads = 10
    barrier = threading.Barrier(n_threads)
    errors: list[BaseException] = []

    def worker(idx: int) -> None:
        try:
            barrier.wait(timeout=5.0)
            result = service.ask_question("t9_shared", question=f"Q{idx}")
            assert result.get("status") == "success", result
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15.0)

    assert not errors, f"Worker errors: {errors!r}"

    history = service.get_chat_history("t9_shared")
    assert isinstance(history, list)
    assert all(
        isinstance(entry, dict) and "question" in entry and "response" in entry
        for entry in history
    ), f"Corrupt history: {history!r}"
    # The whole point of the fix: every append survives.
    assert len(history) == n_threads, (
        f"Lost messages despite per-session lock: got {len(history)}/{n_threads}. "
        f"History: {history!r}"
    )
    # Every question Q0..Q(n-1) must appear exactly once.
    questions = sorted(entry["question"] for entry in history)
    assert questions == sorted(f"Q{i}" for i in range(n_threads))


def test_session_lock_gc_drops_stale_locks(tmp_path) -> None:
    """``_cleanup_expired_sessions`` must drop locks for evicted sessions.

    Without GC the ``_session_locks`` dict grows monotonically with the
    number of distinct ``session_id``s ever seen — a memory leak under
    long-running services. The cleanup pass should remove only locks
    whose store row is gone; live sessions keep theirs.
    """
    cs_mod = _load_chat_service()
    ChatService = cs_mod.ChatService

    db_path = str(tmp_path / "chat_t9_gc.db")
    service = ChatService(db_path=db_path)
    service.client = _FakeLLMClient(latency_seconds=0.0)
    service.config = {"model": "stub"}

    # Touch lock for a session that we never store: the lock entry should
    # be GC'd because the store has no matching row.
    service._get_session_lock("ghost")
    assert "ghost" in service._session_locks

    # Real session: store + touch lock. Must survive GC.
    service.store_analysis_context(
        session_id="alive",
        analysis_results={},
        yolo_results={},
        image_filename="a.jpg",
    )
    service._get_session_lock("alive")
    assert "alive" in service._session_locks

    service._cleanup_expired_sessions()

    assert "ghost" not in service._session_locks, (
        "Stale lock for non-existent session must be GC'd"
    )
    assert "alive" in service._session_locks, (
        "Lock for live session must NOT be GC'd"
    )


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
