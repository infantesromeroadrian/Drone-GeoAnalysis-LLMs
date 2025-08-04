#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para GeoCorrelator del proyecto Drone Geo Analysis.
"""

import sys
import os
import unittest
import tempfile
import shutil
from unittest.mock import patch, mock_open

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
        print("✓ test_geo_correlator_init_with_params: EXITOSO")
    
    def test_geo_correlator_init_default(self):
        """Test: Inicialización con valores por defecto."""
        with patch.dict(os.environ, {"SATELLITE_API_KEY": "env_key"}):
            correlator = GeoCorrelator()
            
            self.assertEqual(correlator.api_key, "env_key")
            self.assertEqual(correlator.satellite_api_url, "https://api.satellite-imagery.com/v1")
            print("✓ test_geo_correlator_init_default: EXITOSO")
    
    def test_get_cache_filename_generation(self):
        """Test: Generación correcta de nombres de archivo de caché."""
        correlator = GeoCorrelator()
        
        filename = correlator._get_cache_filename(40.7128, -74.0060, 17)
        
        self.assertIn("sat_40.71280_-74.00600_17.jpg", filename)
        self.assertIn("cache", filename)
        print("✓ test_get_cache_filename_generation: EXITOSO")
    
    def test_extract_gps_data_success(self):
        """Test: Extracción exitosa de datos GPS."""
        correlator = GeoCorrelator()
        result = correlator._extract_gps_data(self.sample_telemetry)
        
        self.assertEqual(result["latitude"], 40.7128)
        self.assertEqual(result["longitude"], -74.0060)
        self.assertEqual(result["altitude"], 100)
        self.assertNotIn("error", result)
        print("✓ test_extract_gps_data_success: EXITOSO")
    
    def test_extract_gps_data_missing_gps(self):
        """Test: Datos GPS faltantes en telemetría."""
        telemetry_no_gps = {"altitude": 100}
        
        correlator = GeoCorrelator()
        result = correlator._extract_gps_data(telemetry_no_gps)
        
        self.assertIn("error", result)
        self.assertIn("GPS no disponibles", result["error"])
        print("✓ test_extract_gps_data_missing_gps: EXITOSO")
    
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
        print("✓ test_extract_telemetry_data_complete: EXITOSO")
    
    def test_apply_rotation_zero_yaw(self):
        """Test: Aplicación de rotación con yaw cero."""
        correlator = GeoCorrelator()
        x_rotated, y_rotated = correlator._apply_rotation(100, 50, 0)
        
        # Con yaw=0, no debe haber rotación
        self.assertAlmostEqual(x_rotated, 100, places=5)
        self.assertAlmostEqual(y_rotated, 50, places=5)
        print("✓ test_apply_rotation_zero_yaw: EXITOSO")
    
    def test_apply_rotation_90_degrees(self):
        """Test: Aplicación de rotación de 90 grados."""
        correlator = GeoCorrelator()
        x_rotated, y_rotated = correlator._apply_rotation(100, 0, 90)
        
        # Con yaw=90°, (100,0) -> (0,100)
        self.assertAlmostEqual(x_rotated, 0, places=5)
        self.assertAlmostEqual(y_rotated, 100, places=5)
        print("✓ test_apply_rotation_90_degrees: EXITOSO")


if __name__ == '__main__':
    print("🧪 EJECUTANDO TESTS DE GEO CORRELATOR")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGeoCorrelator)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE GEO CORRELATOR:")
    print(f"   Tests ejecutados: {total_tests}")
    print(f"   Exitosos: {passed}")
    print(f"   Fallidos: {failures}")
    print(f"   Errores: {errors}")
    print(f"   Tasa de éxito: {(passed/total_tests)*100:.1f}%")
    
    if failures > 0 or errors > 0:
        print(f"\n❌ FALLOS DETECTADOS:")
        for failure in result.failures:
            print(f"   • {failure[0]}")
        for error in result.errors:
            print(f"   • {error[0]}")
    else:
        print(f"\n🎉 ¡TODOS LOS TESTS DE GEO CORRELATOR PASAN! 🎉") 