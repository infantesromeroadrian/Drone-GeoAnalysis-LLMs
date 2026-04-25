#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke tests for GeoAnalyzer prompt construction.

Validates that the prompt sent to the LLM contains the expected [TAG]
markers (post-emoji cleanup commit f3c1446) and is well-structured.

Does NOT make real LLM calls -- those would require API keys and live
network. For integration tests with live LLM, see
tests/integration/test_geo_analyzer_live.py (TODO).

Why this exists
---------------
Commit f3c1446 ("lote 2 emojis cleanup") replaced emoji headers in the
GeoAnalyzer prompt with bracketed [TAG] markers in uppercase. Because
those strings flow into the prompt sent to Groq Llama 4 Scout / GPT-4
Vision, a regression here would silently degrade model output without
breaking any existing test. This module locks the contract.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_openai_response():
    """Build a mock OpenAI ChatCompletion response shape used in unit tests."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = (
        '{"country": "Japan", "city": "Tokyo", "district": "Shibuya", '
        '"neighborhood": "Shibuya Crossing", "street": "Center Gai", '
        '"confidence": 75, "supporting_evidence": ["Japanese signage"]}'
    )
    return mock


@pytest.fixture
def geo_analyzer_with_mock_client(mock_openai_response, monkeypatch):
    """Instantiate GeoAnalyzer with mocked OpenAI client.

    The fake-key prefix is "fake-" rather than "your_" because
    _validate_api_configuration() rejects keys starting with "your_" as
    placeholders. We need a key that passes validation so the prompt
    builder is exercised normally.
    """
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")

    from src.models.geo_analyzer import GeoAnalyzer

    analyzer = GeoAnalyzer()
    analyzer.client = MagicMock()
    analyzer.client.chat.completions.create = MagicMock(return_value=mock_openai_response)
    return analyzer


class TestPromptHasNoEmojis:
    """Locks the post-f3c1446 contract: no emojis allowed in YOLO context."""

    def test_yolo_context_prompt_has_no_emojis(self, geo_analyzer_with_mock_client):
        """Post-f3c1446 commit: prompts must not contain emojis."""
        analyzer = geo_analyzer_with_mock_client
        yolo_context = {
            "total_objects": 5,
            "object_summary": {"car": 3, "person": 2},
            "prominent_objects": [
                {"class_name": "car", "confidence": 0.9, "area_percentage": 15.0}
            ],
            "geographic_indicators": {
                "vehicles": [{"type": "car", "confidence": 0.9}],
                "urban_elements": [{"type": "traffic_light", "confidence": 0.8}],
                "people_indicators": [{"confidence": 0.85, "area_percentage": 5.0}],
                "transportation": [{"type": "bicycle", "confidence": 0.7}],
                "natural_elements": [],
            },
        }
        formatted = analyzer._format_yolo_context(yolo_context)

        # Common emojis that were in the old prompt before f3c1446
        forbidden_emojis = [
            "\U0001f50d",  # magnifying glass
            "\U0001f4ca",  # bar chart
            "\U0001f4cb",  # clipboard
            "⭐",  # star
            "\U0001f5fa",  # world map
            "\U0001f4a1",  # bulb
            "\U0001f697",  # car
            "\U0001f3d9",  # cityscape
            "\U0001f465",  # busts in silhouette
            "\U0001f6b2",  # bicycle
            "\U0001f33f",  # herb
        ]
        for emoji in forbidden_emojis:
            assert emoji not in formatted, (
                f"Emoji {emoji!r} found in prompt -- regression of f3c1446 cleanup"
            )

    def test_yolo_context_has_tag_markers(self, geo_analyzer_with_mock_client):
        """Validates [TAG] markers replacing emojis are present."""
        analyzer = geo_analyzer_with_mock_client
        yolo_context = {
            "total_objects": 3,
            "object_summary": {"car": 3},
            "prominent_objects": [],
            "geographic_indicators": {},
        }
        formatted = analyzer._format_yolo_context(yolo_context)

        # Expected [TAG] markers (uppercase, in brackets) -- exact strings
        # present in src/models/geo_analyzer.py::_format_yolo_context.
        expected_markers = [
            "[YOLO_OBJECT_ANALYSIS]",
            "[GENERAL_SUMMARY]",
            "[OBJECTS_BY_CATEGORY]",
            "[PROMINENT_OBJECTS]",
            "[GEOGRAPHIC_INDICATORS]",
            "[GEOGRAPHIC_ANALYSIS_CONTEXT]",
        ]
        for marker in expected_markers:
            assert marker in formatted, (
                f"Expected marker {marker!r} not in prompt -- "
                f"check geo_analyzer.py _format_yolo_context"
            )


class TestPromptStructure:
    """Validates the high-level prompt scaffolding remains intact."""

    def test_system_prompt_contains_osint_instructions(self, geo_analyzer_with_mock_client):
        """OSINT analysis instructions must be in system prompt."""
        analyzer = geo_analyzer_with_mock_client
        prompt = analyzer._build_system_prompt()

        # Key OSINT terms expected (Spanish source -- match accordingly)
        assert "OSINT" in prompt
        assert "JSON" in prompt
        assert "geográfica" in prompt.lower() or "geographic" in prompt.lower()

    def test_user_prompt_contains_yolo_context(self, geo_analyzer_with_mock_client):
        """User prompt interpolates YOLO context correctly."""
        analyzer = geo_analyzer_with_mock_client
        metadata = {
            "format": "JPEG",
            "dimensions": (1920, 1080),
            "yolo_context": {
                "total_objects": 7,
                "object_summary": {"car": 4, "truck": 3},
                "prominent_objects": [],
                "geographic_indicators": {},
            },
        }
        prompt = analyzer._build_user_prompt(metadata)

        # YOLO context flows through: total_objects appears verbatim and
        # the [TAG] header lands inside the user prompt.
        assert "7" in prompt
        assert "[YOLO_OBJECT_ANALYSIS]" in prompt
        # Image metadata interpolated as well
        assert "JPEG" in prompt
        assert "1920" in prompt or "1080" in prompt

    def test_response_format_template_is_valid_json_skeleton(self, geo_analyzer_with_mock_client):
        """The expected response format template must reference required JSON keys."""
        analyzer = geo_analyzer_with_mock_client
        template = analyzer._get_response_format_template()

        for key in [
            "country",
            "city",
            "district",
            "neighborhood",
            "street",
            "confidence",
            "supporting_evidence",
            "coordinates",
        ]:
            assert key in template, (
                f"Required JSON key {key!r} missing from response template"
            )


class TestEmptyOrErrorYoloContext:
    """Edge cases: missing or failed YOLO upstream stage must not crash prompt build."""

    def test_empty_yolo_context_handled(self, geo_analyzer_with_mock_client):
        """Empty dict triggers the fallback string."""
        analyzer = geo_analyzer_with_mock_client
        result = analyzer._format_yolo_context({})
        # Fallback string in code: "No hay información adicional de objetos detectados disponible."
        assert "no" in result.lower() or "n/a" in result.lower() or "sin" in result.lower(), (
            "Empty YOLO context should produce a fallback string"
        )

    def test_error_yolo_context_handled(self, geo_analyzer_with_mock_client):
        """An upstream YOLO error key short-circuits to the same fallback."""
        analyzer = geo_analyzer_with_mock_client
        result = analyzer._format_yolo_context({"error": "YOLO unavailable"})
        # Should not crash; should produce some readable string
        assert isinstance(result, str)
        assert len(result) > 0
