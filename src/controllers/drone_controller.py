#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controlador para rutas de control de drones.
Responsabilidad única: Manejar las APIs HTTP relacionadas con drones.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Crear blueprint para rutas de drones
drone_blueprint = Blueprint('drone', __name__, url_prefix='/api/drone')

# Variable global para el servicio de drones (se inyectará desde main)
drone_service = None

def init_drone_controller(service):
    """Inicializa el controlador con el servicio de drones."""
    global drone_service
    drone_service = service
    logger.info("Controlador de drones inicializado")

@drone_blueprint.route('/connect', methods=['POST'])
def connect_drone():
    """Conecta con el dron."""
    try:
        if not drone_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = drone_service.connect()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al conectar: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@drone_blueprint.route('/disconnect', methods=['POST'])
def disconnect_drone():
    """Desconecta del dron."""
    try:
        if not drone_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = drone_service.disconnect()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al desconectar: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@drone_blueprint.route('/takeoff', methods=['POST'])
def takeoff_drone():
    """Despega el dron."""
    try:
        if not drone_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        data = request.json or {}
        altitude = data.get('altitude', 10.0)
        
        result = drone_service.takeoff(altitude)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al despegar: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@drone_blueprint.route('/land', methods=['POST'])
def land_drone():
    """Aterriza el dron."""
    try:
        if not drone_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = drone_service.land()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al aterrizar: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@drone_blueprint.route('/stream/start', methods=['POST'])
def start_stream():
    """Inicia la transmisión de video."""
    try:
        if not drone_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = drone_service.start_video_stream()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al iniciar stream: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@drone_blueprint.route('/stream/stop', methods=['POST'])
def stop_stream():
    """Detiene la transmisión de video."""
    try:
        if not drone_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = drone_service.stop_video_stream()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al detener stream: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@drone_blueprint.route('/telemetry')
def get_telemetry():
    """Obtiene datos de telemetría del dron."""
    try:
        if not drone_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = drone_service.get_telemetry()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al obtener telemetría: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@drone_blueprint.route('/simulate/paths', methods=['GET'])
def get_simulation_paths():
    """Obtiene rutas predefinidas para simulación de vuelo."""
    try:
        if not drone_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = drone_service.get_simulation_paths()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al obtener rutas de simulación: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@drone_blueprint.route('/simulate/start', methods=['POST'])
def start_simulation():
    """Inicia una simulación de vuelo."""
    try:
        if not drone_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        data = request.json or {}
        path_id = data.get('path_id')
        
        if not path_id:
            return jsonify({'success': False, 'error': 'ID de ruta no especificado'})
            
        result = drone_service.start_simulation(path_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al iniciar simulación: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}) 