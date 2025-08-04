#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests completos para AnalysisService del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad del servicio de análisis de imágenes:
- Inicialización y configuración 
- Procesamiento de imágenes y metadatos
- Codificación y análisis
- Filtros de confianza
- Gestión de archivos y resultados
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, Mock
import tempfile
import json
from datetime import datetime

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.analysis_service import AnalysisService


class TestAnalysisService(unittest.TestCase):
    """Tests para la clase AnalysisService."""
    
    def setUp(self):
        """Configurar tests con mocks y datos de prueba."""
        # Mock del analizador geográfico
        self.mock_analyzer = MagicMock()
        self.mock_analyzer.analyze_image.return_value = {
            'confidence': 0.85,
            'results': {'detected_objects': 5, 'classification': 'urban'},
            'timestamp': datetime.now().isoformat()
        }
        
        # Crear instancia del servicio
        self.service = AnalysisService(self.mock_analyzer)
        
        # Mock de archivo Flask
        self.mock_image_file = MagicMock()
        self.mock_image_file.filename = 'test_image.jpg'
        self.mock_image_file.save = MagicMock()
        
        # Parámetros de configuración de prueba
        self.config_params = {
            'confidence_threshold': 0.7,
            'analysis_type': 'full',
            'region': 'test_area'
        }
    
    def test_analysis_service_init(self):
        """Test: Inicialización correcta del servicio."""
        service = AnalysisService(self.mock_analyzer)
        
        self.assertEqual(service.analyzer, self.mock_analyzer)
        print("✓ test_analysis_service_init: EXITOSO")
    
    @patch('tempfile.gettempdir')
    @patch('os.path.join')
    def test_save_temp_image(self, mock_join, mock_gettempdir):
        """Test: Guardado de imagen temporal."""
        mock_gettempdir.return_value = '/tmp'
        mock_join.return_value = '/tmp/test_image.jpg'
        
        result = self.service._save_temp_image(self.mock_image_file)
        
        self.assertEqual(result, '/tmp/test_image.jpg')
        self.mock_image_file.save.assert_called_once_with('/tmp/test_image.jpg')
        print("✓ test_save_temp_image: EXITOSO")
    
    @patch('src.utils.helpers.get_image_metadata')
    def test_prepare_metadata(self, mock_get_metadata):
        """Test: Preparación de metadatos combinados."""
        mock_get_metadata.return_value = {
            'width': 1920,
            'height': 1080,
            'format': 'JPEG'
        }
        
        temp_path = '/tmp/test_image.jpg'
        result = self.service._prepare_metadata(temp_path, self.config_params)
        
        # Verificar que se combinan metadatos de imagen y configuración
        expected_keys = ['width', 'height', 'format', 'confidence_threshold', 'analysis_type', 'region']
        for key in expected_keys:
            self.assertIn(key, result)
        
        self.assertEqual(result['confidence_threshold'], 0.7)
        self.assertEqual(result['width'], 1920)
        mock_get_metadata.assert_called_once_with(temp_path)
        print("✓ test_prepare_metadata: EXITOSO")
    
    @patch('src.utils.helpers.encode_image_to_base64')
    def test_encode_image_success(self, mock_encode):
        """Test: Codificación exitosa de imagen."""
        mock_encode.return_value = ('base64_encoded_data', 'jpeg')
        
        result = self.service._encode_image('/tmp/test_image.jpg')
        
        self.assertEqual(result, ('base64_encoded_data', 'jpeg'))
        mock_encode.assert_called_once_with('/tmp/test_image.jpg')
        print("✓ test_encode_image_success: EXITOSO")
    
    @patch('src.utils.helpers.encode_image_to_base64', side_effect=ImportError)
    @patch('builtins.open', create=True)
    @patch('base64.b64encode')
    def test_encode_image_fallback(self, mock_b64encode, mock_open, mock_encode):
        """Test: Codificación con fallback cuando no está disponible la función helper."""
        # Configurar mocks para fallback
        mock_file_data = b'fake_image_data'
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_data
        mock_b64encode.return_value = b'ZmFrZV9pbWFnZV9kYXRh'
        
        result = self.service._encode_image('/tmp/test_image.jpg')
        
        self.assertEqual(result, ('ZmFrZV9pbWFnZV9kYXRh', 'jpeg'))
        mock_open.assert_called_once_with('/tmp/test_image.jpg', 'rb')
        mock_b64encode.assert_called_once_with(mock_file_data)
        print("✓ test_encode_image_fallback: EXITOSO")
    
    def test_apply_confidence_filter_above_threshold(self):
        """Test: Filtro de confianza cuando está por encima del umbral."""
        results = {'confidence': 0.85, 'analysis': 'test'}
        confidence_threshold = 0.7
        
        self.service._apply_confidence_filter(results, confidence_threshold)
        
        # No debe agregar warning
        self.assertNotIn('warning', results)
        print("✓ test_apply_confidence_filter_above_threshold: EXITOSO")
    
    def test_apply_confidence_filter_below_threshold(self):
        """Test: Filtro de confianza cuando está por debajo del umbral."""
        results = {'confidence': 0.65, 'analysis': 'test'}
        confidence_threshold = 0.7
        
        self.service._apply_confidence_filter(results, confidence_threshold)
        
        # Debe agregar warning
        self.assertIn('warning', results)
        self.assertIn('0.7', results['warning'])
        print("✓ test_apply_confidence_filter_below_threshold: EXITOSO")
    
    def test_apply_confidence_filter_zero_threshold(self):
        """Test: Filtro de confianza con umbral cero (deshabilitado)."""
        results = {'confidence': 0.3, 'analysis': 'test'}
        confidence_threshold = 0
        
        self.service._apply_confidence_filter(results, confidence_threshold)
        
        # No debe agregar warning cuando threshold es 0
        self.assertNotIn('warning', results)
        print("✓ test_apply_confidence_filter_zero_threshold: EXITOSO")
    
    @patch('src.utils.helpers.save_analysis_results_with_filename')
    @patch('src.services.analysis_service.datetime')
    def test_save_results(self, mock_datetime, mock_save):
        """Test: Guardado de resultados de análisis."""
        mock_datetime.now.return_value.strftime.return_value = '20240101_120000'
        mock_save.return_value = '/results/analysis_20240101_120000.json'
        
        results = {'confidence': 0.85, 'analysis': 'test'}
        save_path = self.service._save_results(results)
        
        self.assertEqual(save_path, '/results/analysis_20240101_120000.json')
        mock_save.assert_called_once_with(results, 'analysis_20240101_120000.json')
        print("✓ test_save_results: EXITOSO")
    
    @patch.object(AnalysisService, '_save_temp_image')
    @patch.object(AnalysisService, '_prepare_metadata')
    @patch.object(AnalysisService, '_encode_image')
    @patch.object(AnalysisService, '_apply_confidence_filter')
    @patch.object(AnalysisService, '_save_results')
    def test_analyze_image_success(self, mock_save, mock_filter, mock_encode, 
                                 mock_prepare, mock_save_temp):
        """Test: Análisis exitoso de imagen completo."""
        # Configurar mocks
        mock_save_temp.return_value = '/tmp/test_image.jpg'
        mock_prepare.return_value = {'width': 1920, 'confidence_threshold': 0.7}
        mock_encode.return_value = ('base64_data', 'jpeg')
        mock_save.return_value = '/results/analysis_result.json'
        
        result = self.service.analyze_image(self.mock_image_file, self.config_params)
        
        # Verificar resultado exitoso
        self.assertEqual(result['status'], 'completed')
        self.assertIn('results', result)
        self.assertIn('saved_path', result)
        self.assertEqual(result['saved_path'], '/results/analysis_result.json')
        
        # Verificar que se llamaron todos los métodos
        mock_save_temp.assert_called_once_with(self.mock_image_file)
        mock_prepare.assert_called_once_with('/tmp/test_image.jpg', self.config_params)
        mock_encode.assert_called_once_with('/tmp/test_image.jpg')
        self.mock_analyzer.analyze_image.assert_called_once_with(
            'base64_data', {'width': 1920, 'confidence_threshold': 0.7}, 'jpeg'
        )
        mock_filter.assert_called_once()
        mock_save.assert_called_once()
        print("✓ test_analyze_image_success: EXITOSO")
    
    @patch.object(AnalysisService, '_save_temp_image')
    @patch.object(AnalysisService, '_prepare_metadata')
    @patch.object(AnalysisService, '_encode_image')
    def test_analyze_image_encode_error(self, mock_encode, mock_prepare, mock_save_temp):
        """Test: Error en codificación de imagen."""
        # Configurar mocks
        mock_save_temp.return_value = '/tmp/test_image.jpg'
        mock_prepare.return_value = {'width': 1920}
        mock_encode.return_value = None  # Simular error en codificación
        
        result = self.service.analyze_image(self.mock_image_file, self.config_params)
        
        # Verificar error de codificación
        self.assertEqual(result['status'], 'error')
        self.assertIn('error', result)
        self.assertIn('Formato no compatible', result['error'])
        print("✓ test_analyze_image_encode_error: EXITOSO")
    
    @patch.object(AnalysisService, '_save_temp_image', side_effect=Exception("Temp save error"))
    def test_analyze_image_exception(self, mock_save_temp):
        """Test: Manejo de excepciones generales."""
        result = self.service.analyze_image(self.mock_image_file, self.config_params)
        
        # Verificar manejo de excepción
        self.assertEqual(result['status'], 'error')
        self.assertIn('error', result)
        self.assertIn('Temp save error', result['error'])
        print("✓ test_analyze_image_exception: EXITOSO")
    
    @patch('flask.send_from_directory')
    @patch('os.path.join')
    @patch('os.path.dirname')
    @patch('os.path.abspath')
    def test_serve_result_file(self, mock_abspath, mock_dirname, mock_join, mock_send):
        """Test: Servir archivo de resultados."""
        # Configurar path esperado
        mock_abspath.return_value = '/app/src/services/analysis_service.py'
        mock_dirname.side_effect = ['/app/src/services', '/app/src', '/app']
        mock_join.return_value = '/app/results'
        
        filename = 'analysis_result.json'
        self.service.serve_result_file(filename)
        
        mock_send.assert_called_once_with('/app/results', filename)
        print("✓ test_serve_result_file: EXITOSO")
    
    def test_get_analysis_status(self):
        """Test: Obtener estado de análisis."""
        analysis_id = 'test_analysis_123'
        
        result = self.service.get_analysis_status(analysis_id)
        
        # Verificar estructura del resultado
        self.assertEqual(result['id'], analysis_id)
        self.assertEqual(result['status'], 'processing')
        self.assertIn('progress', result)
        self.assertIn('estimated_time_remaining', result)
        self.assertIsInstance(result['progress'], int)
        print("✓ test_get_analysis_status: EXITOSO")
    
    def test_analyze_image_with_default_confidence(self):
        """Test: Análisis con umbral de confianza por defecto."""
        config_without_threshold = {'analysis_type': 'basic'}
        
        # Mock solo los métodos necesarios
        with patch.object(self.service, '_save_temp_image', return_value='/tmp/test.jpg'), \
             patch.object(self.service, '_prepare_metadata', return_value={}), \
             patch.object(self.service, '_encode_image', return_value=('data', 'jpeg')), \
             patch.object(self.service, '_save_results', return_value='/path/result.json'):
            
            result = self.service.analyze_image(self.mock_image_file, config_without_threshold)
            
            # Verificar que se usa umbral por defecto (0)
            self.assertEqual(result['status'], 'completed')
            print("✓ test_analyze_image_with_default_confidence: EXITOSO")


if __name__ == '__main__':
    print("🔬 EJECUTANDO TESTS DE ANALYSIS SERVICE")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAnalysisService)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE ANALYSIS SERVICE:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE ANALYSIS SERVICE PASAN! 🎉")
