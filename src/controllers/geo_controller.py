#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controlador para rutas de geolocalización y triangulación.
Responsabilidad única: Manejar las APIs HTTP de análisis geográfico.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Crear blueprint para rutas de geolocalización
geo_blueprint = Blueprint('geo', __name__, url_prefix='/api/geo')

# Variable global para el servicio de geolocalización (se inyectará desde main)
geo_service = None

def init_geo_controller(service):
    """Inicializa el controlador con el servicio de geolocalización."""
    global geo_service
    geo_service = service
    logger.info("Controlador de geolocalización inicializado")

@geo_blueprint.route('/reference/add', methods=['POST'])
def add_reference():
    """Añade una imagen de referencia para detección de cambios."""
    try:
        if not geo_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = geo_service.add_reference_image()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al añadir referencia: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@geo_blueprint.route('/changes/detect', methods=['POST'])
def detect_changes():
    """Detecta cambios entre imagen actual y referencia."""
    try:
        if not geo_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = geo_service.detect_changes()
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error en detección de cambios: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@geo_blueprint.route('/target/create', methods=['POST'])
def create_target():
    """Crea un nuevo objetivo para triangulación."""
    try:
        if not geo_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = geo_service.create_target()
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error al crear objetivo: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@geo_blueprint.route('/position/calculate', methods=['POST'])
def calculate_position():
    """Calcula la posición geográfica de un objetivo usando triangulación."""
    try:
        if not geo_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        data = request.json or {}
        target_id = data.get('target_id')
        
        if not target_id:
            return jsonify({'success': False, 'error': 'ID de objetivo no especificado'})
        
        result = geo_service.calculate_position(target_id)
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error al calcular posición: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@geo_blueprint.route('/observation/add', methods=['POST'])
def add_observation():
    """Agrega una observación manual para triangulación."""
    try:
        if not geo_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        data = request.json or {}
        observation_params = _extract_observation_params(data)
        
        if not observation_params['target_id'] or observation_params['target_bearing'] is None:
            return jsonify({
                'success': False, 
                'error': 'target_id y target_bearing son requeridos'
            })
        
        result = geo_service.add_observation(observation_params)
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error al agregar observación: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@geo_blueprint.route('/targets/status', methods=['GET'])
def get_targets_status():
    """Obtiene el estado de todos los objetivos de triangulación."""
    try:
        if not geo_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = geo_service.get_targets_status()
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error al obtener estado de objetivos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def _extract_observation_params(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae y valida parámetros de observación."""
    return {
        'target_id': data.get('target_id'),
        'target_bearing': data.get('target_bearing'),
        'target_elevation': data.get('target_elevation', 0),
        'confidence': data.get('confidence', 1.0)
    } 