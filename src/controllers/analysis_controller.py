#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controlador para rutas de análisis de imágenes.
Responsabilidad única: Manejar las APIs HTTP de análisis geográfico y detección YOLO.
"""

import logging
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, session
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Crear blueprint para rutas de análisis
analysis_blueprint = Blueprint('analysis', __name__)

# Variables globales para servicios (se inyectarán desde main)
analysis_service = None
chat_service = None

def init_analysis_controller(service, chat_svc=None):
    """Inicializa el controlador con el servicio de análisis y chat."""
    global analysis_service, chat_service
    analysis_service = service
    chat_service = chat_svc
    logger.info("Controlador de análisis inicializado")

@analysis_blueprint.route('/analyze', methods=['POST'])
def analyze():
    """Procesa una imagen y retorna los resultados del análisis."""
    try:
        if not analysis_service:
            return jsonify({'error': 'Servicio no inicializado', 'status': 'error'}), 500
            
        # Validar entrada
        if 'image' not in request.files:
            return jsonify({'error': 'No se envió ninguna imagen'}), 400
            
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        # Obtener parámetros de configuración
        config_params = _extract_analysis_params(request.form)
        
        # Procesar imagen usando el servicio
        result = analysis_service.analyze_image(image_file, config_params)
        
        # Almacenar contexto para chat si está disponible
        if chat_service and result.get('status') == 'completed':
            session_id = _get_or_create_session_id()
            analysis_results = result.get('results', {})
            yolo_results = analysis_results.get('yolo_detected_objects', {})
            
            # Obtener la imagen codificada para análisis visual específico
            encoded_image, image_format = _get_encoded_image_for_chat(image_file)
            
            chat_service.store_analysis_context(
                session_id=session_id,
                analysis_results=analysis_results,
                yolo_results=yolo_results,
                image_filename=image_file.filename,
                encoded_image=encoded_image,
                image_format=image_format
            )
            
            # Añadir session_id al resultado para el frontend
            result['session_id'] = session_id
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en el análisis: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@analysis_blueprint.route('/results/<path:filename>')
def results(filename):
    """Sirve archivos de resultados guardados."""
    try:
        if not analysis_service:
            return jsonify({'error': 'Servicio no inicializado'}), 500
            
        return analysis_service.serve_result_file(filename)
        
    except Exception as e:
        logger.error(f"Error sirviendo archivo: {str(e)}")
        return jsonify({'error': str(e)}), 500

@analysis_blueprint.route('/api/analysis/status', methods=['GET'])
def analysis_status():
    """Obtiene el estado actual del análisis en progreso."""
    try:
        if not analysis_service:
            return jsonify({'error': 'Servicio no inicializado'}), 500
            
        analysis_id = request.args.get('id')
        result = analysis_service.get_analysis_status(analysis_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error obteniendo estado: {str(e)}")
        return jsonify({'error': str(e)}), 500

@analysis_blueprint.route('/analyze_yolo', methods=['POST'])
def analyze_yolo():
    """Detecta objetos en una imagen usando YOLO 11."""
    try:
        if not analysis_service:
            return jsonify({'error': 'Servicio no inicializado', 'status': 'error'}), 500
            
        # Validar entrada
        if 'image' not in request.files:
            return jsonify({'error': 'No se envió ninguna imagen'}), 400
            
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        # Obtener parámetros de configuración YOLO
        config_params = _extract_yolo_params(request.form)
        
        # Procesar imagen usando YOLO
        result = analysis_service.analyze_objects_yolo(image_file, config_params)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en análisis YOLO: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@analysis_blueprint.route('/yolo/model_info', methods=['GET'])
def yolo_model_info():
    """Obtiene información del modelo YOLO."""
    try:
        if not analysis_service:
            return jsonify({'error': 'Servicio no inicializado'}), 500
            
        result = analysis_service.get_yolo_model_info()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error obteniendo info del modelo YOLO: {str(e)}")
        return jsonify({'error': str(e)}), 500

# === RUTAS DE CHAT CONTEXTUAL ===

@analysis_blueprint.route('/chat/question', methods=['POST'])
def chat_question():
    """Procesa una pregunta sobre la imagen analizada."""
    try:
        if not chat_service:
            return jsonify({'error': 'Servicio de chat no disponible'}), 503
        
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'Pregunta requerida'}), 400
        
        session_id = data.get('session_id') or session.get('analysis_session_id')
        if not session_id:
            return jsonify({'error': 'No hay sesión de análisis activa'}), 400
        
        question = data['question'].strip()
        if not question:
            return jsonify({'error': 'Pregunta vacía'}), 400
        
        # Procesar pregunta
        result = chat_service.ask_question(session_id, question)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en chat: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@analysis_blueprint.route('/chat/history', methods=['GET'])
def chat_history():
    """Obtiene el historial de chat para una sesión."""
    try:
        if not chat_service:
            return jsonify({'error': 'Servicio de chat no disponible'}), 503
        
        session_id = request.args.get('session_id') or session.get('analysis_session_id')
        if not session_id:
            return jsonify({'error': 'No hay sesión de análisis activa'}), 400
        
        history = chat_service.get_chat_history(session_id)
        
        return jsonify({
            'session_id': session_id,
            'chat_history': history,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@analysis_blueprint.route('/chat/suggested_questions', methods=['GET'])
def suggested_questions():
    """Obtiene preguntas sugeridas basadas en el contexto."""
    try:
        if not chat_service:
            return jsonify({'error': 'Servicio de chat no disponible'}), 503
        
        session_id = request.args.get('session_id') or session.get('analysis_session_id')
        if not session_id:
            return jsonify({'error': 'No hay sesión de análisis activa'}), 400
        
        suggestions = chat_service.get_suggested_questions(session_id)
        
        return jsonify({
            'session_id': session_id,
            'suggested_questions': suggestions,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo sugerencias: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@analysis_blueprint.route('/chat/context_summary', methods=['GET'])
def context_summary():
    """Obtiene un resumen del contexto de análisis."""
    try:
        if not chat_service:
            return jsonify({'error': 'Servicio de chat no disponible'}), 503
        
        session_id = request.args.get('session_id') or session.get('analysis_session_id')
        if not session_id:
            return jsonify({'error': 'No hay sesión de análisis activa'}), 400
        
        summary = chat_service.get_context_summary(session_id)
        
        return jsonify({
            'session_id': session_id,
            'context_summary': summary,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo resumen: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@analysis_blueprint.route('/chat/clear_history', methods=['POST'])
def clear_chat_history():
    """Limpia el historial de chat para una sesión."""
    try:
        if not chat_service:
            return jsonify({'error': 'Servicio de chat no disponible'}), 503
        
        data = request.get_json()
        session_id = data.get('session_id') if data else session.get('analysis_session_id')
        if not session_id:
            return jsonify({'error': 'No hay sesión de análisis activa'}), 400
        
        success = chat_service.clear_chat_history(session_id)
        
        return jsonify({
            'session_id': session_id,
            'cleared': success,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error limpiando historial: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

# === FUNCIONES AUXILIARES ===

def _get_or_create_session_id() -> str:
    """Obtiene o crea un ID de sesión único."""
    if 'analysis_session_id' not in session:
        session['analysis_session_id'] = str(uuid.uuid4())
    return session['analysis_session_id']

def _extract_analysis_params(form_data) -> Dict[str, Any]:
    """Extrae y valida parámetros de configuración del análisis."""
    return {
        'confidence_threshold': float(form_data.get('confidence_threshold', 0)),
        'model_version': form_data.get('model_version', 'default'),
        'detail_level': form_data.get('detail_level', 'normal')
    }

def _extract_yolo_params(form_data) -> Dict[str, Any]:
    """Extrae y valida parámetros de configuración para YOLO."""
    return {
        'confidence_threshold': float(form_data.get('yolo_confidence', 0.5)),
        'nms_threshold': float(form_data.get('nms_threshold', 0.4)),
        'model_version': form_data.get('yolo_model', 'yolo11n')
    }

def _get_encoded_image_for_chat(image_file) -> tuple:
    """
    Codifica la imagen para análisis visual específico en el chat.
    
    Args:
        image_file: Archivo de imagen Flask
        
    Returns:
        Tupla con (imagen_codificada, formato)
    """
    try:
        import base64
        import os
        from PIL import Image
        
        # Resetear el puntero del archivo
        image_file.seek(0)
        
        # Leer los datos de la imagen
        image_data = image_file.read()
        
        # Codificar en base64
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        
        # Determinar formato de la imagen
        filename = image_file.filename.lower()
        if filename.endswith('.png'):
            image_format = 'png'
        elif filename.endswith('.gif'):
            image_format = 'gif'
        elif filename.endswith('.webp'):
            image_format = 'webp'
        else:
            image_format = 'jpeg'  # Por defecto
        
        # Resetear el puntero del archivo para futuras operaciones
        image_file.seek(0)
        
        logger.info(f"Imagen codificada para chat: {len(encoded_image)} bytes, formato: {image_format}")
        return encoded_image, image_format
        
    except Exception as e:
        logger.error(f"Error codificando imagen para chat: {str(e)}")
        # Resetear el puntero del archivo en caso de error
        image_file.seek(0)
        return None, "jpeg"