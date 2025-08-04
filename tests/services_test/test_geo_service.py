#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests completos para GeoService del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad del servicio de geolocalización:
- Gestión de imágenes de referencia
- Detección de cambios con correlación real y mock
- Triangulación real y simulada  
- Manejo de observaciones
- Estados de objetivos
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.geo_service import GeoService


class TestGeoService(unittest.TestCase):
    """Tests para la clase GeoService."""
    
    def setUp(self):
        """Configurar tests con mocks y datos de prueba."""
        # Mock del geo_manager
        self.mock_geo_manager = MagicMock()
        self.mock_geo_manager.current_reference_image = None
        self.mock_geo_manager.targets = {}
        
        # Mock del geo_triangulation
        self.mock_geo_triangulation = MagicMock()
        self.mock_geo_triangulation.observations = {}
        
        # Mock del geo_correlator  
        self.mock_geo_correlator = MagicMock()
        
        # Crear instancia del servicio
        self.service = GeoService(
            self.mock_geo_manager, 
            self.mock_geo_triangulation, 
            self.mock_geo_correlator
        )
    
    def test_geo_service_init(self):
        """Test: Inicialización correcta del servicio."""
        service = GeoService(
            self.mock_geo_manager,
            self.mock_geo_triangulation,
            self.mock_geo_correlator
        )
        
        self.assertEqual(service.geo_manager, self.mock_geo_manager)
        self.assertEqual(service.geo_triangulation, self.mock_geo_triangulation)
        self.assertEqual(service.geo_correlator, self.mock_geo_correlator)
        print("✓ test_geo_service_init: EXITOSO")
    
    def test_is_mock_module_detection(self):
        """Test: Detección correcta de módulos mock."""
        # Mock real debería ser detectado como mock
        mock_module = MagicMock()
        result = self.service._is_mock_module(mock_module)
        self.assertTrue(result)
        
        # Objeto sin 'Mock' en el nombre no debería ser detectado como mock
        class RealModule:
            pass
        
        real_module = RealModule()
        result = self.service._is_mock_module(real_module)
        self.assertFalse(result)
        
        print("✓ test_is_mock_module_detection: EXITOSO")
    
    @patch.object(GeoService, '_get_mock_telemetry')
    def test_add_reference_image_success(self, mock_telemetry):
        """Test: Agregar imagen de referencia exitosamente."""
        mock_telemetry.return_value = {
            'gps': {'latitude': 40.0, 'longitude': -3.0},
            'timestamp': 1234567890
        }
        self.mock_geo_manager.add_reference_image.return_value = 'ref_001'
        
        result = self.service.add_reference_image()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['reference_id'], 'ref_001')
        self.mock_geo_manager.add_reference_image.assert_called_once()
        print("✓ test_add_reference_image_success: EXITOSO")
    
    @patch.object(GeoService, '_get_mock_telemetry')
    def test_add_reference_image_exception(self, mock_telemetry):
        """Test: Excepción al agregar imagen de referencia."""
        mock_telemetry.side_effect = Exception("Telemetry error")
        
        result = self.service.add_reference_image()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Telemetry error', result['error'])
        print("✓ test_add_reference_image_exception: EXITOSO")
    
    def test_detect_changes_no_reference(self):
        """Test: Detección de cambios sin imagen de referencia."""
        self.mock_geo_manager.current_reference_image = None
        
        result = self.service.detect_changes()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('No hay imagen de referencia', result['error'])
        print("✓ test_detect_changes_no_reference: EXITOSO")
    
    @patch.object(GeoService, '_detect_changes_real')
    def test_detect_changes_with_real_correlator(self, mock_detect_real):
        """Test: Detección de cambios con correlador real."""
        self.mock_geo_manager.current_reference_image = 'ref_001'
        self.service.is_mock_correlator = False  # Simular correlador real
        mock_detect_real.return_value = {
            'success': True,
            'has_changes': True,
            'change_percentage': 25.5
        }
        
        result = self.service.detect_changes()
        
        self.assertTrue(result['success'])
        self.assertTrue(result['has_changes'])
        self.assertEqual(result['change_percentage'], 25.5)
        mock_detect_real.assert_called_once()
        print("✓ test_detect_changes_with_real_correlator: EXITOSO")
    
    @patch.object(GeoService, '_detect_changes_mock')
    def test_detect_changes_with_mock_correlator(self, mock_detect_mock):
        """Test: Detección de cambios con correlador mock."""
        self.mock_geo_manager.current_reference_image = 'ref_001'
        self.service.is_mock_correlator = True  # Simular correlador mock
        mock_detect_mock.return_value = {
            'success': True,
            'has_changes': True,
            'change_percentage': 15.7,
            'note': 'Resultado simulado'
        }
        
        result = self.service.detect_changes()
        
        self.assertTrue(result['success'])
        self.assertTrue(result['has_changes'])
        self.assertEqual(result['change_percentage'], 15.7)
        self.assertIn('note', result)
        mock_detect_mock.assert_called_once()
        print("✓ test_detect_changes_with_mock_correlator: EXITOSO")
    
    def test_detect_changes_exception(self):
        """Test: Excepción durante detección de cambios."""
        self.mock_geo_manager.current_reference_image = 'ref_001'
        with patch.object(self.service, '_detect_changes_mock', side_effect=Exception("Detection error")):
            result = self.service.detect_changes()
            
            self.assertFalse(result['success'])
            self.assertIn('error', result)
            self.assertIn('Detection error', result['error'])
        
        print("✓ test_detect_changes_exception: EXITOSO")
    
    def test_create_target_with_real_triangulation(self):
        """Test: Crear objetivo con triangulación real."""
        self.service.is_mock_triangulation = False
        self.mock_geo_triangulation.create_target.return_value = 'target_001'
        
        result = self.service.create_target()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['target_id'], 'target_001')
        self.mock_geo_triangulation.create_target.assert_called_once()
        
        # Verificar que se registró en el gestor local
        self.assertIn('target_001', self.mock_geo_manager.targets)
        print("✓ test_create_target_with_real_triangulation: EXITOSO")
    
    def test_create_target_with_mock_triangulation(self):
        """Test: Crear objetivo con triangulación mock (fallback)."""
        self.service.is_mock_triangulation = True
        self.mock_geo_manager.create_target.return_value = 'target_fallback_001'
        
        result = self.service.create_target()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['target_id'], 'target_fallback_001')
        self.assertIn('note', result)
        self.assertIn('fallback', result['note'])
        self.mock_geo_manager.create_target.assert_called_once()
        print("✓ test_create_target_with_mock_triangulation: EXITOSO")
    
    def test_create_target_exception(self):
        """Test: Excepción durante creación de objetivo."""
        self.service.is_mock_triangulation = False
        self.mock_geo_triangulation.create_target.side_effect = Exception("Target creation error")
        
        result = self.service.create_target()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Target creation error', result['error'])
        print("✓ test_create_target_exception: EXITOSO")
    
    def test_calculate_position_empty_target_id(self):
        """Test: Calcular posición con ID de objetivo vacío."""
        result = self.service.calculate_position("")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('ID de objetivo no especificado', result['error'])
        print("✓ test_calculate_position_empty_target_id: EXITOSO")
    
    @patch.object(GeoService, '_calculate_position_real')
    def test_calculate_position_with_real_triangulation(self, mock_calc_real):
        """Test: Calcular posición con triangulación real."""
        self.service.is_mock_triangulation = False
        mock_calc_real.return_value = {
            'success': True,
            'position': {'latitude': 40.1, 'longitude': -3.1},
            'precision': {'confidence': 85.0, 'error_radius': 15.0}
        }
        
        result = self.service.calculate_position('target_001')
        
        self.assertTrue(result['success'])
        self.assertIn('position', result)
        self.assertIn('precision', result)
        mock_calc_real.assert_called_once_with('target_001')
        print("✓ test_calculate_position_with_real_triangulation: EXITOSO")
    
    @patch.object(GeoService, '_calculate_position_mock')
    def test_calculate_position_with_mock_triangulation(self, mock_calc_mock):
        """Test: Calcular posición con triangulación mock."""
        self.service.is_mock_triangulation = True
        mock_calc_mock.return_value = {
            'success': True,
            'position': {'latitude': 40.2, 'longitude': -3.2},
            'method': 'simulated',
            'note': 'Resultado simulado'
        }
        
        result = self.service.calculate_position('target_001')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['method'], 'simulated')
        self.assertIn('note', result)
        mock_calc_mock.assert_called_once_with('target_001')
        print("✓ test_calculate_position_with_mock_triangulation: EXITOSO")
    
    def test_calculate_position_exception(self):
        """Test: Excepción durante cálculo de posición."""
        with patch.object(self.service, '_calculate_position_mock', side_effect=Exception("Calc error")):
            result = self.service.calculate_position('target_001')
            
            self.assertFalse(result['success'])
            self.assertIn('error', result)
            self.assertIn('Calc error', result['error'])
        
        print("✓ test_calculate_position_exception: EXITOSO")
    
    @patch.object(GeoService, '_get_mock_drone_position')
    def test_add_observation_with_real_triangulation(self, mock_position):
        """Test: Agregar observación con triangulación real."""
        self.service.is_mock_triangulation = False
        mock_position.return_value = {
            'latitude': 40.416775,
            'longitude': -3.703790,
            'altitude': 50
        }
        
        observation_params = {
            'target_id': 'target_001',
            'target_bearing': 45.0,
            'target_elevation': 15.0,
            'confidence': 0.9
        }
        
        self.mock_geo_triangulation.add_observation.return_value = 'obs_001'
        self.mock_geo_triangulation.observations = {'target_001': [{'id': 'obs_001'}]}
        
        result = self.service.add_observation(observation_params)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['observation_id'], 'obs_001')
        self.assertEqual(result['total_observations'], 1)
        self.assertFalse(result['can_calculate'])  # Solo 1 observación, necesita >= 2
        
        self.mock_geo_triangulation.add_observation.assert_called_once_with(
            target_id='target_001',
            drone_position=mock_position.return_value,
            target_bearing=45.0,
            target_elevation=15.0,
            confidence=0.9
        )
        print("✓ test_add_observation_with_real_triangulation: EXITOSO")
    
    def test_add_observation_with_mock_triangulation(self):
        """Test: Agregar observación con triangulación mock."""
        self.service.is_mock_triangulation = True
        
        observation_params = {
            'target_id': 'target_001',
            'target_bearing': 45.0
        }
        
        result = self.service.add_observation(observation_params)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Módulo de triangulación no disponible', result['error'])
        print("✓ test_add_observation_with_mock_triangulation: EXITOSO")
    
    def test_add_observation_exception(self):
        """Test: Excepción durante agregar observación."""
        self.service.is_mock_triangulation = False
        
        observation_params = {
            'target_id': 'target_001',
            'target_bearing': 'invalid_bearing'  # Tipo inválido
        }
        
        result = self.service.add_observation(observation_params)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        print("✓ test_add_observation_exception: EXITOSO")
    
    def test_get_targets_status_with_real_triangulation(self):
        """Test: Obtener estado de objetivos con triangulación real."""
        self.service.is_mock_triangulation = False
        
        # Configurar datos de prueba
        targets = ['target_001', 'target_002']
        self.mock_geo_triangulation.get_all_targets.return_value = targets
        self.mock_geo_triangulation.observations = {
            'target_001': [
                {'timestamp': '2024-01-01T12:00:00'},
                {'timestamp': '2024-01-01T12:05:00'}
            ],
            'target_002': [
                {'timestamp': '2024-01-01T12:10:00'}
            ]
        }
        
        result = self.service.get_targets_status()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_targets'], 2)
        self.assertIsInstance(result['targets'], list)
        
        # Verificar primer objetivo
        target_1 = result['targets'][0]
        self.assertEqual(target_1['target_id'], 'target_001')
        self.assertEqual(target_1['observations_count'], 2)
        self.assertTrue(target_1['can_calculate'])  # >= 2 observaciones
        
        # Verificar segundo objetivo
        target_2 = result['targets'][1]
        self.assertEqual(target_2['target_id'], 'target_002')
        self.assertEqual(target_2['observations_count'], 1)
        self.assertFalse(target_2['can_calculate'])  # < 2 observaciones
        
        print("✓ test_get_targets_status_with_real_triangulation: EXITOSO")
    
    def test_get_targets_status_with_mock_triangulation(self):
        """Test: Obtener estado de objetivos con triangulación mock."""
        self.service.is_mock_triangulation = True
        
        result = self.service.get_targets_status()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Módulo de triangulación no disponible', result['error'])
        print("✓ test_get_targets_status_with_mock_triangulation: EXITOSO")
    
    def test_get_targets_status_exception(self):
        """Test: Excepción durante obtener estado de objetivos."""
        self.service.is_mock_triangulation = False
        self.mock_geo_triangulation.get_all_targets.side_effect = Exception("Status error")
        
        result = self.service.get_targets_status()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Status error', result['error'])
        print("✓ test_get_targets_status_exception: EXITOSO")
    
    @patch.object(GeoService, '_get_mock_telemetry')
    def test_detect_changes_real_success(self, mock_telemetry):
        """Test: Detección de cambios real exitosa."""
        mock_telemetry.return_value = {
            'gps': {'latitude': 40.0, 'longitude': -3.0},
            'timestamp': 1234567890
        }
        
        self.mock_geo_correlator.correlate_drone_image.return_value = {
            'confidence': 0.75,
            'correlation_data': 'test_data'
        }
        
        result = self.service._detect_changes_real()
        
        self.assertTrue(result['success'])
        self.assertTrue(result['has_changes'])  # confidence < 0.8
        self.assertEqual(result['change_percentage'], 25.0)  # (1 - 0.75) * 100
        self.assertEqual(result['correlation_confidence'], 0.75)
        print("✓ test_detect_changes_real_success: EXITOSO")
    
    @patch.object(GeoService, '_get_mock_telemetry')
    def test_detect_changes_real_error(self, mock_telemetry):
        """Test: Error en detección de cambios real."""
        mock_telemetry.return_value = {
            'gps': {'latitude': 40.0, 'longitude': -3.0},
            'timestamp': 1234567890
        }
        
        self.mock_geo_correlator.correlate_drone_image.return_value = {
            'error': 'Correlation failed'
        }
        
        result = self.service._detect_changes_real()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Correlation failed')
        print("✓ test_detect_changes_real_error: EXITOSO")
    
    def test_detect_changes_mock(self):
        """Test: Detección de cambios mock."""
        result = self.service._detect_changes_mock()
        
        self.assertTrue(result['success'])
        self.assertTrue(result['has_changes'])
        self.assertEqual(result['change_percentage'], 15.7)
        self.assertIn('note', result)
        self.assertIn('simulado', result['note'])
        print("✓ test_detect_changes_mock: EXITOSO")
    
    @patch.object(GeoService, '_add_automatic_observations')
    def test_calculate_position_real_with_observations(self, mock_auto_obs):
        """Test: Cálculo de posición real con observaciones existentes."""
        target_id = 'target_001'
        self.mock_geo_triangulation.observations = {
            target_id: [{'id': 'obs_1'}, {'id': 'obs_2'}]  # 2 observaciones
        }
        
        self.mock_geo_triangulation.calculate_position.return_value = {
            'position': {'latitude': 40.1, 'longitude': -3.1},
            'precision': {'confidence': 85.0, 'error_radius': 15.0},
            'observations_count': 2,
            'timestamp': '2024-01-01T12:00:00'
        }
        
        result = self.service._calculate_position_real(target_id)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['method'], 'real_triangulation')
        self.assertIn('position', result)
        self.assertIn('precision', result)
        
        # No debe agregar observaciones automáticas
        mock_auto_obs.assert_not_called()
        print("✓ test_calculate_position_real_with_observations: EXITOSO")
    
    @patch.object(GeoService, '_add_automatic_observations')
    def test_calculate_position_real_without_observations(self, mock_auto_obs):
        """Test: Cálculo de posición real sin observaciones suficientes."""
        target_id = 'target_001'
        self.mock_geo_triangulation.observations = {}  # Sin observaciones
        
        self.mock_geo_triangulation.calculate_position.return_value = {
            'position': {'latitude': 40.1, 'longitude': -3.1},
            'precision': {'confidence': 85.0, 'error_radius': 15.0},
            'observations_count': 2,
            'timestamp': '2024-01-01T12:00:00'
        }
        
        result = self.service._calculate_position_real(target_id)
        
        self.assertTrue(result['success'])
        
        # Debe agregar observaciones automáticas
        mock_auto_obs.assert_called_once_with(target_id)
        print("✓ test_calculate_position_real_without_observations: EXITOSO")
    
    def test_calculate_position_real_error(self):
        """Test: Error en cálculo de posición real."""
        target_id = 'target_001'
        self.mock_geo_triangulation.observations = {target_id: [{'id': 'obs_1'}, {'id': 'obs_2'}]}
        
        self.mock_geo_triangulation.calculate_position.return_value = {
            'error': 'Insufficient data'
        }
        
        result = self.service._calculate_position_real(target_id)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Insufficient data')
        print("✓ test_calculate_position_real_error: EXITOSO")
    
    def test_calculate_position_mock(self):
        """Test: Cálculo de posición mock."""
        target_id = 'target_001'
        
        result = self.service._calculate_position_mock(target_id)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['method'], 'simulated')
        self.assertIn('position', result)
        self.assertIn('precision', result)
        self.assertIn('note', result)
        
        # Verificar que la posición es determinística basada en el target_id
        expected_lat = 40.416775 + (hash(target_id) % 100) / 10000
        expected_lng = -3.703790 + (hash(target_id[::-1]) % 100) / 10000
        
        self.assertAlmostEqual(result['position']['latitude'], expected_lat, places=5)
        self.assertAlmostEqual(result['position']['longitude'], expected_lng, places=5)
        print("✓ test_calculate_position_mock: EXITOSO")
    
    def test_add_automatic_observations(self):
        """Test: Agregar observaciones automáticas."""
        target_id = 'target_001'
        
        self.service._add_automatic_observations(target_id)
        
        # Verificar que se agregaron 2 observaciones
        self.assertEqual(self.mock_geo_triangulation.add_observation.call_count, 2)
        
        # Verificar parámetros de las llamadas
        calls = self.mock_geo_triangulation.add_observation.call_args_list
        
        # Primera observación
        call_1 = calls[0][1]  # kwargs
        self.assertEqual(call_1['target_id'], target_id)
        self.assertEqual(call_1['target_bearing'], 45.0)
        self.assertEqual(call_1['target_elevation'], 15.0)
        self.assertEqual(call_1['confidence'], 0.9)
        
        # Segunda observación
        call_2 = calls[1][1]  # kwargs
        self.assertEqual(call_2['target_id'], target_id)
        self.assertEqual(call_2['target_bearing'], 50.0)
        self.assertEqual(call_2['target_elevation'], 12.0)
        self.assertEqual(call_2['confidence'], 0.85)
        
        print("✓ test_add_automatic_observations: EXITOSO")
    
    def test_get_mock_telemetry(self):
        """Test: Obtener telemetría simulada."""
        result = self.service._get_mock_telemetry()
        
        expected_keys = ['gps', 'timestamp']
        for key in expected_keys:
            self.assertIn(key, result)
        
        # Verificar estructura del GPS
        gps = result['gps']
        self.assertIn('latitude', gps)
        self.assertIn('longitude', gps)
        self.assertEqual(gps['latitude'], 40.416775)
        self.assertEqual(gps['longitude'], -3.703790)
        
        # Verificar tipo de timestamp
        self.assertIsInstance(result['timestamp'], float)
        print("✓ test_get_mock_telemetry: EXITOSO")
    
    def test_get_mock_drone_position(self):
        """Test: Obtener posición simulada del dron."""
        result = self.service._get_mock_drone_position()
        
        expected_keys = ['latitude', 'longitude', 'altitude']
        for key in expected_keys:
            self.assertIn(key, result)
        
        self.assertEqual(result['latitude'], 40.416775)
        self.assertEqual(result['longitude'], -3.703790)
        self.assertEqual(result['altitude'], 50)
        print("✓ test_get_mock_drone_position: EXITOSO")


if __name__ == '__main__':
    print("🌍 EJECUTANDO TESTS DE GEO SERVICE")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGeoService)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE GEO SERVICE:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE GEO SERVICE PASAN! 🎉")
