#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests completos para DroneService del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad del servicio de drones:
- Conexión y desconexión de drones
- Operaciones de vuelo (despegue, aterrizaje)
- Streaming de video
- Telemetría y datos de posición
- Simulaciones y rutas predefinidas
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, Mock
import time

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.drone_service import DroneService


class TestDroneService(unittest.TestCase):
    """Tests para la clase DroneService."""
    
    def setUp(self):
        """Configurar tests con mocks y datos de prueba."""
        # Mock del controlador de dron
        self.mock_drone_controller = MagicMock()
        self.mock_drone_controller.current_position = {
            'latitude': 40.416775,
            'longitude': -3.703790
        }
        
        # Mock del procesador de video
        self.mock_video_processor = MagicMock()
        
        # Crear instancia del servicio
        self.service = DroneService(self.mock_drone_controller, self.mock_video_processor)
    
    def test_drone_service_init(self):
        """Test: Inicialización correcta del servicio."""
        service = DroneService(self.mock_drone_controller, self.mock_video_processor)
        
        self.assertEqual(service.drone_controller, self.mock_drone_controller)
        self.assertEqual(service.video_processor, self.mock_video_processor)
        print("✓ test_drone_service_init: EXITOSO")
    
    def test_connect_success(self):
        """Test: Conexión exitosa con el dron."""
        self.mock_drone_controller.connect.return_value = True
        
        result = self.service.connect()
        
        self.assertTrue(result['success'])
        self.assertIn('position', result)
        self.assertEqual(result['position']['latitude'], 40.416775)
        self.assertEqual(result['position']['longitude'], -3.703790)
        self.mock_drone_controller.connect.assert_called_once()
        print("✓ test_connect_success: EXITOSO")
    
    def test_connect_failure(self):
        """Test: Fallo en conexión con el dron."""
        self.mock_drone_controller.connect.return_value = False
        
        result = self.service.connect()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Error al conectar', result['error'])
        print("✓ test_connect_failure: EXITOSO")
    
    def test_connect_exception(self):
        """Test: Excepción durante conexión."""
        self.mock_drone_controller.connect.side_effect = Exception("Connection timeout")
        
        result = self.service.connect()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Connection timeout', result['error'])
        print("✓ test_connect_exception: EXITOSO")
    
    def test_disconnect_success(self):
        """Test: Desconexión exitosa del dron."""
        self.mock_drone_controller.disconnect.return_value = True
        
        result = self.service.disconnect()
        
        self.assertTrue(result['success'])
        self.mock_drone_controller.disconnect.assert_called_once()
        print("✓ test_disconnect_success: EXITOSO")
    
    def test_disconnect_failure(self):
        """Test: Fallo en desconexión del dron."""
        self.mock_drone_controller.disconnect.return_value = False
        
        result = self.service.disconnect()
        
        self.assertFalse(result['success'])
        print("✓ test_disconnect_failure: EXITOSO")
    
    def test_disconnect_exception(self):
        """Test: Excepción durante desconexión."""
        self.mock_drone_controller.disconnect.side_effect = Exception("Disconnect error")
        
        result = self.service.disconnect()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Disconnect error', result['error'])
        print("✓ test_disconnect_exception: EXITOSO")
    
    def test_takeoff_valid_altitude(self):
        """Test: Despegue con altitud válida."""
        altitude = 50.0
        self.mock_drone_controller.take_off.return_value = True
        
        result = self.service.takeoff(altitude)
        
        self.assertTrue(result['success'])
        self.mock_drone_controller.take_off.assert_called_once_with(altitude)
        print("✓ test_takeoff_valid_altitude: EXITOSO")
    
    def test_takeoff_invalid_altitude_too_high(self):
        """Test: Despegue con altitud demasiado alta."""
        altitude = 150.0  # Excede el límite de 120m
        
        result = self.service.takeoff(altitude)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Altitud inválida', result['error'])
        self.assertIn('120m', result['error'])
        # No debe llamar al controlador
        self.mock_drone_controller.take_off.assert_not_called()
        print("✓ test_takeoff_invalid_altitude_too_high: EXITOSO")
    
    def test_takeoff_invalid_altitude_zero(self):
        """Test: Despegue con altitud cero o negativa."""
        altitude = 0.0
        
        result = self.service.takeoff(altitude)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Altitud inválida', result['error'])
        print("✓ test_takeoff_invalid_altitude_zero: EXITOSO")
    
    def test_takeoff_controller_failure(self):
        """Test: Fallo del controlador durante despegue."""
        altitude = 50.0
        self.mock_drone_controller.take_off.return_value = False
        
        result = self.service.takeoff(altitude)
        
        self.assertFalse(result['success'])
        print("✓ test_takeoff_controller_failure: EXITOSO")
    
    def test_takeoff_exception(self):
        """Test: Excepción durante despegue."""
        altitude = 50.0
        self.mock_drone_controller.take_off.side_effect = Exception("Takeoff error")
        
        result = self.service.takeoff(altitude)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Takeoff error', result['error'])
        print("✓ test_takeoff_exception: EXITOSO")
    
    def test_land_success(self):
        """Test: Aterrizaje exitoso."""
        self.mock_drone_controller.land.return_value = True
        
        result = self.service.land()
        
        self.assertTrue(result['success'])
        self.mock_drone_controller.land.assert_called_once()
        print("✓ test_land_success: EXITOSO")
    
    def test_land_failure(self):
        """Test: Fallo en aterrizaje."""
        self.mock_drone_controller.land.return_value = False
        
        result = self.service.land()
        
        self.assertFalse(result['success'])
        print("✓ test_land_failure: EXITOSO")
    
    def test_land_exception(self):
        """Test: Excepción durante aterrizaje."""
        self.mock_drone_controller.land.side_effect = Exception("Landing error")
        
        result = self.service.land()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Landing error', result['error'])
        print("✓ test_land_exception: EXITOSO")
    
    def test_start_video_stream_success(self):
        """Test: Inicio exitoso de streaming de video."""
        stream_url = 'rtmp://test.stream.url/live'
        self.mock_drone_controller.start_video_stream.return_value = stream_url
        self.mock_video_processor.start_processing.return_value = True
        
        result = self.service.start_video_stream()
        
        self.assertTrue(result['success'])
        self.mock_drone_controller.start_video_stream.assert_called_once()
        self.mock_video_processor.start_processing.assert_called_once_with(stream_url)
        print("✓ test_start_video_stream_success: EXITOSO")
    
    def test_start_video_stream_processor_failure(self):
        """Test: Fallo del procesador de video."""
        stream_url = 'rtmp://test.stream.url/live'
        self.mock_drone_controller.start_video_stream.return_value = stream_url
        self.mock_video_processor.start_processing.return_value = False
        
        result = self.service.start_video_stream()
        
        self.assertFalse(result['success'])
        print("✓ test_start_video_stream_processor_failure: EXITOSO")
    
    def test_start_video_stream_exception(self):
        """Test: Excepción durante inicio de stream."""
        self.mock_drone_controller.start_video_stream.side_effect = Exception("Stream error")
        
        result = self.service.start_video_stream()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Stream error', result['error'])
        print("✓ test_start_video_stream_exception: EXITOSO")
    
    def test_stop_video_stream_success(self):
        """Test: Parada exitosa de streaming de video."""
        self.mock_drone_controller.stop_video_stream.return_value = True
        
        result = self.service.stop_video_stream()
        
        self.assertTrue(result['success'])
        self.mock_video_processor.stop_processing.assert_called_once()
        self.mock_drone_controller.stop_video_stream.assert_called_once()
        print("✓ test_stop_video_stream_success: EXITOSO")
    
    def test_stop_video_stream_controller_failure(self):
        """Test: Fallo del controlador al parar stream."""
        self.mock_drone_controller.stop_video_stream.return_value = False
        
        result = self.service.stop_video_stream()
        
        self.assertFalse(result['success'])
        # Debe intentar parar el processor de todos modos
        self.mock_video_processor.stop_processing.assert_called_once()
        print("✓ test_stop_video_stream_controller_failure: EXITOSO")
    
    def test_stop_video_stream_exception(self):
        """Test: Excepción durante parada de stream."""
        self.mock_video_processor.stop_processing.side_effect = Exception("Stop error")
        
        result = self.service.stop_video_stream()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Stop error', result['error'])
        print("✓ test_stop_video_stream_exception: EXITOSO")
    
    def test_get_telemetry_success(self):
        """Test: Obtención exitosa de telemetría."""
        telemetry_data = {
            'battery': 85,
            'altitude': 50.5,
            'speed': 12.3,
            'heading': 180
        }
        self.mock_drone_controller.get_telemetry.return_value = telemetry_data
        
        result = self.service.get_telemetry()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['telemetry'], telemetry_data)
        self.mock_drone_controller.get_telemetry.assert_called_once()
        print("✓ test_get_telemetry_success: EXITOSO")
    
    def test_get_telemetry_exception(self):
        """Test: Excepción durante obtención de telemetría."""
        self.mock_drone_controller.get_telemetry.side_effect = Exception("Telemetry error")
        
        result = self.service.get_telemetry()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Telemetry error', result['error'])
        print("✓ test_get_telemetry_exception: EXITOSO")
    
    def test_get_simulation_paths_success(self):
        """Test: Obtención de rutas de simulación."""
        result = self.service.get_simulation_paths()
        
        self.assertTrue(result['success'])
        self.assertIn('paths', result)
        self.assertIsInstance(result['paths'], list)
        self.assertGreater(len(result['paths']), 0)
        
        # Verificar estructura de las rutas
        first_path = result['paths'][0]
        expected_keys = ['id', 'name', 'description', 'waypoints']
        for key in expected_keys:
            self.assertIn(key, first_path)
        
        # Verificar waypoints tienen estructura correcta
        waypoint = first_path['waypoints'][0]
        waypoint_keys = ['lat', 'lng', 'alt']
        for key in waypoint_keys:
            self.assertIn(key, waypoint)
        
        print("✓ test_get_simulation_paths_success: EXITOSO")
    
    def test_get_simulation_paths_exception(self):
        """Test: Excepción durante obtención de rutas."""
        # Simular excepción en el método interno
        with patch.object(self.service, '_generate_simulation_paths', side_effect=Exception("Path error")):
            result = self.service.get_simulation_paths()
            
            self.assertFalse(result['success'])
            self.assertIn('error', result)
            self.assertIn('Path error', result['error'])
        
        print("✓ test_get_simulation_paths_exception: EXITOSO")
    
    @patch('time.time')
    def test_start_simulation(self, mock_time):
        """Test: Inicio de simulación de vuelo."""
        mock_time.return_value = 1234567890
        path_id = 'route_1'
        
        result = self.service.start_simulation(path_id)
        
        self.assertTrue(result['success'])
        self.assertIn('message', result)
        self.assertIn('simulation_id', result)
        self.assertIn(path_id, result['message'])
        self.assertEqual(result['simulation_id'], 'sim_1234567890')
        print("✓ test_start_simulation: EXITOSO")
    
    def test_start_simulation_exception(self):
        """Test: Excepción durante inicio de simulación."""
        with patch('time.time', side_effect=Exception("Time error")):
            result = self.service.start_simulation('route_1')
            
            self.assertFalse(result['success'])
            self.assertIn('error', result)
            self.assertIn('Time error', result['error'])
        
        print("✓ test_start_simulation_exception: EXITOSO")
    
    def test_validate_altitude_valid_range(self):
        """Test: Validación de altitudes dentro del rango válido."""
        valid_altitudes = [1.0, 50.0, 120.0]
        
        for altitude in valid_altitudes:
            result = self.service._validate_altitude(altitude)
            self.assertTrue(result, f"Altitud {altitude} debería ser válida")
        
        print("✓ test_validate_altitude_valid_range: EXITOSO")
    
    def test_validate_altitude_invalid_range(self):
        """Test: Validación de altitudes fuera del rango válido."""
        invalid_altitudes = [0.0, -10.0, 121.0, 500.0]
        
        for altitude in invalid_altitudes:
            result = self.service._validate_altitude(altitude)
            self.assertFalse(result, f"Altitud {altitude} debería ser inválida")
        
        print("✓ test_validate_altitude_invalid_range: EXITOSO")
    
    def test_get_current_position_success(self):
        """Test: Obtención exitosa de posición actual."""
        result = self.service._get_current_position()
        
        expected_position = {
            'latitude': 40.416775,
            'longitude': -3.703790
        }
        self.assertEqual(result, expected_position)
        print("✓ test_get_current_position_success: EXITOSO")
    
    def test_get_current_position_fallback(self):
        """Test: Posición por defecto cuando falla la obtención."""
        # Simular fallo en acceso a current_position
        self.mock_drone_controller.current_position = None
        
        result = self.service._get_current_position()
        
        # Debe devolver posición por defecto
        expected_fallback = {'latitude': 40.416775, 'longitude': -3.703790}
        self.assertEqual(result, expected_fallback)
        print("✓ test_get_current_position_fallback: EXITOSO")
    
    def test_generate_simulation_paths_structure(self):
        """Test: Estructura correcta de rutas de simulación generadas."""
        paths = self.service._generate_simulation_paths()
        
        self.assertIsInstance(paths, list)
        self.assertEqual(len(paths), 3)  # Debe generar 3 rutas
        
        for i, path in enumerate(paths):
            # Verificar ID único
            self.assertEqual(path['id'], f'route_{i+1}')
            
            # Verificar campos requeridos
            self.assertIn('name', path)
            self.assertIn('description', path)
            self.assertIn('waypoints', path)
            
            # Verificar waypoints
            self.assertIsInstance(path['waypoints'], list)
            self.assertGreater(len(path['waypoints']), 5)  # Al menos 6 waypoints
            
            # Verificar estructura de waypoints
            for waypoint in path['waypoints']:
                self.assertIn('lat', waypoint)
                self.assertIn('lng', waypoint)
                self.assertIn('alt', waypoint)
                
                # Verificar tipos
                self.assertIsInstance(waypoint['lat'], float)
                self.assertIsInstance(waypoint['lng'], float)
                self.assertIsInstance(waypoint['alt'], int)
        
        print("✓ test_generate_simulation_paths_structure: EXITOSO")


if __name__ == '__main__':
    print("🚁 EJECUTANDO TESTS DE DRONE SERVICE")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDroneService)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE DRONE SERVICE:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE DRONE SERVICE PASAN! 🎉")
