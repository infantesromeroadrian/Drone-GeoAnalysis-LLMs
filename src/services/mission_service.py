#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de misiones para lógica de negocio.
Responsabilidad única: Gestionar misiones y planificación LLM.
"""

import logging
import tempfile
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MissionService:
    """
    Servicio que encapsula la lógica de negocio para misiones.
    Maneja planificación LLM, cartografía y validación de misiones.
    """
    
    def __init__(self, mission_planner, drone_controller):
        """
        Inicializa el servicio de misiones.
        
        Args:
            mission_planner: Planificador de misiones LLM
            drone_controller: Controlador de dron
        """
        self.mission_planner = mission_planner
        self.drone_controller = drone_controller
        logger.info("Servicio de misiones inicializado")
    
    def get_missions(self) -> Dict[str, Any]:
        """Obtiene lista de misiones disponibles."""
        try:
            # Obtener misiones básicas predefinidas
            basic_missions = self._get_basic_missions()
            
            return {'success': True, 'missions': basic_missions}
            
        except Exception as e:
            logger.error(f"Error obteniendo misiones: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def start_mission(self, mission_id: str) -> Dict[str, Any]:
        """Inicia una misión específica."""
        try:
            # En una implementación real, esto cargaría la misión y la ejecutaría
            logger.info(f"Iniciando misión: {mission_id}")
            return {'success': True, 'message': f'Misión {mission_id} iniciada'}
            
        except Exception as e:
            logger.error(f"Error iniciando misión: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def abort_mission(self) -> Dict[str, Any]:
        """Aborta la misión actual."""
        try:
            logger.info("Abortando misión actual")
            return {'success': True, 'message': 'Misión abortada'}
            
        except Exception as e:
            logger.error(f"Error abortando misión: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_llm_mission(self, natural_command: str, area_name: Optional[str] = None) -> Dict[str, Any]:
        """Crea una misión usando comandos en lenguaje natural con LLM."""
        try:
            # Crear misión usando LLM
            mission = self.mission_planner.create_mission_from_command(
                natural_command, area_name
            )
            
            if mission:
                # Validar seguridad (usando validación del módulo refactorizado)
                from src.models.mission_validator import validate_mission_safety
                warnings = validate_mission_safety(mission)
                mission['safety_warnings'] = warnings
                
                return {
                    'success': True, 
                    'mission': mission,
                    'safety_warnings': warnings
                }
            else:
                return {'success': False, 'error': 'Error creando misión con LLM'}
                
        except Exception as e:
            logger.error(f"Error creando misión LLM: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def adaptive_control(self, mission_id: str, current_position: tuple, 
                        situation_report: str) -> Dict[str, Any]:
        """Control adaptativo de misión usando LLM."""
        try:
            # Crear una función de adaptación básica
            # En una implementación real, esto usaría el LLM para tomar decisiones
            
            decision = {
                'action': 'continue',
                'reason': f'Misión {mission_id} continúa según plan',
                'adjustments': [],
                'confidence': 0.8
            }
            
            # Análisis básico de la situación
            if 'emergency' in situation_report.lower():
                decision = {
                    'action': 'abort',
                    'reason': 'Emergencia detectada en reporte de situación',
                    'adjustments': ['return_to_base'],
                    'confidence': 0.9
                }
            elif 'weather' in situation_report.lower():
                decision = {
                    'action': 'adjust',
                    'reason': 'Condiciones meteorológicas requieren ajuste',
                    'adjustments': ['reduce_altitude', 'increase_safety_margin'],
                    'confidence': 0.7
                }
            
            return {'success': True, 'decision': decision}
            
        except Exception as e:
            logger.error(f"Error en control adaptativo: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_llm_missions(self) -> Dict[str, Any]:
        """Obtiene lista de misiones LLM creadas."""
        try:
            missions = self.mission_planner.get_available_missions()
            return {'success': True, 'missions': missions}
            
        except Exception as e:
            logger.error(f"Error obteniendo misiones LLM: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def upload_cartography(self, file, area_name: str) -> Dict[str, Any]:
        """Sube y procesa archivos de cartografía."""
        try:
            logger.info(f"Iniciando carga de cartografía: {file.filename} para área: {area_name}")
            
            # Validar archivo
            if not file.filename:
                return {'success': False, 'error': 'Nombre de archivo vacío'}
            
            # Verificar extensión
            if not file.filename.lower().endswith(('.geojson', '.json')):
                return {
                    'success': False, 
                    'error': f'Formato no soportado: {file.filename}. Solo se aceptan archivos .geojson o .json'
                }
            
            # Guardar archivo temporalmente
            logger.info(f"Guardando archivo temporal: {file.filename}")
            temp_path = self._save_temp_file(file)
            
            # Verificar que el archivo se guardó correctamente
            if not os.path.exists(temp_path):
                return {'success': False, 'error': 'Error al guardar archivo temporal'}
            
            # Verificar contenido del archivo
            try:
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content_preview = f.read(200)  # Leer primeros 200 caracteres
                logger.info(f"Contenido inicial del archivo: {content_preview[:100]}...")
                
                # Verificar que no sea HTML
                if content_preview.strip().lower().startswith('<!doctype') or '<html' in content_preview.lower():
                    return {
                        'success': False, 
                        'error': 'El archivo parece ser HTML en lugar de GeoJSON. Verifica que subiste el archivo correcto.'
                    }
                
            except Exception as read_error:
                logger.error(f"Error leyendo archivo: {read_error}")
                return {'success': False, 'error': f'Error leyendo archivo: {str(read_error)}'}
            
            # Cargar cartografía
            logger.info(f"Procesando cartografía con mission_planner...")
            success = self.mission_planner.load_cartography(temp_path, area_name)
            
            if success:
                logger.info(f"Cartografía cargada exitosamente: {area_name}")
                
                # Obtener coordenadas del centro
                center_coordinates = self.mission_planner.get_area_center_coordinates(area_name)
                
                response_data = {
                    'success': True, 
                    'message': f'Cartografía "{area_name}" cargada correctamente',
                    'area_name': area_name
                }
                
                # Agregar coordenadas del centro si están disponibles
                if center_coordinates:
                    response_data['center_coordinates'] = {
                        'latitude': center_coordinates[0],
                        'longitude': center_coordinates[1]
                    }
                    
                    # Actualizar posición del dron mock
                    if hasattr(self.drone_controller, 'update_position'):
                        self.drone_controller.update_position(
                            center_coordinates[0], center_coordinates[1]
                        )
                
                # Limpiar archivo temporal
                try:
                    os.remove(temp_path)
                except:
                    pass  # No es crítico si no se puede limpiar
                
                return response_data
            else:
                logger.error(f"Error en mission_planner.load_cartography para {area_name}")
                return {
                    'success': False, 
                    'error': 'Error procesando cartografía. Verifica que el archivo GeoJSON sea válido.'
                }
                
        except Exception as e:
            logger.error(f"Error general subiendo cartografía: {str(e)}", exc_info=True)
            return {
                'success': False, 
                'error': f'Error interno del servidor: {str(e)}'
            }
    
    def get_loaded_areas(self) -> Dict[str, Any]:
        """Obtiene las áreas de cartografía cargadas."""
        try:
            areas = []
            
            # Usar CartographyManager a través del mission_planner refactorizado
            if hasattr(self.mission_planner, 'cartography_manager'):
                loaded_areas = self.mission_planner.cartography_manager.get_loaded_areas()
                for area_name, area_data in loaded_areas.items():
                    areas.append({
                        'name': area_name,
                        'boundaries_count': len(area_data.boundaries),
                        'poi_count': len(area_data.points_of_interest or [])
                    })
            
            return {'success': True, 'areas': areas}
            
        except Exception as e:
            logger.error(f"Error obteniendo áreas: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_basic_missions(self) -> List[Dict[str, Any]]:
        """Obtiene misiones básicas predefinidas."""
        return [
            {'id': '1', 'name': 'Reconocimiento Área 1'},
            {'id': '2', 'name': 'Vigilancia Perímetro'},
            {'id': '3', 'name': 'Inspección Estructura'}
        ]
    
    def _save_temp_file(self, file) -> str:
        """Guarda archivo en directorio temporal."""
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        return temp_path 