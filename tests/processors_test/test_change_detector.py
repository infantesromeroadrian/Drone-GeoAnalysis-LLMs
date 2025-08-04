#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para ChangeDetector del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad del detector de cambios entre imágenes:
- Inicialización y configuración
- Generación de IDs de ubicación
- Validación de referencias
- Métricas de cambio (sin procesamiento OpenCV real)
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.processors.change_detector import ChangeDetector


class TestChangeDetector(unittest.TestCase):
    """Tests para la clase ChangeDetector."""
    
    def setUp(self):
        """Configurar tests con datos de prueba."""
        self.detector = ChangeDetector(sensitivity=0.3)
        
        self.sample_coordinates = {
            "latitude": 40.7128,
            "longitude": -74.0060
        }
        
        self.sample_metadata = {
            "timestamp": 1234567890,
            "drone_id": "test_drone_001",
            "altitude": 100
        }
        
        # Simular datos de imagen
        self.fake_image_data = b"fake_image_data_12345"
    
    def test_change_detector_init_default(self):
        """Test: Inicialización con sensibilidad por defecto."""
        detector = ChangeDetector()
        
        self.assertEqual(detector.sensitivity, 0.2)
        self.assertIsInstance(detector.reference_images, dict)
        self.assertEqual(len(detector.reference_images), 0)
        print("✓ test_change_detector_init_default: EXITOSO")
    
    def test_change_detector_init_custom_sensitivity(self):
        """Test: Inicialización con sensibilidad personalizada."""
        detector = ChangeDetector(sensitivity=0.5)
        
        self.assertEqual(detector.sensitivity, 0.5)
        self.assertIsInstance(detector.reference_images, dict)
        print("✓ test_change_detector_init_custom_sensitivity: EXITOSO")
    
    def test_generate_location_id(self):
        """Test: Generación correcta de ID de ubicación."""
        location_id = self.detector._generate_location_id(self.sample_coordinates)
        
        expected_id = "40.71280_-74.00600"
        self.assertEqual(location_id, expected_id)
        print("✓ test_generate_location_id: EXITOSO")
    
    def test_generate_location_id_precision(self):
        """Test: Precisión en la generación de ID de ubicación."""
        coords = {"latitude": 40.712834567, "longitude": -74.006012345}
        location_id = self.detector._generate_location_id(coords)
        
        # Debe mantener 5 decimales
        expected_id = "40.71283_-74.00601"
        self.assertEqual(location_id, expected_id)
        print("✓ test_generate_location_id_precision: EXITOSO")
    
    def test_validate_reference_exists(self):
        """Test: Validación de referencia existente."""
        # Simular referencia existente
        location_id = "test_location_001"
        self.detector.reference_images[location_id] = {"test": "data"}
        
        result = self.detector._validate_reference(location_id)
        
        self.assertTrue(result)
        print("✓ test_validate_reference_exists: EXITOSO")
    
    def test_validate_reference_not_exists(self):
        """Test: Validación de referencia inexistente."""
        result = self.detector._validate_reference("nonexistent_location")
        
        self.assertFalse(result)
        print("✓ test_validate_reference_not_exists: EXITOSO")
    
    @patch('cv2.imdecode')
    @patch('cv2.cvtColor')
    @patch('cv2.GaussianBlur')
    def test_process_reference_image_success(self, mock_blur, mock_cvt, mock_decode):
        """Test: Procesamiento exitoso de imagen de referencia."""
        # Configurar mocks
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_gray = np.zeros((100, 100), dtype=np.uint8)
        mock_blurred = np.zeros((100, 100), dtype=np.uint8)
        
        mock_decode.return_value = mock_image
        mock_cvt.return_value = mock_gray
        mock_blur.return_value = mock_blurred
        
        result = self.detector._process_reference_image(self.fake_image_data)
        
        self.assertIsNotNone(result)
        self.assertIn("original", result)
        self.assertIn("processed", result)
        mock_decode.assert_called_once()
        mock_cvt.assert_called_once()
        mock_blur.assert_called_once()
        print("✓ test_process_reference_image_success: EXITOSO")
    
    @patch('cv2.imdecode')
    def test_process_reference_image_decode_error(self, mock_decode):
        """Test: Error en decodificación de imagen de referencia."""
        mock_decode.side_effect = Exception("Decode error")
        
        result = self.detector._process_reference_image(self.fake_image_data)
        
        self.assertIsNone(result)
        print("✓ test_process_reference_image_decode_error: EXITOSO")
    
    def test_store_reference_image(self):
        """Test: Almacenamiento de imagen de referencia."""
        location_id = "test_location_001"
        processed_image = {
            "original": np.zeros((100, 100, 3), dtype=np.uint8),
            "processed": np.zeros((100, 100), dtype=np.uint8)
        }
        
        self.detector._store_reference_image(
            location_id, processed_image, self.sample_coordinates, self.sample_metadata
        )
        
        # Verificar que se almacenó correctamente
        self.assertIn(location_id, self.detector.reference_images)
        stored = self.detector.reference_images[location_id]
        self.assertIn("image", stored)
        self.assertIn("original", stored)
        self.assertIn("metadata", stored)
        self.assertIn("coordinates", stored)
        self.assertEqual(stored["metadata"], self.sample_metadata)
        self.assertEqual(stored["coordinates"], self.sample_coordinates)
        print("✓ test_store_reference_image: EXITOSO")
    
    @patch.object(ChangeDetector, '_process_reference_image')
    def test_add_reference_image_success(self, mock_process):
        """Test: Agregar imagen de referencia exitosamente."""
        # Configurar mock
        mock_process.return_value = {
            "original": np.zeros((100, 100, 3), dtype=np.uint8),
            "processed": np.zeros((100, 100), dtype=np.uint8)
        }
        
        location_id = self.detector.add_reference_image(
            self.fake_image_data, self.sample_coordinates, self.sample_metadata
        )
        
        expected_id = "40.71280_-74.00600"
        self.assertEqual(location_id, expected_id)
        self.assertIn(location_id, self.detector.reference_images)
        mock_process.assert_called_once_with(self.fake_image_data)
        print("✓ test_add_reference_image_success: EXITOSO")
    
    @patch.object(ChangeDetector, '_process_reference_image')
    def test_add_reference_image_process_error(self, mock_process):
        """Test: Error en procesamiento al agregar imagen de referencia."""
        mock_process.return_value = None  # Simular error en procesamiento
        
        location_id = self.detector.add_reference_image(
            self.fake_image_data, self.sample_coordinates, self.sample_metadata
        )
        
        self.assertEqual(location_id, "")
        self.assertEqual(len(self.detector.reference_images), 0)
        print("✓ test_add_reference_image_process_error: EXITOSO")
    
    def test_detect_changes_no_reference(self):
        """Test: Detección de cambios sin imagen de referencia."""
        result = self.detector.detect_changes(self.fake_image_data, "nonexistent_location")
        
        self.assertIn("error", result)
        self.assertIn("no encontrada", result["error"])
        print("✓ test_detect_changes_no_reference: EXITOSO")
    
    def test_calculate_change_metrics(self):
        """Test: Cálculo de métricas de cambio."""
        # Simular datos de diferencia
        threshold_image = np.zeros((100, 100), dtype=np.uint8)
        threshold_image[10:20, 10:20] = 255  # 100 píxeles cambiados de 10000 total = 1%
        
        difference_data = {"threshold": threshold_image}
        contour_data = {"significant_contours": []}  # Sin contornos significativos
        
        metrics = self.detector._calculate_change_metrics(difference_data, contour_data)
        
        self.assertIn("change_percentage", metrics)
        self.assertIn("has_significant_changes", metrics)
        self.assertIn("significant_areas", metrics)
        self.assertAlmostEqual(metrics["change_percentage"], 1.0, places=1)
        self.assertEqual(metrics["significant_areas"], 0)
        print("✓ test_calculate_change_metrics: EXITOSO")
    
    def test_calculate_change_metrics_significant_changes(self):
        """Test: Métricas con cambios significativos."""
        # Detector con sensibilidad 0.3 (30%)
        # Simular 40% de cambio
        threshold_image = np.zeros((100, 100), dtype=np.uint8)
        threshold_image[0:40, :] = 255  # 4000 píxeles de 10000 = 40%
        
        difference_data = {"threshold": threshold_image}
        contour_data = {"significant_contours": [1, 2, 3]}  # 3 contornos
        
        metrics = self.detector._calculate_change_metrics(difference_data, contour_data)
        
        self.assertAlmostEqual(metrics["change_percentage"], 40.0, places=1)
        self.assertTrue(metrics["has_significant_changes"])  # 40% > 30%
        self.assertEqual(metrics["significant_areas"], 3)
        print("✓ test_calculate_change_metrics_significant_changes: EXITOSO")
    
    def test_build_detection_result(self):
        """Test: Construcción del resultado de detección."""
        location_id = "test_location_001"
        
        # Agregar imagen de referencia simulada
        self.detector.reference_images[location_id] = {
            "metadata": {"timestamp": 1234567890}
        }
        
        metrics = {
            "has_significant_changes": True,
            "change_percentage": 25.5,
            "significant_areas": 2
        }
        
        changes_image_bytes = b"fake_changes_image"
        contour_data = {"significant_contours": []}
        
        result = self.detector._build_detection_result(
            location_id, metrics, changes_image_bytes, contour_data
        )
        
        self.assertEqual(result["location_id"], location_id)
        self.assertTrue(result["has_changes"])
        self.assertEqual(result["change_percentage"], 25.5)
        self.assertEqual(result["significant_areas"], 2)
        self.assertEqual(result["changes_image"], changes_image_bytes)
        self.assertEqual(result["timestamp"], 1234567890)
        print("✓ test_build_detection_result: EXITOSO")
    
    def test_get_reference_image_not_exists(self):
        """Test: Obtener imagen de referencia que no existe."""
        result = self.detector.get_reference_image("nonexistent_location")
        
        self.assertIsNone(result)
        print("✓ test_get_reference_image_not_exists: EXITOSO")
    
    @patch('cv2.imencode')
    def test_get_reference_image_exists(self, mock_encode):
        """Test: Obtener imagen de referencia existente."""
        location_id = "test_location_001"
        mock_buffer = MagicMock()
        mock_buffer.tobytes.return_value = b"encoded_image_data"
        mock_encode.return_value = (True, mock_buffer)
        
        # Agregar imagen de referencia
        self.detector.reference_images[location_id] = {
            "original": np.zeros((100, 100, 3), dtype=np.uint8)
        }
        
        result = self.detector.get_reference_image(location_id)
        
        self.assertEqual(result, b"encoded_image_data")
        mock_encode.assert_called_once()
        print("✓ test_get_reference_image_exists: EXITOSO")
    
    def test_remove_reference_image_not_exists(self):
        """Test: Eliminar imagen de referencia que no existe."""
        result = self.detector.remove_reference_image("nonexistent_location")
        
        self.assertFalse(result)
        print("✓ test_remove_reference_image_not_exists: EXITOSO")
    
    def test_remove_reference_image_exists(self):
        """Test: Eliminar imagen de referencia existente."""
        location_id = "test_location_001"
        
        # Agregar imagen de referencia
        self.detector.reference_images[location_id] = {"test": "data"}
        
        result = self.detector.remove_reference_image(location_id)
        
        self.assertTrue(result)
        self.assertNotIn(location_id, self.detector.reference_images)
        print("✓ test_remove_reference_image_exists: EXITOSO")


if __name__ == '__main__':
    print("🧪 EJECUTANDO TESTS DE CHANGE DETECTOR")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestChangeDetector)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE CHANGE DETECTOR:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE CHANGE DETECTOR PASAN! 🎉") 