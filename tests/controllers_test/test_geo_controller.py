#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para geo_controller.py
Prueba todas las funciones y endpoints del controlador de geolocalización.
"""

import sys
import os
import pytest
from unittest.mock import Mock
from flask import Flask

# Configuración de path para importar módulos desde src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.controllers.geo_controller import (
    geo_blueprint,
    init_geo_controller,
    _extract_observation_params
)

class TestGeoController:
    """Clase de tests para GeoController"""
    
    @pytest.fixture
    def app(self):
        """Crea una app Flask de prueba"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(geo_blueprint)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Crea un cliente de prueba"""
        return app.test_client()
    
    @pytest.fixture
    def mock_service(self):
        """Crea un mock del servicio de geolocalización"""
        service = Mock()
        service.add_reference_image.return_value = {
            'success': True,
            'message': 'Imagen de referencia añadida',
            'reference_id': 'ref_001'
        }
        service.detect_changes.return_value = {
            'success': True,
            'changes_detected': True,
            'change_areas': [{'x': 100, 'y': 150, 'width': 50, 'height': 30}],
            'confidence': 0.92
        }
        service.create_target.return_value = {
            'success': True,
            'target_id': 'target_001',
            'message': 'Objetivo creado exitosamente'
        }
        service.calculate_position.return_value = {
            'success': True,
            'position': {'lat': 40.416775, 'lng': -3.703790},
            'accuracy': 'high',
            'confidence': 0.95
        }
        service.add_observation.return_value = {
            'success': True,
            'observation_id': 'obs_001',
            'message': 'Observación añadida'
        }
        service.get_targets_status.return_value = {
            'success': True,
            'targets': [
                {
                    'id': 'target_001',
                    'status': 'triangulating',
                    'observations': 2,
                    'estimated_position': {'lat': 40.416775, 'lng': -3.703790}
                }
            ]
        }
        return service
    
    def test_init_geo_controller(self, mock_service):
        """Prueba la inicialización del controlador"""
        # Inicializar controlador
        init_geo_controller(mock_service)
        
        # Verificar que se inicializó correctamente
        from src.controllers.geo_controller import geo_service
        assert geo_service is not None
        assert geo_service == mock_service
    
    def test_add_reference_success(self, client, mock_service):
        """Prueba el endpoint /api/geo/reference/add con éxito"""
        init_geo_controller(mock_service)
        
        # Hacer petición
        response = client.post('/api/geo/reference/add')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'reference_id' in json_data
        
        # Verificar que se llamó al servicio
        mock_service.add_reference_image.assert_called_once()
    
    def test_calculate_position_success(self, client, mock_service):
        """Prueba el endpoint /api/geo/position/calculate con éxito"""
        init_geo_controller(mock_service)
        
        # Hacer petición con target_id
        data = {'target_id': 'target_001'}
        response = client.post('/api/geo/position/calculate', json=data)
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'position' in json_data
        assert json_data['position']['lat'] == 40.416775
        assert json_data['accuracy'] == 'high'
        
        # Verificar que se llamó al servicio con el target_id correcto
        mock_service.calculate_position.assert_called_once_with('target_001')
    
    def test_add_observation_success(self, client, mock_service):
        """Prueba el endpoint /api/geo/observation/add con éxito"""
        init_geo_controller(mock_service)
        
        # Hacer petición con datos completos
        data = {
            'target_id': 'target_001',
            'target_bearing': 45.5,
            'target_elevation': 10.2,
            'confidence': 0.9
        }
        response = client.post('/api/geo/observation/add', json=data)
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['observation_id'] == 'obs_001'
        
        # Verificar que se llamó al servicio con los parámetros correctos
        mock_service.add_observation.assert_called_once()
        call_args = mock_service.add_observation.call_args[0][0]
        assert call_args['target_id'] == 'target_001'
        assert call_args['target_bearing'] == 45.5
        assert call_args['target_elevation'] == 10.2
        assert call_args['confidence'] == 0.9
    
    def test_extract_observation_params_complete(self):
        """Prueba _extract_observation_params con todos los parámetros"""
        data = {
            'target_id': 'target_001',
            'target_bearing': 45.5,
            'target_elevation': 10.2,
            'confidence': 0.9
        }
        
        # Llamar función
        params = _extract_observation_params(data)
        
        # Verificar resultado
        assert params['target_id'] == 'target_001'
        assert params['target_bearing'] == 45.5
        assert params['target_elevation'] == 10.2
        assert params['confidence'] == 0.9
