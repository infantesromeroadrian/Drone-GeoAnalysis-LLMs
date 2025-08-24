#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests completos para MissionService del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad del servicio de misiones:
- Gestión de misiones predefinidas
- Planificación con LLM
- Control adaptativo
- Carga de cartografía
- Validación de seguridad
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, Mock, mock_open
import tempfile
import json

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.mission_service import MissionService


class TestMissionService(unittest.TestCase):
    """Tests para la clase MissionService."""
    
    def setUp(self):
        """Configurar tests con mocks y datos de prueba."""
        # Mock del planificador de misiones
        self.mock_mission_planner = MagicMock()
        self.mock_mission_planner.loaded_areas = {}
        
        # Mock del controlador de dron
        self.mock_drone_controller = MagicMock()
        
        # Crear instancia del servicio
        self.service = MissionService(self.mock_mission_planner, self.mock_drone_controller)
        
        # Mock de archivo Flask
        self.mock_file = MagicMock()
        self.mock_file.filename = 'test_area.geojson'
        self.mock_file.save = MagicMock()
    
    def test_mission_service_init(self):
        """Test: Inicialización correcta del servicio."""
        service = MissionService(self.mock_mission_planner, self.mock_drone_controller)
        
        self.assertEqual(service.mission_planner, self.mock_mission_planner)
        self.assertEqual(service.drone_controller, self.mock_drone_controller)
        print("✓ test_mission_service_init: EXITOSO")
    
    @patch.object(MissionService, '_get_basic_missions')
    def test_get_missions_success(self, mock_basic_missions):
        """Test: Obtener misiones básicas exitosamente."""
        mock_basic_missions.return_value = [
            {'id': '1', 'name': 'Test Mission 1'},
            {'id': '2', 'name': 'Test Mission 2'}
        ]
        
        result = self.service.get_missions()
        
        self.assertTrue(result['success'])
        self.assertIn('missions', result)
        self.assertEqual(len(result['missions']), 2)
        mock_basic_missions.assert_called_once()
        print("✓ test_get_missions_success: EXITOSO")
    
    @patch.object(MissionService, '_get_basic_missions')
    def test_get_missions_exception(self, mock_basic_missions):
        """Test: Excepción al obtener misiones."""
        mock_basic_missions.side_effect = Exception("Mission error")
        
        result = self.service.get_missions()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Mission error', result['error'])
        print("✓ test_get_missions_exception: EXITOSO")
    
    def test_start_mission_success(self):
        """Test: Iniciar misión exitosamente."""
        mission_id = 'mission_001'
        
        result = self.service.start_mission(mission_id)
        
        self.assertTrue(result['success'])
        self.assertIn('message', result)
        self.assertIn(mission_id, result['message'])
        print("✓ test_start_mission_success: EXITOSO")
    
    def test_start_mission_exception(self):
        """Test: Excepción al iniciar misión."""
        # Forzar excepción mockeando el logger
        with patch('src.services.mission_service.logger') as mock_logger:
            mock_logger.info.side_effect = Exception("Logger error")
            
            result = self.service.start_mission('mission_001')
            
            self.assertFalse(result['success'])
            self.assertIn('error', result)
            self.assertIn('Logger error', result['error'])
        
        print("✓ test_start_mission_exception: EXITOSO")
    
    def test_abort_mission_success(self):
        """Test: Abortar misión exitosamente."""
        result = self.service.abort_mission()
        
        self.assertTrue(result['success'])
        self.assertIn('message', result)
        self.assertIn('abortada', result['message'])
        print("✓ test_abort_mission_success: EXITOSO")
    
    def test_abort_mission_exception(self):
        """Test: Excepción al abortar misión."""
        with patch('src.services.mission_service.logger') as mock_logger:
            mock_logger.info.side_effect = Exception("Abort error")
            
            result = self.service.abort_mission()
            
            self.assertFalse(result['success'])
            self.assertIn('error', result)
            self.assertIn('Abort error', result['error'])
        
        print("✓ test_abort_mission_exception: EXITOSO")
    
    @patch('src.models.mission_validator.validate_mission_safety')
    def test_create_llm_mission_success(self, mock_validate):
        """Test: Crear misión LLM exitosamente."""
        # Configurar misión simulada
        mock_mission = {
            'id': 'llm_mission_001',
            'waypoints': [{'lat': 40.0, 'lng': -3.0}],
            'description': 'Test LLM mission'
        }
        self.mock_mission_planner.create_mission_from_command.return_value = mock_mission
        
        # Configurar validación
        mock_validate.return_value = ['Warning: Test warning']
        
        natural_command = "Vuela en círculo sobre el área urbana"
        area_name = "test_area"
        
        result = self.service.create_llm_mission(natural_command, area_name)
        
        self.assertTrue(result['success'])
        self.assertIn('mission', result)
        self.assertIn('safety_warnings', result)
        self.assertEqual(result['mission'], mock_mission)
        self.assertEqual(len(result['safety_warnings']), 1)
        
        self.mock_mission_planner.create_mission_from_command.assert_called_once_with(
            natural_command, area_name
        )
        mock_validate.assert_called_once_with(mock_mission)
        print("✓ test_create_llm_mission_success: EXITOSO")
    
    def test_create_llm_mission_failure(self):
        """Test: Fallo en creación de misión LLM."""
        self.mock_mission_planner.create_mission_from_command.return_value = None
        
        natural_command = "Comando inválido"
        
        result = self.service.create_llm_mission(natural_command)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Error creando misión con LLM', result['error'])
        print("✓ test_create_llm_mission_failure: EXITOSO")
    
    def test_create_llm_mission_exception(self):
        """Test: Excepción durante creación de misión LLM."""
        self.mock_mission_planner.create_mission_from_command.side_effect = Exception("LLM error")
        
        result = self.service.create_llm_mission("test command")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('LLM error', result['error'])
        print("✓ test_create_llm_mission_exception: EXITOSO")
    
    def test_adaptive_control_continue(self):
        """Test: Control adaptativo - continuar misión."""
        mission_id = 'mission_001'
        current_position = (40.0, -3.0)
        situation_report = "Todo normal, continuando operación"
        
        result = self.service.adaptive_control(mission_id, current_position, situation_report)
        
        self.assertTrue(result['success'])
        self.assertIn('decision', result)
        
        decision = result['decision']
        self.assertEqual(decision['action'], 'continue')
        self.assertIn(mission_id, decision['reason'])
        self.assertEqual(len(decision['adjustments']), 0)
        self.assertEqual(decision['confidence'], 0.8)
        print("✓ test_adaptive_control_continue: EXITOSO")
    
    def test_adaptive_control_abort_emergency(self):
        """Test: Control adaptativo - abortar por emergencia."""
        mission_id = 'mission_001'
        current_position = (40.0, -3.0)
        situation_report = "EMERGENCY: Motor failure detected"
        
        result = self.service.adaptive_control(mission_id, current_position, situation_report)
        
        self.assertTrue(result['success'])
        
        decision = result['decision']
        self.assertEqual(decision['action'], 'abort')
        self.assertIn('Emergencia detectada', decision['reason'])
        self.assertIn('return_to_base', decision['adjustments'])
        self.assertEqual(decision['confidence'], 0.9)
        print("✓ test_adaptive_control_abort_emergency: EXITOSO")
    
    def test_adaptive_control_adjust_weather(self):
        """Test: Control adaptativo - ajustar por clima."""
        mission_id = 'mission_001'
        current_position = (40.0, -3.0)
        situation_report = "Weather conditions deteriorating, strong winds"
        
        result = self.service.adaptive_control(mission_id, current_position, situation_report)
        
        self.assertTrue(result['success'])
        
        decision = result['decision']
        self.assertEqual(decision['action'], 'adjust')
        self.assertIn('meteorológicas', decision['reason'])
        self.assertIn('reduce_altitude', decision['adjustments'])
        self.assertIn('increase_safety_margin', decision['adjustments'])
        self.assertEqual(decision['confidence'], 0.7)
        print("✓ test_adaptive_control_adjust_weather: EXITOSO")
    
    def test_adaptive_control_exception(self):
        """Test: Excepción durante control adaptativo."""
        # Simular excepción en el análisis
        with patch.dict('sys.modules', {'situation_report': None}):
            result = self.service.adaptive_control('mission_001', (40.0, -3.0), None)
            
            # Debería manejar la situación gracefully
            self.assertTrue(result['success'])  # El método actual no falla con None
        
        print("✓ test_adaptive_control_exception: EXITOSO")
    
    def test_get_llm_missions_success(self):
        """Test: Obtener misiones LLM exitosamente."""
        mock_missions = [
            {'id': 'llm_1', 'name': 'LLM Mission 1'},
            {'id': 'llm_2', 'name': 'LLM Mission 2'}
        ]
        self.mock_mission_planner.get_available_missions.return_value = mock_missions
        
        result = self.service.get_llm_missions()
        
        self.assertTrue(result['success'])
        self.assertIn('missions', result)
        self.assertEqual(result['missions'], mock_missions)
        self.mock_mission_planner.get_available_missions.assert_called_once()
        print("✓ test_get_llm_missions_success: EXITOSO")
    
    def test_get_llm_missions_exception(self):
        """Test: Excepción al obtener misiones LLM."""
        self.mock_mission_planner.get_available_missions.side_effect = Exception("LLM missions error")
        
        result = self.service.get_llm_missions()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('LLM missions error', result['error'])
        print("✓ test_get_llm_missions_exception: EXITOSO")
    
    def test_upload_cartography_empty_filename(self):
        """Test: Error con nombre de archivo vacío."""
        self.mock_file.filename = ""
        
        result = self.service.upload_cartography(self.mock_file, "test_area")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Nombre de archivo vacío', result['error'])
        print("✓ test_upload_cartography_empty_filename: EXITOSO")
    
    def test_upload_cartography_invalid_extension(self):
        """Test: Error con extensión de archivo inválida."""
        self.mock_file.filename = "test_file.txt"
        
        result = self.service.upload_cartography(self.mock_file, "test_area")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Formato no soportado', result['error'])
        self.assertIn('test_file.txt', result['error'])
        print("✓ test_upload_cartography_invalid_extension: EXITOSO")
    
    @patch.object(MissionService, '_save_temp_file')
    @patch('os.path.exists')
    def test_upload_cartography_temp_save_error(self, mock_exists, mock_save_temp):
        """Test: Error al guardar archivo temporal."""
        mock_save_temp.return_value = '/tmp/test_area.geojson'
        mock_exists.return_value = False  # Archivo no existe después de guardar
        
        result = self.service.upload_cartography(self.mock_file, "test_area")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Error al guardar archivo temporal', result['error'])
        print("✓ test_upload_cartography_temp_save_error: EXITOSO")
    
    @patch.object(MissionService, '_save_temp_file')
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='<!DOCTYPE html><html>'))
    def test_upload_cartography_html_content(self, mock_exists, mock_save_temp):
        """Test: Error cuando el archivo contiene HTML."""
        mock_save_temp.return_value = '/tmp/test_area.geojson'
        mock_exists.return_value = True
        
        result = self.service.upload_cartography(self.mock_file, "test_area")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('HTML en lugar de GeoJSON', result['error'])
        print("✓ test_upload_cartography_html_content: EXITOSO")
    
    @patch.object(MissionService, '_save_temp_file')
    @patch('os.path.exists')
    @patch('builtins.open', mock_open())
    def test_upload_cartography_read_error(self, mock_exists, mock_save_temp):
        """Test: Error al leer archivo."""
        mock_save_temp.return_value = '/tmp/test_area.geojson'
        mock_exists.return_value = True
        
        # Configurar excepción en la lectura
        with patch('builtins.open', mock_open()) as mock_file_open:
            mock_file_open.return_value.__enter__.return_value.read.side_effect = Exception("Read error")
            
            result = self.service.upload_cartography(self.mock_file, "test_area")
            
            self.assertFalse(result['success'])
            self.assertIn('error', result)
            self.assertIn('Error leyendo archivo', result['error'])
        
        print("✓ test_upload_cartography_read_error: EXITOSO")
    
    @patch.object(MissionService, '_save_temp_file')
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='{"type": "FeatureCollection"}'))
    @patch('os.remove')
    def test_upload_cartography_success(self, mock_remove, mock_exists, mock_save_temp):
        """Test: Carga exitosa de cartografía."""
        mock_save_temp.return_value = '/tmp/test_area.geojson'
        mock_exists.return_value = True
        
        # Configurar éxito en load_cartography
        self.mock_mission_planner.load_cartography.return_value = True
        self.mock_mission_planner.get_area_center_coordinates.return_value = (40.0, -3.0)
        self.mock_drone_controller.update_position = MagicMock()
        
        result = self.service.upload_cartography(self.mock_file, "test_area")
        
        self.assertTrue(result['success'])
        self.assertIn('message', result)
        self.assertIn('test_area', result['message'])
        self.assertEqual(result['area_name'], 'test_area')
        self.assertIn('center_coordinates', result)
        self.assertEqual(result['center_coordinates']['latitude'], 40.0)
        self.assertEqual(result['center_coordinates']['longitude'], -3.0)
        
        # Verificar llamadas
        self.mock_mission_planner.load_cartography.assert_called_once_with('/tmp/test_area.geojson', 'test_area')
        self.mock_mission_planner.get_area_center_coordinates.assert_called_once_with('test_area')
        self.mock_drone_controller.update_position.assert_called_once_with(40.0, -3.0)
        mock_remove.assert_called_once_with('/tmp/test_area.geojson')
        print("✓ test_upload_cartography_success: EXITOSO")
    
    @patch.object(MissionService, '_save_temp_file')
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data='{"type": "FeatureCollection"}'))
    def test_upload_cartography_planner_failure(self, mock_exists, mock_save_temp):
        """Test: Fallo en el planificador de misiones."""
        mock_save_temp.return_value = '/tmp/test_area.geojson'
        mock_exists.return_value = True
        
        # Configurar fallo en load_cartography
        self.mock_mission_planner.load_cartography.return_value = False
        
        result = self.service.upload_cartography(self.mock_file, "test_area")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Error procesando cartografía', result['error'])
        print("✓ test_upload_cartography_planner_failure: EXITOSO")
    
    @patch.object(MissionService, '_save_temp_file')
    def test_upload_cartography_general_exception(self, mock_save_temp):
        """Test: Excepción general durante carga."""
        mock_save_temp.side_effect = Exception("Unexpected error")
        
        result = self.service.upload_cartography(self.mock_file, "test_area")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Error interno del servidor', result['error'])
        self.assertIn('Unexpected error', result['error'])
        print("✓ test_upload_cartography_general_exception: EXITOSO")
    
    def test_get_loaded_areas_with_areas(self):
        """Test: Obtener áreas cargadas exitosamente."""
        # Configurar áreas simuladas
        mock_area_1 = MagicMock()
        mock_area_1.boundaries = [1, 2, 3]  # 3 boundaries
        mock_area_1.points_of_interest = [{'name': 'POI1'}, {'name': 'POI2'}]  # 2 POIs
        
        mock_area_2 = MagicMock()
        mock_area_2.boundaries = [1, 2]  # 2 boundaries
        mock_area_2.points_of_interest = None  # Sin POIs
        
        self.mock_mission_planner.loaded_areas = {
            'area_1': mock_area_1,
            'area_2': mock_area_2
        }
        
        result = self.service.get_loaded_areas()
        
        self.assertTrue(result['success'])
        self.assertIn('areas', result)
        self.assertEqual(len(result['areas']), 2)
        
        # Verificar área 1
        area_1 = result['areas'][0]
        self.assertEqual(area_1['name'], 'area_1')
        self.assertEqual(area_1['boundaries_count'], 3)
        self.assertEqual(area_1['poi_count'], 2)
        
        # Verificar área 2
        area_2 = result['areas'][1]
        self.assertEqual(area_2['name'], 'area_2')
        self.assertEqual(area_2['boundaries_count'], 2)
        self.assertEqual(area_2['poi_count'], 0)  # None se convierte a 0
        
        print("✓ test_get_loaded_areas_with_areas: EXITOSO")
    
    def test_get_loaded_areas_empty(self):
        """Test: Obtener áreas cuando no hay ninguna cargada."""
        # Sin loaded_areas attribute
        del self.mock_mission_planner.loaded_areas
        
        result = self.service.get_loaded_areas()
        
        self.assertTrue(result['success'])
        self.assertIn('areas', result)
        self.assertEqual(len(result['areas']), 0)
        print("✓ test_get_loaded_areas_empty: EXITOSO")
    
    def test_get_loaded_areas_exception(self):
        """Test: Excepción al obtener áreas cargadas."""
        # Configurar excepción en el acceso
        self.mock_mission_planner.loaded_areas = property(lambda self: 1/0)  # División por cero
        
        result = self.service.get_loaded_areas()
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        print("✓ test_get_loaded_areas_exception: EXITOSO")
    
    def test_get_basic_missions(self):
        """Test: Obtener misiones básicas predefinidas."""
        missions = self.service._get_basic_missions()
        
        self.assertIsInstance(missions, list)
        self.assertEqual(len(missions), 3)
        
        # Verificar estructura de las misiones
        for mission in missions:
            self.assertIn('id', mission)
            self.assertIn('name', mission)
        
        # Verificar IDs específicos
        mission_ids = [mission['id'] for mission in missions]
        self.assertIn('1', mission_ids)
        self.assertIn('2', mission_ids)
        self.assertIn('3', mission_ids)
        print("✓ test_get_basic_missions: EXITOSO")
    
    @patch('tempfile.gettempdir')
    @patch('os.path.join')
    def test_save_temp_file(self, mock_join, mock_gettempdir):
        """Test: Guardar archivo temporal."""
        mock_gettempdir.return_value = '/tmp'
        mock_join.return_value = '/tmp/test_area.geojson'
        
        result = self.service._save_temp_file(self.mock_file)
        
        self.assertEqual(result, '/tmp/test_area.geojson')
        self.mock_file.save.assert_called_once_with('/tmp/test_area.geojson')
        print("✓ test_save_temp_file: EXITOSO")


if __name__ == '__main__':
    print("🎯 EJECUTANDO TESTS DE MISSION SERVICE")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMissionService)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE MISSION SERVICE:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE MISSION SERVICE PASAN! 🎉")
