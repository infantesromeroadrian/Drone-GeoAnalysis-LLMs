#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para mission_controller.py
Prueba todas las funciones y endpoints del controlador de misiones.
"""

import sys
import os
import pytest
from unittest.mock import Mock
from flask import Flask

# Configuración de path para importar módulos desde src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.controllers.mission_controller import (
    mission_blueprint,
    init_mission_controller
)

class TestMissionController:
    """Clase de tests para MissionController"""
    
    @pytest.fixture
    def app(self):
        """Crea una app Flask de prueba"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(mission_blueprint)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Crea un cliente de prueba"""
        return app.test_client()
    
    @pytest.fixture
    def mock_service(self):
        """Crea un mock del servicio de misiones"""
        service = Mock()
        service.get_missions.return_value = {
            'success': True,
            'missions': [
                {'id': 'mission_001', 'name': 'Misión Madrid Centro', 'status': 'ready'},
                {'id': 'mission_002', 'name': 'Misión Retiro', 'status': 'completed'}
            ]
        }
        service.start_mission.return_value = {
            'success': True,
            'message': 'Misión iniciada exitosamente',
            'mission_id': 'mission_001'
        }
        service.create_llm_mission.return_value = {
            'success': True,
            'mission_id': 'llm_mission_001',
            'mission_plan': 'Plan de vuelo generado por LLM'
        }
        service.upload_cartography.return_value = {
            'success': True,
            'area_name': 'Base Militar Centro'
        }
        service.get_loaded_areas.return_value = {
            'areas': [
                {'name': 'Base Militar Centro', 'poi_count': 4, 'boundaries_count': 6}
            ]
        }
        return service
    
    def test_init_mission_controller(self, mock_service):
        """Prueba la inicialización del controlador"""
        # Inicializar controlador
        init_mission_controller(mock_service)
        
        # Verificar que se inicializó correctamente
        from src.controllers.mission_controller import mission_service
        assert mission_service is not None
        assert mission_service == mock_service
    
    def test_get_missions_success(self, client, mock_service):
        """Prueba el endpoint /api/missions/ con éxito"""
        init_mission_controller(mock_service)
        
        # Hacer petición
        response = client.get('/api/missions/')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'missions' in json_data
        assert len(json_data['missions']) == 2
        
        # Verificar que se llamó al servicio
        mock_service.get_missions.assert_called_once()
    
    def test_start_mission_success(self, client, mock_service):
        """Prueba el endpoint /api/missions/start con éxito"""
        init_mission_controller(mock_service)
        
        # Hacer petición con mission_id
        data = {'id': 'mission_001'}
        response = client.post('/api/missions/start', json=data)
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['mission_id'] == 'mission_001'
        
        # Verificar que se llamó al servicio
        mock_service.start_mission.assert_called_once_with('mission_001')
    
    def test_create_llm_mission_success(self, client, mock_service):
        """Prueba el endpoint /api/missions/llm/create con éxito"""
        init_mission_controller(mock_service)
        
        # Hacer petición con comando natural
        data = {
            'command': 'Vuela sobre el parque del Retiro a 50 metros de altura',
            'area_name': 'retiro_area'
        }
        response = client.post('/api/missions/llm/create', json=data)
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'mission_id' in json_data
        
        # Verificar que se llamó al servicio
        mock_service.create_llm_mission.assert_called_once_with(
            'Vuela sobre el parque del Retiro a 50 metros de altura',
            'retiro_area'
        )
