#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controlador para rutas de misiones y planificación.
Responsabilidad única: Manejar las APIs HTTP de misiones y LLM.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Crear blueprint para rutas de misiones
mission_blueprint = Blueprint('mission', __name__, url_prefix='/api/missions')

# Variable global para el servicio de misiones (se inyectará desde main)
mission_service = None

def init_mission_controller(service):
    """Inicializa el controlador con el servicio de misiones."""
    global mission_service
    mission_service = service
    logger.info("Controlador de misiones inicializado")

@mission_blueprint.route('/')
def get_missions():
    """Obtiene la lista de misiones disponibles."""
    try:
        if not mission_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = mission_service.get_missions()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al obtener misiones: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@mission_blueprint.route('/start', methods=['POST'])
def start_mission():
    """Inicia una misión."""
    try:
        if not mission_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        data = request.json or {}
        mission_id = data.get('id')
        
        if not mission_id:
            return jsonify({'success': False, 'error': 'ID de misión no especificado'})
        
        result = mission_service.start_mission(mission_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al iniciar misión: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@mission_blueprint.route('/abort', methods=['POST'])
def abort_mission():
    """Aborta la misión actual."""
    try:
        if not mission_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = mission_service.abort_mission()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error al abortar misión: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@mission_blueprint.route('/llm/create', methods=['POST'])
def create_llm_mission():
    """Crea una misión usando comandos en lenguaje natural con LLM."""
    try:
        if not mission_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        data = request.json or {}
        natural_command = data.get('command')
        area_name = data.get('area_name')
        
        if not natural_command:
            return jsonify({'success': False, 'error': 'Comando no especificado'})
        
        result = mission_service.create_llm_mission(natural_command, area_name)
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error creando misión LLM: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@mission_blueprint.route('/llm/adaptive', methods=['POST'])
def adaptive_mission_control():
    """Control adaptativo de misión usando LLM."""
    try:
        if not mission_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        data = request.json or {}
        mission_id = data.get('mission_id')
        current_position = data.get('current_position', [40.416775, -3.703790])
        situation_report = data.get('situation_report', '')
        
        if not mission_id:
            return jsonify({'success': False, 'error': 'ID de misión no especificado'})
        
        result = mission_service.adaptive_control(
            mission_id, tuple(current_position), situation_report
        )
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en control adaptativo: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@mission_blueprint.route('/llm/list', methods=['GET'])
def get_llm_missions():
    """Obtiene lista de misiones LLM creadas."""
    try:
        if not mission_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = mission_service.get_llm_missions()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error obteniendo misiones LLM: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@mission_blueprint.route('/cartography/upload', methods=['POST'])
def upload_cartography():
    """Sube y procesa archivos de cartografía."""
    try:
        if not mission_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        if 'cartography_file' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió archivo de cartografía'})
        
        file = request.files['cartography_file']
        area_name = request.form.get('area_name', 'area_sin_nombre')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nombre de archivo vacío'})
        
        result = mission_service.upload_cartography(file, area_name)
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error subiendo cartografía: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@mission_blueprint.route('/cartography/areas', methods=['GET'])
def get_loaded_areas():
    """Obtiene las áreas de cartografía cargadas."""
    try:
        if not mission_service:
            return jsonify({'success': False, 'error': 'Servicio no inicializado'})
            
        result = mission_service.get_loaded_areas()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error obteniendo áreas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}) 