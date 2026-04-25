"""Security-focused tests for src.main.DroneGeoApp.

Covers SECRET_KEY enforcement: production-like contexts must hard-fail when
SECRET_KEY is missing, while development falls back to a random key with an
ERROR-level log so the gap is visible.
"""

import logging
import os
import sys

import pytest

# Ensure project root is importable when running this test file in isolation.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import DroneGeoApp


@pytest.fixture
def clean_env(monkeypatch):
    """Strip SECRET_KEY / FLASK_ENV / LLM_PROVIDER from the environment for the test."""
    for var in ("SECRET_KEY", "FLASK_ENV", "LLM_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


class TestResolveSecretKey:
    """_resolve_secret_key behaviour under the four relevant scenarios."""

    def test_returns_env_value_when_present(self, clean_env):
        clean_env.setenv("SECRET_KEY", "deadbeef" * 4)
        clean_env.setenv("FLASK_ENV", "production")  # would normally enforce
        app = DroneGeoApp()
        assert app._resolve_secret_key() == "deadbeef" * 4

    def test_raises_in_flask_production_without_key(self, clean_env):
        clean_env.setenv("FLASK_ENV", "production")
        app = DroneGeoApp()
        with pytest.raises(RuntimeError, match="SECRET_KEY is required"):
            app._resolve_secret_key()

    def test_raises_when_provider_is_openai(self, clean_env):
        clean_env.setenv("LLM_PROVIDER", "openai")
        app = DroneGeoApp()
        with pytest.raises(RuntimeError, match="SECRET_KEY is required"):
            app._resolve_secret_key()

    def test_raises_when_provider_is_groq(self, clean_env):
        clean_env.setenv("LLM_PROVIDER", "groq")
        app = DroneGeoApp()
        with pytest.raises(RuntimeError, match="SECRET_KEY is required"):
            app._resolve_secret_key()

    def test_dev_fallback_when_provider_is_docker(self, clean_env, caplog):
        clean_env.setenv("LLM_PROVIDER", "docker")
        app = DroneGeoApp()
        with caplog.at_level(logging.ERROR, logger="src.main"):
            key = app._resolve_secret_key()
        # 32 random bytes hex-encoded == 64 chars.
        assert isinstance(key, str)
        assert len(key) == 64
        # Must log at ERROR (not WARNING) so the gap is impossible to miss.
        assert any(
            record.levelno == logging.ERROR and "SECRET_KEY" in record.message
            for record in caplog.records
        )

    def test_dev_fallback_when_no_provider_set(self, clean_env, caplog):
        # Default provider in main is "docker", same dev posture.
        app = DroneGeoApp()
        with caplog.at_level(logging.ERROR, logger="src.main"):
            key = app._resolve_secret_key()
        assert len(key) == 64
        assert any(record.levelno == logging.ERROR for record in caplog.records)


class TestProductionContextDetection:
    """_is_production_context covers the trigger matrix."""

    def test_flask_env_production_triggers(self, clean_env):
        clean_env.setenv("FLASK_ENV", "production")
        assert DroneGeoApp()._is_production_context() is True

    def test_flask_env_production_case_insensitive(self, clean_env):
        clean_env.setenv("FLASK_ENV", "PRODUCTION")
        assert DroneGeoApp()._is_production_context() is True

    def test_provider_openai_triggers(self, clean_env):
        clean_env.setenv("LLM_PROVIDER", "openai")
        assert DroneGeoApp()._is_production_context() is True

    def test_provider_groq_triggers(self, clean_env):
        clean_env.setenv("LLM_PROVIDER", "groq")
        assert DroneGeoApp()._is_production_context() is True

    def test_provider_docker_does_not_trigger(self, clean_env):
        clean_env.setenv("LLM_PROVIDER", "docker")
        assert DroneGeoApp()._is_production_context() is False

    def test_default_does_not_trigger(self, clean_env):
        assert DroneGeoApp()._is_production_context() is False
