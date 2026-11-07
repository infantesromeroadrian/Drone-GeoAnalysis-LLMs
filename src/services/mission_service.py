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
from werkzeug.utils import secure_filename

from src.safety.approval import ApprovalError, MissionGate
from src.safety.schemas import MissionAmendment

logger = logging.getLogger(__name__)

class MissionService:
    """
    Servicio que encapsula la lógica de negocio para misiones.
    Maneja planificación LLM, cartografía y validación de misiones.
    """
    
    def __init__(self, mission_planner, drone_controller, mission_executor=None, gate: Optional[MissionGate] = None):
        self.mission_planner = mission_planner
        self.drone_controller = drone_controller
        self.executor = mission_executor
        # One gate for the whole process: the executor redeems tokens issued by this same instance.
        self.gate = gate or getattr(mission_executor, "_gate", None) or MissionGate()
        if mission_executor is not None and getattr(mission_executor, "_gate", None) is None:
            mission_executor._gate = self.gate
        self._pending: Dict[str, Dict[str, Any]] = {}
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
    
    def start_mission(self, mission_id: str, approval_token: Optional[str] = None) -> Dict[str, Any]:
        """Inicia la ejecucion de una mision aprobada (delega al executor, que exige el token)."""
        return self.execute_mission(mission_id, approval_token)

    def abort_mission(self) -> Dict[str, Any]:
        """Aborta la mision en curso."""
        return self.abort_execution()

    # -- safety envelope + approval ------------------------------------------------------------
    def _drone_position(self):
        pos = self.drone_controller.current_position
        return (float(pos["latitude"]), float(pos["longitude"]))

    def create_llm_mission(self, natural_command: str, area_name: Optional[str] = None) -> Dict[str, Any]:
        """Crea una misión con el LLM. Success solo si pasa la envolvente determinista.

        Una misión aceptada NO es ejecutable: requiere aprobación del operador (approve_mission).
        """
        try:
            mission = self.mission_planner.create_mission_from_command(natural_command, area_name)
            if not mission:
                return {'success': False, 'error': 'Error creando misión con LLM'}

            from src.models.mission_validator import validate_mission_safety
            warnings = validate_mission_safety(mission)  # advisory only; the envelope is the control
            mission['safety_warnings'] = warnings

            mission_id = str(mission.get('id', ''))
            review = self.gate.review(mission_id, mission, self._drone_position())
            if not review.ok:
                return {
                    'success': False,
                    'error': 'Mission rejected by safety envelope',
                    'mission_id': mission_id,
                    'violations': [v.model_dump() for v in review.violations],
                    'safety_warnings': warnings,
                }
            return {
                'success': True,
                'mission': mission,
                'safety_warnings': warnings,
                'requires_approval': True,
                'mission_hash': review.mission_hash,
                'review': review.summary,
            }
        except Exception as e:
            logger.error(f"Error creando misión LLM: {str(e)}")
            return {'success': False, 'error': str(e)}

    def review_mission(self, mission_id: str) -> Dict[str, Any]:
        """Revisión completa de una misión almacenada (lo que ve el operador antes de aprobar)."""
        mission = self.executor.load_mission(mission_id) if self.executor else None
        if not mission:
            return {'success': False, 'error': 'Mission not found'}
        ctx = self._pending.get(mission_id)
        home = ctx['home'] if ctx else self._drone_position()
        start = self._drone_position() if ctx else None
        r = self.gate.review(mission_id, mission, home, start)
        return {'success': r.ok, **r.as_dict()}

    def approve_mission(self, mission_id: str, mission_hash: str, approver: str) -> Dict[str, Any]:
        """Aprobación del operador (el endpoint HTTP la autentica). Devuelve un token de un solo uso."""
        mission = self.executor.load_mission(mission_id) if self.executor else None
        if not mission:
            return {'success': False, 'error': 'Mission not found'}
        ctx = self._pending.get(mission_id)
        home = ctx['home'] if ctx else self._drone_position()
        start = self._drone_position() if ctx else None
        try:
            token = self.gate.approve(mission_id, mission, home, mission_hash, approver,
                                      kind=ctx['kind'] if ctx else 'new', start=start)
        except ApprovalError as e:
            return {'success': False, 'error': f'Approval refused: {e.code}', 'code': e.code}
        return {'success': True, 'approval_token': token, 'expires_in_s': self.gate.ttl_s}

    def propose_amendment(self, mission_id: str, amendment: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica una enmienda propuesta por adaptive_control.

        hold/abort/return_to_base reducen riesgo y se aplican; continue no hace nada. Cualquier
        enmienda con coordenadas nuevas es una misión nueva: envolvente completa + nueva aprobación.
        """
        try:
            am = MissionAmendment.model_validate(amendment)
        except Exception as e:
            return {'success': False, 'error': f'Invalid amendment: {e}'}
        if am.action == 'continue':
            return {'success': True, 'applied': 'none'}
        if am.action in ('hold', 'abort', 'return_to_base'):
            return {'success': True, 'applied': am.action, 'result': self.abort_execution()}
        home = getattr(self.drone_controller, 'home_position', None)
        parent = self.executor.load_mission(mission_id) if self.executor else None
        if home is None or parent is None:
            return {'success': False, 'error': 'No home or parent mission for amendment'}
        import uuid
        new = {k: v for k, v in parent.items() if k not in ('waypoints', 'id', 'safety_warnings')}
        new.update(id=str(uuid.uuid4()), parent_mission_id=mission_id, status='amendment',
                   waypoints=am.waypoints_as_dicts())
        review = self.gate.review(new['id'], new, home, self._drone_position())
        if not review.ok:
            return {'success': False, 'error': 'Amendment rejected by safety envelope',
                    'violations': [v.model_dump() for v in review.violations]}
        self.executor.store_mission(new)
        self._pending[new['id']] = {'kind': 'amendment', 'home': (float(home[0]), float(home[1]))}
        return {'success': True, 'applied': 'pending_approval', 'mission_id': new['id'],
                'mission_hash': review.mission_hash, 'review': review.summary}

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
                except Exception as e:
                    logger.debug("No se pudo eliminar archivo temporal %s: %s", temp_path, e)
                
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
        safe_name = secure_filename(file.filename)
        if not safe_name:
            safe_name = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_path = os.path.join(temp_dir, safe_name)
        file.save(temp_path)
        return temp_path

    def execute_mission(self, mission_id: str, approval_token: Optional[str] = None) -> Dict[str, Any]:
        """Ejecuta una mision en background; el executor exige un token de aprobación válido."""
        if not self.executor:
            return {'success': False, 'error': 'Mission executor not available'}
        try:
            return self.executor.start(mission_id, approval_token)
        except Exception as e:
            logger.error("Error executing mission: %s", e)
            return {'success': False, 'error': str(e)}

    def abort_execution(self) -> Dict[str, Any]:
        """Aborta la ejecucion en curso."""
        if not self.executor:
            return {'success': False, 'error': 'Mission executor not available'}
        return self.executor.abort()

    def get_execution_status(self) -> Dict[str, Any]:
        """Obtiene el estado de la ejecucion actual."""
        if not self.executor:
            return {'status': 'idle'}
        return self.executor.get_status()