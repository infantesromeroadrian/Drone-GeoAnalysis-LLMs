#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para drone_controller.py
Prueba todas las funciones y endpoints del controlador de drones.
"""

import sys
import os
import pytest
from unittest.mock import Mock
from flask import Flask

# Configuración de path para importar módulos desde src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.controllers.drone_controller import (
    drone_blueprint,
    init_drone_controller
)

class TestDroneController:
    """Clase de tests para DroneController"""
    
    @pytest.fixture
    def app(self):
        """Crea una app Flask de prueba"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(drone_blueprint)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Crea un cliente de prueba"""
        return app.test_client()
    
    @pytest.fixture
    def mock_service(self):
        """Crea un mock del servicio de drones"""
        service = Mock()
        service.connect.return_value = {'success': True, 'message': 'Conectado exitosamente'}
        service.disconnect.return_value = {'success': True, 'message': 'Desconectado exitosamente'}
        service.takeoff.return_value = {'success': True, 'altitude': 10.0}
        service.land.return_value = {'success': True, 'message': 'Aterrizaje exitoso'}
        service.start_video_stream.return_value = {'success': True, 'stream_url': 'http://localhost:5000/video'}
        service.stop_video_stream.return_value = {'success': True, 'message': 'Stream detenido'}
        service.get_telemetry.return_value = {
            'success': True,
            'battery': 85,
            'altitude': 15.5,
            'gps': {'lat': 40.416775, 'lng': -3.703790}
        }
        service.get_simulation_paths.return_value = {
            'success': True,
            'paths': [
                {'id': 'path1', 'name': 'Ruta Madrid Centro'},
                {'id': 'path2', 'name': 'Ruta Retiro'}
            ]
        }
        service.start_simulation.return_value = {'success': True, 'message': 'Simulación iniciada'}
        return service
    
    def test_init_drone_controller(self, mock_service):
        """Prueba la inicialización del controlador"""
        # Inicializar controlador
        init_drone_controller(mock_service)
        
        # Verificar que se inicializó correctamente
        from src.controllers.drone_controller import drone_service
        assert drone_service is not None
        assert drone_service == mock_service
    
    def test_connect_drone_success(self, client, mock_service):
        """Prueba el endpoint /api/drone/connect con éxito"""
        init_drone_controller(mock_service)
        
        # Hacer petición
        response = client.post('/api/drone/connect')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'message' in json_data
        
        # Verificar que se llamó al servicio
        mock_service.connect.assert_called_once()
    
    def test_connect_drone_service_not_initialized(self, client):
        """Prueba el endpoint /api/drone/connect sin servicio inicializado"""
        # Resetear servicio global
        from src.controllers import drone_controller
        drone_controller.drone_service = None
        
        # Hacer petición
        response = client.post('/api/drone/connect')
        
        # Verificar error
        assert response.status_code == 200  # El endpoint devuelve 200 con error en JSON
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'Servicio no inicializado' in json_data['error']
    
    def test_connect_drone_exception(self, client, mock_service):
        """Prueba el endpoint /api/drone/connect cuando el servicio lanza excepción"""
        # Configurar servicio para lanzar excepción
        mock_service.connect.side_effect = Exception("Error de conexión")
        init_drone_controller(mock_service)
        
        # Hacer petición
        response = client.post('/api/drone/connect')
        
        # Verificar error
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'Error de conexión' in json_data['error']
    
    def test_disconnect_drone_success(self, client, mock_service):
        """Prueba el endpoint /api/drone/disconnect con éxito"""
        init_drone_controller(mock_service)
        
        # Hacer petición
        response = client.post('/api/drone/disconnect')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        
        # Verificar que se llamó al servicio
        mock_service.disconnect.assert_called_once()
    
    def test_takeoff_drone_success_default_altitude(self, client, mock_service):
        """Prueba el endpoint /api/drone/takeoff con altitud por defecto"""
        init_drone_controller(mock_service)
        
        # Hacer petición sin datos pero con content type JSON
        response = client.post('/api/drone/takeoff', json={})
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        
        # Verificar que se llamó al servicio con altitud por defecto
        mock_service.takeoff.assert_called_once_with(10.0)
    
    def test_takeoff_drone_success_custom_altitude(self, client, mock_service):
        """Prueba el endpoint /api/drone/takeoff con altitud personalizada"""
        init_drone_controller(mock_service)
        
        # Hacer petición con altitud personalizada
        data = {'altitude': 25.0}
        response = client.post('/api/drone/takeoff', json=data)
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        
        # Verificar que se llamó al servicio con la altitud correcta
        mock_service.takeoff.assert_called_once_with(25.0)
    
    def test_land_drone_success(self, client, mock_service):
        """Prueba el endpoint /api/drone/land con éxito"""
        init_drone_controller(mock_service)
        
        # Hacer petición
        response = client.post('/api/drone/land')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        
        # Verificar que se llamó al servicio
        mock_service.land.assert_called_once()
    
    def test_start_stream_success(self, client, mock_service):
        """Prueba el endpoint /api/drone/stream/start con éxito"""
        init_drone_controller(mock_service)
        
        # Hacer petición
        response = client.post('/api/drone/stream/start')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'stream_url' in json_data
        
        # Verificar que se llamó al servicio
        mock_service.start_video_stream.assert_called_once()
    
    def test_stop_stream_success(self, client, mock_service):
        """Prueba el endpoint /api/drone/stream/stop con éxito"""
        init_drone_controller(mock_service)
        
        # Hacer petición
        response = client.post('/api/drone/stream/stop')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        
        # Verificar que se llamó al servicio
        mock_service.stop_video_stream.assert_called_once()
    
    def test_get_telemetry_success(self, client, mock_service):
        """Prueba el endpoint /api/drone/telemetry con éxito"""
        init_drone_controller(mock_service)
        
        # Hacer petición
        response = client.get('/api/drone/telemetry')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['battery'] == 85
        assert json_data['altitude'] == 15.5
        assert 'gps' in json_data
        
        # Verificar que se llamó al servicio
        mock_service.get_telemetry.assert_called_once()
    
    def test_get_simulation_paths_success(self, client, mock_service):
        """Prueba el endpoint /api/drone/simulate/paths con éxito"""
        init_drone_controller(mock_service)
        
        # Hacer petición
        response = client.get('/api/drone/simulate/paths')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'paths' in json_data
        assert len(json_data['paths']) == 2
        assert json_data['paths'][0]['id'] == 'path1'
        
        # Verificar que se llamó al servicio
        mock_service.get_simulation_paths.assert_called_once()
    
    def test_start_simulation_success(self, client, mock_service):
        """Prueba el endpoint /api/drone/simulate/start con éxito"""
        init_drone_controller(mock_service)
        
        # Hacer petición con path_id
        data = {'path_id': 'path1'}
        response = client.post('/api/drone/simulate/start', json=data)
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        
        # Verificar que se llamó al servicio con el path_id correcto
        mock_service.start_simulation.assert_called_once_with('path1')
    
    def test_start_simulation_no_path_id(self, client, mock_service):
        """Prueba el endpoint /api/drone/simulate/start sin path_id"""
        init_drone_controller(mock_service)
        
        # Hacer petición sin path_id
        response = client.post('/api/drone/simulate/start', json={})
        
        # Verificar error
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'ID de ruta no especificado' in json_data['error']
        
        # Verificar que NO se llamó al servicio
        mock_service.start_simulation.assert_not_called()
    
    def test_start_simulation_missing_json(self, client, mock_service):
        """Prueba el endpoint /api/drone/simulate/start sin JSON"""
        init_drone_controller(mock_service)
        
        # Hacer petición sin JSON pero con content type correcto
        response = client.post('/api/drone/simulate/start', json={})
        
        # Verificar error
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'ID de ruta no especificado' in json_data['error']
    
    # Tests para casos de error comunes en todos los endpoints
    def test_all_endpoints_service_not_initialized(self, client):
        """Prueba que todos los endpoints manejan correctamente el servicio no inicializado"""
        # Resetear servicio global
        from src.controllers import drone_controller
        drone_controller.drone_service = None
        
        endpoints_to_test = [
            ('POST', '/api/drone/disconnect'),
            ('POST', '/api/drone/takeoff'),
            ('POST', '/api/drone/land'),
            ('POST', '/api/drone/stream/start'),
            ('POST', '/api/drone/stream/stop'),
            ('GET', '/api/drone/telemetry'),
            ('GET', '/api/drone/simulate/paths')
        ]
        
        for method, endpoint in endpoints_to_test:
            if method == 'POST':
                response = client.post(endpoint)
            else:
                response = client.get(endpoint)
            
            # Verificar que todos devuelven error de servicio no inicializado
            assert response.status_code == 200
            json_data = response.get_json()
            assert json_data['success'] is False
            assert 'Servicio no inicializado' in json_data['error']
    
    def test_all_endpoints_exception_handling(self, client, mock_service):
        """Prueba que todos los endpoints manejan correctamente las excepciones"""
        init_drone_controller(mock_service)
        
        # Configurar todos los métodos del servicio para lanzar excepciones
        mock_service.disconnect.side_effect = Exception("Error de desconexión")
        mock_service.takeoff.side_effect = Exception("Error de despegue")
        mock_service.land.side_effect = Exception("Error de aterrizaje")
        mock_service.start_video_stream.side_effect = Exception("Error de stream")
        mock_service.stop_video_stream.side_effect = Exception("Error stopping stream")
        mock_service.get_telemetry.side_effect = Exception("Error de telemetría")
        mock_service.get_simulation_paths.side_effect = Exception("Error de rutas")
        mock_service.start_simulation.side_effect = Exception("Error de simulación")
        
        endpoints_with_errors = [
            ('POST', '/api/drone/disconnect', 'Error de desconexión'),
            ('POST', '/api/drone/takeoff', 'Error de despegue'),
            ('POST', '/api/drone/land', 'Error de aterrizaje'),
            ('POST', '/api/drone/stream/start', 'Error de stream'),
            ('POST', '/api/drone/stream/stop', 'Error stopping stream'),
            ('GET', '/api/drone/telemetry', 'Error de telemetría'),
            ('GET', '/api/drone/simulate/paths', 'Error de rutas')
        ]
        
        for method, endpoint, expected_error in endpoints_with_errors:
            if method == 'POST':
                response = client.post(endpoint, json={})
            else:
                response = client.get(endpoint)
            
            # Verificar que todos manejan la excepción correctamente
            assert response.status_code == 200
            json_data = response.get_json()
            assert json_data['success'] is False
            assert expected_error in json_data['error']
        
        # Test especial para start_simulation con path_id
        data = {'path_id': 'test_path'}
        response = client.post('/api/drone/simulate/start', json=data)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'Error de simulación' in json_data['error'] 