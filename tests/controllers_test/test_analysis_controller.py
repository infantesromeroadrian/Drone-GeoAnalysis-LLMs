#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para analysis_controller.py
Prueba todas las funciones y endpoints del controlador de análisis.
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from werkzeug.datastructures import FileStorage
import io

# Configuración de path para importar módulos desde src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.controllers.analysis_controller import (
    analysis_blueprint,
    init_analysis_controller,
    _extract_analysis_params
)

class TestAnalysisController:
    """Clase de tests para AnalysisController"""
    
    @pytest.fixture
    def app(self):
        """Crea una app Flask de prueba"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(analysis_blueprint)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Crea un cliente de prueba"""
        return app.test_client()
    
    @pytest.fixture
    def mock_service(self):
        """Crea un mock del servicio de análisis"""
        service = Mock()
        service.analyze_image.return_value = {
            'success': True,
            'analysis': 'Análisis completado',
            'confidence': 0.85
        }
        service.serve_result_file.return_value = {'success': True}
        service.get_analysis_status.return_value = {
            'status': 'completed',
            'progress': 100
        }
        return service
    
    def test_init_analysis_controller(self, mock_service):
        """Prueba la inicialización del controlador"""
        # Inicializar controlador
        init_analysis_controller(mock_service)
        
        # Verificar que se inicializó correctamente
        from src.controllers.analysis_controller import analysis_service
        assert analysis_service is not None
        assert analysis_service == mock_service
    
    def test_analyze_endpoint_success(self, client, mock_service):
        """Prueba el endpoint /analyze con éxito"""
        # Inicializar controlador
        init_analysis_controller(mock_service)
        
        # Crear archivo de imagen mock
        data = {
            'image': (io.BytesIO(b'fake image content'), 'test.jpg'),
            'confidence_threshold': '0.5',
            'model_version': 'v2',
            'detail_level': 'high'
        }
        
        # Hacer petición
        response = client.post('/analyze', data=data, content_type='multipart/form-data')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'analysis' in json_data
        
        # Verificar que se llamó al servicio con los parámetros correctos
        mock_service.analyze_image.assert_called_once()
        args, kwargs = mock_service.analyze_image.call_args
        assert args[1]['confidence_threshold'] == 0.5
        assert args[1]['model_version'] == 'v2'
        assert args[1]['detail_level'] == 'high'
    
    def test_analyze_endpoint_no_image(self, client, mock_service):
        """Prueba el endpoint /analyze sin imagen"""
        init_analysis_controller(mock_service)
        
        # Hacer petición sin imagen
        response = client.post('/analyze', data={})
        
        # Verificar error
        assert response.status_code == 400
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'No se envió ninguna imagen' in json_data['error']
    
    def test_analyze_endpoint_empty_filename(self, client, mock_service):
        """Prueba el endpoint /analyze con nombre de archivo vacío"""
        init_analysis_controller(mock_service)
        
        # Crear archivo con nombre vacío
        data = {'image': (io.BytesIO(b'fake image content'), '')}
        
        # Hacer petición
        response = client.post('/analyze', data=data, content_type='multipart/form-data')
        
        # Verificar error
        assert response.status_code == 400
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'Nombre de archivo vacío' in json_data['error']
    
    def test_analyze_endpoint_service_not_initialized(self, client):
        """Prueba el endpoint /analyze sin servicio inicializado"""
        # Resetear servicio global
        from src.controllers import analysis_controller
        analysis_controller.analysis_service = None
        
        # Crear archivo de imagen mock
        data = {'image': (io.BytesIO(b'fake image content'), 'test.jpg')}
        
        # Hacer petición
        response = client.post('/analyze', data=data, content_type='multipart/form-data')
        
        # Verificar error
        assert response.status_code == 500
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'Servicio no inicializado' in json_data['error']
    
    def test_analyze_endpoint_service_exception(self, client, mock_service):
        """Prueba el endpoint /analyze cuando el servicio lanza excepción"""
        # Configurar servicio para lanzar excepción
        mock_service.analyze_image.side_effect = Exception("Error de servicio")
        init_analysis_controller(mock_service)
        
        # Crear archivo de imagen mock
        data = {'image': (io.BytesIO(b'fake image content'), 'test.jpg')}
        
        # Hacer petición
        response = client.post('/analyze', data=data, content_type='multipart/form-data')
        
        # Verificar error
        assert response.status_code == 500
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'Error de servicio' in json_data['error']
    
    def test_results_endpoint_success(self, client, mock_service):
        """Prueba el endpoint /results/<filename> con éxito"""
        init_analysis_controller(mock_service)
        
        # Hacer petición
        response = client.get('/results/test_result.json')
        
        # Verificar respuesta
        assert response.status_code == 200
        
        # Verificar que se llamó al servicio
        mock_service.serve_result_file.assert_called_once_with('test_result.json')
    
    def test_results_endpoint_service_not_initialized(self, client):
        """Prueba el endpoint /results/<filename> sin servicio inicializado"""
        # Resetear servicio global
        from src.controllers import analysis_controller
        analysis_controller.analysis_service = None
        
        # Hacer petición
        response = client.get('/results/test_result.json')
        
        # Verificar error
        assert response.status_code == 500
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'Servicio no inicializado' in json_data['error']
    
    def test_results_endpoint_exception(self, client, mock_service):
        """Prueba el endpoint /results/<filename> cuando el servicio lanza excepción"""
        # Configurar servicio para lanzar excepción
        mock_service.serve_result_file.side_effect = Exception("Archivo no encontrado")
        init_analysis_controller(mock_service)
        
        # Hacer petición
        response = client.get('/results/nonexistent.json')
        
        # Verificar error
        assert response.status_code == 500
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'Archivo no encontrado' in json_data['error']
    
    def test_analysis_status_endpoint_success(self, client, mock_service):
        """Prueba el endpoint /api/analysis/status con éxito"""
        init_analysis_controller(mock_service)
        
        # Hacer petición con ID
        response = client.get('/api/analysis/status?id=test_123')
        
        # Verificar respuesta
        assert response.status_code == 200
        json_data = response.get_json()
        assert 'status' in json_data
        assert json_data['status'] == 'completed'
        
        # Verificar que se llamó al servicio con el ID correcto
        mock_service.get_analysis_status.assert_called_once_with('test_123')
    
    def test_analysis_status_endpoint_no_id(self, client, mock_service):
        """Prueba el endpoint /api/analysis/status sin ID"""
        init_analysis_controller(mock_service)
        
        # Hacer petición sin ID
        response = client.get('/api/analysis/status')
        
        # Verificar respuesta (debe funcionar con None)
        assert response.status_code == 200
        
        # Verificar que se llamó al servicio con None
        mock_service.get_analysis_status.assert_called_once_with(None)
    
    def test_analysis_status_endpoint_service_not_initialized(self, client):
        """Prueba el endpoint /api/analysis/status sin servicio inicializado"""
        # Resetear servicio global
        from src.controllers import analysis_controller
        analysis_controller.analysis_service = None
        
        # Hacer petición
        response = client.get('/api/analysis/status?id=test_123')
        
        # Verificar error
        assert response.status_code == 500
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'Servicio no inicializado' in json_data['error']
    
    def test_analysis_status_endpoint_exception(self, client, mock_service):
        """Prueba el endpoint /api/analysis/status cuando el servicio lanza excepción"""
        # Configurar servicio para lanzar excepción
        mock_service.get_analysis_status.side_effect = Exception("Error de estado")
        init_analysis_controller(mock_service)
        
        # Hacer petición
        response = client.get('/api/analysis/status?id=test_123')
        
        # Verificar error
        assert response.status_code == 500
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'Error de estado' in json_data['error']
    
    def test_extract_analysis_params_complete(self):
        """Prueba _extract_analysis_params con todos los parámetros"""
        # Crear form data mock
        form_data = Mock()
        form_data.get.side_effect = lambda key, default: {
            'confidence_threshold': '0.75',
            'model_version': 'v3',
            'detail_level': 'maximum'
        }.get(key, default)
        
        # Llamar función
        params = _extract_analysis_params(form_data)
        
        # Verificar resultado
        assert params['confidence_threshold'] == 0.75
        assert params['model_version'] == 'v3'
        assert params['detail_level'] == 'maximum'
    
    def test_extract_analysis_params_defaults(self):
        """Prueba _extract_analysis_params con valores por defecto"""
        # Crear form data mock vacío
        form_data = Mock()
        form_data.get.side_effect = lambda key, default: default
        
        # Llamar función
        params = _extract_analysis_params(form_data)
        
        # Verificar valores por defecto
        assert params['confidence_threshold'] == 0
        assert params['model_version'] == 'default'
        assert params['detail_level'] == 'normal'
    
    def test_extract_analysis_params_partial(self):
        """Prueba _extract_analysis_params con algunos parámetros"""
        # Crear form data mock parcial
        form_data = Mock()
        form_data.get.side_effect = lambda key, default: {
            'confidence_threshold': '0.5',
            'detail_level': 'high'
        }.get(key, default)
        
        # Llamar función
        params = _extract_analysis_params(form_data)
        
        # Verificar resultado mixto
        assert params['confidence_threshold'] == 0.5
        assert params['model_version'] == 'default'  # valor por defecto
        assert params['detail_level'] == 'high' 