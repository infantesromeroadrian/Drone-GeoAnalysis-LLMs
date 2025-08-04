#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para GeolocationManager del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad del gestor de geolocalización:
- add_reference_image: Agregar imágenes de referencia
- create_target: Crear objetivos para triangulación
- get_reference_images: Obtener imágenes de referencia
- get_targets: Obtener objetivos
"""

import sys
import os
import unittest
from datetime import datetime

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.geo_manager import GeolocationManager


class TestGeolocationManager(unittest.TestCase):
    """Tests para el gestor de geolocalización."""
    
    def setUp(self):
        """Configurar tests con datos de prueba."""
        self.manager = GeolocationManager()
        
        self.sample_telemetry = {
            "gps": {
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "altitude": 100,
            "timestamp": "2024-01-01T10:00:00"
        }
    
    def test_geolocation_manager_init(self):
        """Test: Inicialización correcta del gestor."""
        manager = GeolocationManager()
        
        self.assertIsNone(manager.current_reference_image)
        self.assertIsInstance(manager.reference_images, dict)
        self.assertIsInstance(manager.targets, dict)
        self.assertEqual(len(manager.reference_images), 0)
        self.assertEqual(len(manager.targets), 0)
        print("✓ test_geolocation_manager_init: EXITOSO")
    
    def test_add_reference_image_success(self):
        """Test: Agregar imagen de referencia exitosamente."""
        ref_id = self.manager.add_reference_image(self.sample_telemetry)
        
        # Verificar que se generó un ID válido
        self.assertIsInstance(ref_id, str)
        self.assertTrue(ref_id.startswith("ref_"))
        
        # Verificar que se guardó en el diccionario
        self.assertIn(ref_id, self.manager.reference_images)
        
        # Verificar que se estableció como referencia actual
        self.assertEqual(self.manager.current_reference_image, ref_id)
        
        # Verificar contenido de la referencia
        ref_data = self.manager.reference_images[ref_id]
        self.assertIn("timestamp", ref_data)
        self.assertIn("location", ref_data)
        self.assertEqual(ref_data["location"], self.sample_telemetry["gps"])
        print("✓ test_add_reference_image_success: EXITOSO")
    
    def test_add_multiple_reference_images(self):
        """Test: Agregar múltiples imágenes de referencia."""
        # Agregar primera imagen
        ref_id_1 = self.manager.add_reference_image(self.sample_telemetry)
        
        # Agregar segunda imagen con diferentes coordenadas
        telemetry_2 = {
            "gps": {
                "latitude": 40.7129,
                "longitude": -74.0061
            },
            "altitude": 120
        }
        ref_id_2 = self.manager.add_reference_image(telemetry_2)
        
        # Verificar que ambas se guardaron
        self.assertEqual(len(self.manager.reference_images), 2)
        self.assertIn(ref_id_1, self.manager.reference_images)
        self.assertIn(ref_id_2, self.manager.reference_images)
        
        # La referencia actual debe ser la más reciente
        self.assertEqual(self.manager.current_reference_image, ref_id_2)
        print("✓ test_add_multiple_reference_images: EXITOSO")
    
    def test_create_target_success(self):
        """Test: Crear objetivo exitosamente."""
        target_id = self.manager.create_target()
        
        # Verificar que se generó un ID válido
        self.assertIsInstance(target_id, str)
        self.assertTrue(target_id.startswith("target_"))
        
        # Verificar que se guardó en el diccionario
        self.assertIn(target_id, self.manager.targets)
        
        # Verificar contenido del objetivo
        target_data = self.manager.targets[target_id]
        self.assertIn("captures", target_data)
        self.assertIn("timestamp", target_data)
        self.assertIsInstance(target_data["captures"], list)
        self.assertEqual(len(target_data["captures"]), 0)
        print("✓ test_create_target_success: EXITOSO")
    
    def test_create_multiple_targets(self):
        """Test: Crear múltiples objetivos."""
        target_id_1 = self.manager.create_target()
        target_id_2 = self.manager.create_target()
        target_id_3 = self.manager.create_target()
        
        # Verificar que todos se crearon
        self.assertEqual(len(self.manager.targets), 3)
        self.assertIn(target_id_1, self.manager.targets)
        self.assertIn(target_id_2, self.manager.targets)
        self.assertIn(target_id_3, self.manager.targets)
        
        # Verificar que los IDs son únicos
        self.assertNotEqual(target_id_1, target_id_2)
        self.assertNotEqual(target_id_2, target_id_3)
        self.assertNotEqual(target_id_1, target_id_3)
        print("✓ test_create_multiple_targets: EXITOSO")
    
    def test_get_reference_images_empty(self):
        """Test: Obtener imágenes de referencia cuando no hay ninguna."""
        ref_images = self.manager.get_reference_images()
        
        self.assertIsInstance(ref_images, dict)
        self.assertEqual(len(ref_images), 0)
        print("✓ test_get_reference_images_empty: EXITOSO")
    
    def test_get_reference_images_with_data(self):
        """Test: Obtener imágenes de referencia con datos."""
        # Agregar algunas imágenes de referencia
        ref_id_1 = self.manager.add_reference_image(self.sample_telemetry)
        ref_id_2 = self.manager.add_reference_image(self.sample_telemetry)
        
        ref_images = self.manager.get_reference_images()
        
        self.assertIsInstance(ref_images, dict)
        self.assertEqual(len(ref_images), 2)
        self.assertIn(ref_id_1, ref_images)
        self.assertIn(ref_id_2, ref_images)
        
        # Verificar que devuelve los mismos datos
        self.assertEqual(ref_images, self.manager.reference_images)
        print("✓ test_get_reference_images_with_data: EXITOSO")
    
    def test_get_targets_empty(self):
        """Test: Obtener objetivos cuando no hay ninguno."""
        targets = self.manager.get_targets()
        
        self.assertIsInstance(targets, dict)
        self.assertEqual(len(targets), 0)
        print("✓ test_get_targets_empty: EXITOSO")
    
    def test_get_targets_with_data(self):
        """Test: Obtener objetivos con datos."""
        # Crear algunos objetivos
        target_id_1 = self.manager.create_target()
        target_id_2 = self.manager.create_target()
        
        targets = self.manager.get_targets()
        
        self.assertIsInstance(targets, dict)
        self.assertEqual(len(targets), 2)
        self.assertIn(target_id_1, targets)
        self.assertIn(target_id_2, targets)
        
        # Verificar que devuelve los mismos datos
        self.assertEqual(targets, self.manager.targets)
        print("✓ test_get_targets_with_data: EXITOSO")
    
    def test_add_reference_image_with_empty_gps(self):
        """Test: Agregar imagen de referencia con GPS vacío."""
        telemetry_no_gps = {"altitude": 100}
        
        ref_id = self.manager.add_reference_image(telemetry_no_gps)
        
        # Debe funcionar aunque no haya datos GPS
        self.assertIsInstance(ref_id, str)
        self.assertIn(ref_id, self.manager.reference_images)
        
        # El campo location debe estar presente aunque esté vacío
        ref_data = self.manager.reference_images[ref_id]
        self.assertIn("location", ref_data)
        self.assertEqual(ref_data["location"], {})
        print("✓ test_add_reference_image_with_empty_gps: EXITOSO")
    
    def test_reference_image_id_format(self):
        """Test: Formato correcto del ID de imagen de referencia."""
        ref_id = self.manager.add_reference_image(self.sample_telemetry)
        
        # Verificar formato: ref_YYYYMMDDHHMMSS
        self.assertTrue(ref_id.startswith("ref_"))
        id_part = ref_id[4:]  # Remover "ref_"
        self.assertEqual(len(id_part), 14)  # YYYYMMDDHHMMSS
        self.assertTrue(id_part.isdigit())
        print("✓ test_reference_image_id_format: EXITOSO")
    
    def test_target_id_format(self):
        """Test: Formato correcto del ID de objetivo."""
        target_id = self.manager.create_target()
        
        # Verificar formato: target_YYYYMMDDHHMMSS
        self.assertTrue(target_id.startswith("target_"))
        id_part = target_id[7:]  # Remover "target_"
        self.assertEqual(len(id_part), 14)  # YYYYMMDDHHMMSS
        self.assertTrue(id_part.isdigit())
        print("✓ test_target_id_format: EXITOSO")


if __name__ == '__main__':
    print("🧪 EJECUTANDO TESTS DE GEOLOCATION MANAGER")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGeolocationManager)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE GEOLOCATION MANAGER:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE GEOLOCATION MANAGER PASAN! 🎉") 