#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para GeoTriangulation del proyecto Drone Geo Analysis.
"""

import sys
import os
import unittest

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.geo.geo_triangulation import GeoTriangulation


class TestGeoTriangulation(unittest.TestCase):
    """Tests para la clase GeoTriangulation."""
    
    def setUp(self):
        """Configurar tests con datos de prueba."""
        self.triangulation = GeoTriangulation()
        
        self.drone_position_1 = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": 100
        }
        
        self.drone_position_2 = {
            "latitude": 40.7130,
            "longitude": -74.0058,
            "altitude": 120
        }
        
        self.test_target_id = "test_target_001"
    
    def test_geo_triangulation_init(self):
        """Test: Inicialización correcta del sistema de triangulación."""
        triangulation = GeoTriangulation()
        self.assertIsInstance(triangulation.observations, dict)
        self.assertEqual(len(triangulation.observations), 0)
        print("✓ test_geo_triangulation_init: EXITOSO")
    
    def test_add_observation_success(self):
        """Test: Agregar observación exitosamente."""
        observation_id = self.triangulation.add_observation(
            self.test_target_id, self.drone_position_1, 45.0, 15.0, 0.85
        )
        
        self.assertIsInstance(observation_id, str)
        self.assertIn(self.test_target_id, observation_id)
        self.assertEqual(len(self.triangulation.observations[self.test_target_id]), 1)
        print("✓ test_add_observation_success: EXITOSO")
    
    def test_calculate_position_success(self):
        """Test: Cálculo exitoso de posición con múltiples observaciones."""
        # Agregar múltiples observaciones
        self.triangulation.add_observation(
            self.test_target_id, self.drone_position_1, 45.0, 15.0, 0.85
        )
        self.triangulation.add_observation(
            self.test_target_id, self.drone_position_2, 30.0, 20.0, 0.90
        )
        
        result = self.triangulation.calculate_position(self.test_target_id)
        
        self.assertNotIn("error", result)
        self.assertEqual(result["target_id"], self.test_target_id)
        self.assertEqual(result["observations_count"], 2)
        self.assertIn("position", result)
        print("✓ test_calculate_position_success: EXITOSO")
    
    def test_reset_target_success(self):
        """Test: Eliminación exitosa de observaciones de un objetivo."""
        # Agregar observaciones
        self.triangulation.add_observation(
            self.test_target_id, self.drone_position_1, 45.0, 15.0, 0.85
        )
        
        # Eliminar
        result = self.triangulation.reset_target(self.test_target_id)
        
        self.assertTrue(result)
        self.assertNotIn(self.test_target_id, self.triangulation.observations)
        print("✓ test_reset_target_success: EXITOSO")
    
    def test_create_target(self):
        """Test: Creación de nuevo objetivo."""
        target_id = self.triangulation.create_target()
        
        self.assertIsInstance(target_id, str)
        self.assertIn("target_", target_id)
        self.assertIn(target_id, self.triangulation.observations)
        print("✓ test_create_target: EXITOSO")


if __name__ == '__main__':
    print("🧪 EJECUTANDO TESTS DE GEO TRIANGULATION")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGeoTriangulation)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE GEO TRIANGULATION:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE GEO TRIANGULATION PASAN! 🎉") 