#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para GeoCorrelator del proyecto Drone Geo Analysis.

After ADR-002, the correlation pipeline is explicitly marked as
NotImplemented. These tests assert the new (safe) behavior — no hardcoded
confidence values, no invented coordinate offsets.
"""

import sys
import os
import unittest
from unittest.mock import patch

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.geo.geo_correlator import GeoCorrelator


class TestGeoCorrelator(unittest.TestCase):
    """Tests para la clase GeoCorrelator."""

    def setUp(self):
        """Configurar tests con datos de prueba."""
        self.test_api_key = "test_api_key_12345"
        self.test_satellite_url = "https://test-api.example.com/v1"

        self.sample_telemetry = {
            "gps": {
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "altitude": 100,
            "orientation": {
                "yaw": 45,
                "pitch": -10,
                "roll": 5
            }
        }
        self.sample_drone_image = b"fake_drone_image_data_12345"

    def test_geo_correlator_init_with_params(self):
        """Test: Inicialización correcta con parámetros específicos."""
        correlator = GeoCorrelator(
            api_key=self.test_api_key,
            satellite_api_url=self.test_satellite_url
        )

        self.assertEqual(correlator.api_key, self.test_api_key)
        self.assertEqual(correlator.satellite_api_url, self.test_satellite_url)
        self.assertIsNotNone(correlator.cache_dir)

    def test_extract_gps_data_success(self):
        """Test: Extracción exitosa de datos GPS."""
        correlator = GeoCorrelator()
        result = correlator._extract_gps_data(self.sample_telemetry)

        self.assertEqual(result["latitude"], 40.7128)
        self.assertEqual(result["longitude"], -74.0060)
        self.assertEqual(result["altitude"], 100)
        self.assertNotIn("error", result)

    def test_extract_gps_data_missing_gps(self):
        """Test: Datos GPS faltantes en telemetría."""
        telemetry_no_gps = {"altitude": 100}

        correlator = GeoCorrelator()
        result = correlator._extract_gps_data(telemetry_no_gps)

        self.assertIn("error", result)
        self.assertIn("GPS no disponibles", result["error"])

    def test_extract_telemetry_data_complete(self):
        """Test: Extracción completa de datos de telemetría."""
        correlator = GeoCorrelator()
        result = correlator._extract_telemetry_data(self.sample_telemetry)

        self.assertEqual(result["latitude"], 40.7128)
        self.assertEqual(result["longitude"], -74.0060)
        self.assertEqual(result["altitude"], 100)
        self.assertEqual(result["yaw"], 45)
        self.assertEqual(result["pitch"], -10)
        self.assertEqual(result["roll"], 5)

    def test_apply_rotation_zero_yaw(self):
        """Test: Aplicación de rotación con yaw cero."""
        correlator = GeoCorrelator()
        x_rotated, y_rotated = correlator._apply_rotation(100, 50, 0)

        # Con yaw=0, no debe haber rotación
        self.assertAlmostEqual(x_rotated, 100, places=5)
        self.assertAlmostEqual(y_rotated, 50, places=5)

    # --- Stub-status tests (ADR-002) ---

    def test_perform_correlation_raises_not_implemented(self):
        """Test: _perform_correlation raises NotImplementedError (stub status)."""
        correlator = GeoCorrelator()
        gps_data = {"latitude": 40.7128, "longitude": -74.0060, "altitude": 100}

        with self.assertRaises(NotImplementedError) as ctx:
            correlator._perform_correlation(
                drone_image=self.sample_drone_image,
                satellite_image=None,
                gps_data=gps_data,
                drone_telemetry=self.sample_telemetry,
            )

        # Mensaje debe alertar sobre el stub status
        self.assertIn("not implemented", str(ctx.exception).lower())

    def test_correlate_drone_image_returns_not_implemented_marker(self):
        """Test: correlate_drone_image surfaces NotImplemented as a dict marker."""
        correlator = GeoCorrelator()

        result = correlator.correlate_drone_image(
            drone_image=self.sample_drone_image,
            drone_telemetry=self.sample_telemetry,
        )

        # No hardcoded confidence, no invented coordinates
        self.assertNotIn("confidence", result)
        self.assertNotIn("corrected_coordinates", result)

        # Explicit stub markers
        self.assertEqual(result.get("error"), "correlation_not_implemented")
        self.assertFalse(result.get("implemented", True))
        self.assertIn("message", result)
        self.assertIn("original_coordinates", result)
        self.assertEqual(result["original_coordinates"]["latitude"], 40.7128)
        self.assertEqual(result["original_coordinates"]["longitude"], -74.0060)

    def test_correlate_drone_image_propagates_gps_validation_error(self):
        """Test: missing GPS still short-circuits before reaching the stub."""
        correlator = GeoCorrelator()

        result = correlator.correlate_drone_image(
            drone_image=self.sample_drone_image,
            drone_telemetry={"altitude": 100},  # no gps key
        )

        self.assertIn("error", result)
        self.assertIn("GPS no disponibles", result["error"])

    def test_get_satellite_image_returns_none_with_warning(self):
        """Test: get_satellite_image returns None and emits a stub warning."""
        correlator = GeoCorrelator()

        with self.assertLogs("src.geo.geo_correlator", level="WARNING") as cm:
            result = correlator.get_satellite_image(40.7128, -74.0060)

        self.assertIsNone(result)
        self.assertTrue(
            any("stub" in msg.lower() for msg in cm.output),
            "Expected a 'stub' warning in logs",
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
