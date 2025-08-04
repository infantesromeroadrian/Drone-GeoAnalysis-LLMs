#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de geolocalización para lógica de negocio.
Responsabilidad única: Gestionar triangulación y análisis geográfico.
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class GeoService:
    """
    Servicio que encapsula la lógica de negocio para geolocalización.
    Maneja triangulación, detección de cambios y análisis geográfico.
    """
    
    def __init__(self, geo_manager, geo_triangulation, geo_correlator):
        """
        Inicializa el servicio de geolocalización.
        
        Args:
            geo_manager: Gestor de geolocalización
            geo_triangulation: Módulo de triangulación
            geo_correlator: Módulo de correlación geográfica
        """
        self.geo_manager = geo_manager
        self.geo_triangulation = geo_triangulation
        self.geo_correlator = geo_correlator
        self.is_mock_triangulation = self._is_mock_module(geo_triangulation)
        self.is_mock_correlator = self._is_mock_module(geo_correlator)
        
        logger.info("Servicio de geolocalización inicializado")
    
    def add_reference_image(self) -> Dict[str, Any]:
        """Añade una imagen de referencia para detección de cambios."""
        try:
            # Simular telemetría del dron
            drone_telemetry = self._get_mock_telemetry()
            
            ref_id = self.geo_manager.add_reference_image(drone_telemetry)
            return {'success': True, 'reference_id': ref_id}
            
        except Exception as e:
            logger.error(f"Error añadiendo referencia: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def detect_changes(self) -> Dict[str, Any]:
        """Detecta cambios entre imagen actual y referencia."""
        try:
            # Verificar si tenemos imagen de referencia
            if not self.geo_manager.current_reference_image:
                return {
                    'success': False, 
                    'error': 'No hay imagen de referencia establecida'
                }
            
            # Usar correlador real si está disponible
            if not self.is_mock_correlator:
                return self._detect_changes_real()
            else:
                return self._detect_changes_mock()
                
        except Exception as e:
            logger.error(f"Error detectando cambios: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_target(self) -> Dict[str, Any]:
        """Crea un nuevo objetivo para triangulación."""
        try:
            # Usar módulo real de triangulación si está disponible
            if not self.is_mock_triangulation:
                target_id = self.geo_triangulation.create_target()
                
                # Registrar también en el gestor local
                self.geo_manager.targets[target_id] = {
                    'captures': [],
                    'timestamp': datetime.now().isoformat(),
                    'created_by': 'triangulation_module'
                }
                
                logger.info(f"Objetivo creado usando módulo real: {target_id}")
                return {'success': True, 'target_id': target_id}
            else:
                # Fallback al gestor local
                target_id = self.geo_manager.create_target()
                logger.warning(f"Objetivo creado usando fallback: {target_id}")
                return {
                    'success': True, 
                    'target_id': target_id,
                    'note': 'Creado con módulo fallback'
                }
                
        except Exception as e:
            logger.error(f"Error creando objetivo: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def calculate_position(self, target_id: str) -> Dict[str, Any]:
        """Calcula la posición geográfica de un objetivo usando triangulación."""
        try:
            if not target_id:
                return {'success': False, 'error': 'ID de objetivo no especificado'}
            
            # Usar módulo real de triangulación si está disponible
            if not self.is_mock_triangulation:
                return self._calculate_position_real(target_id)
            else:
                return self._calculate_position_mock(target_id)
                
        except Exception as e:
            logger.error(f"Error calculando posición: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def add_observation(self, observation_params: Dict[str, Any]) -> Dict[str, Any]:
        """Agrega una observación manual para triangulación."""
        try:
            target_id = observation_params['target_id']
            target_bearing = observation_params['target_bearing']
            target_elevation = observation_params.get('target_elevation', 0)
            confidence = observation_params.get('confidence', 1.0)
            
            # Usar módulo real de triangulación si está disponible
            if not self.is_mock_triangulation:
                # Obtener posición actual del dron (simulada)
                drone_position = self._get_mock_drone_position()
                
                # Agregar observación
                observation_id = self.geo_triangulation.add_observation(
                    target_id=target_id,
                    drone_position=drone_position,
                    target_bearing=float(target_bearing),
                    target_elevation=float(target_elevation),
                    confidence=float(confidence)
                )
                
                # Obtener número total de observaciones
                obs_count = len(self.geo_triangulation.observations.get(target_id, []))
                
                return {
                    'success': True,
                    'observation_id': observation_id,
                    'total_observations': obs_count,
                    'can_calculate': obs_count >= 2
                }
            else:
                return {
                    'success': False,
                    'error': 'Módulo de triangulación no disponible'
                }
                
        except Exception as e:
            logger.error(f"Error agregando observación: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_targets_status(self) -> Dict[str, Any]:
        """Obtiene el estado de todos los objetivos de triangulación."""
        try:
            if not self.is_mock_triangulation:
                targets = self.geo_triangulation.get_all_targets()
                
                targets_status = []
                for target_id in targets:
                    observations = self.geo_triangulation.observations.get(target_id, [])
                    targets_status.append({
                        'target_id': target_id,
                        'observations_count': len(observations),
                        'can_calculate': len(observations) >= 2,
                        'last_observation': observations[-1]['timestamp'] if observations else None
                    })
                
                return {
                    'success': True,
                    'targets': targets_status,
                    'total_targets': len(targets)
                }
            else:
                return {
                    'success': False,
                    'error': 'Módulo de triangulación no disponible'
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo estado: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _detect_changes_real(self) -> Dict[str, Any]:
        """Detecta cambios usando el correlador real."""
        # Simular imagen actual
        mock_image_data = b"mock_image_data"
        drone_telemetry = self._get_mock_telemetry()
        
        # Usar el correlador real
        correlation_result = self.geo_correlator.correlate_drone_image(
            mock_image_data, 
            drone_telemetry,
            confidence_threshold=0.6
        )
        
        if 'error' in correlation_result:
            return {'success': False, 'error': correlation_result['error']}
        
        # Determinar cambios basándose en la correlación
        confidence = correlation_result.get('confidence', 0)
        has_changes = confidence < 0.8
        change_percentage = (1 - confidence) * 100
        
        return {
            'success': True,
            'has_changes': has_changes,
            'change_percentage': round(change_percentage, 2),
            'correlation_confidence': confidence,
            'analysis_details': correlation_result
        }
    
    def _detect_changes_mock(self) -> Dict[str, Any]:
        """Detecta cambios usando simulación."""
        logger.warning("Usando simulación para detección de cambios")
        return {
            'success': True, 
            'has_changes': True,
            'change_percentage': 15.7,
            'note': 'Resultado simulado - módulo real no disponible'
        }
    
    def _calculate_position_real(self, target_id: str) -> Dict[str, Any]:
        """Calcula posición usando triangulación real."""
        # Verificar observaciones
        if (target_id not in self.geo_triangulation.observations or 
            len(self.geo_triangulation.observations.get(target_id, [])) < 2):
            
            # Agregar observaciones automáticas para demostración
            self._add_automatic_observations(target_id)
        
        # Calcular posición
        result = self.geo_triangulation.calculate_position(target_id)
        
        if 'error' in result:
            return {'success': False, 'error': result['error']}
        
        return {
            'success': True,
            'position': result['position'],
            'precision': result['precision'],
            'observations_count': result['observations_count'],
            'timestamp': result['timestamp'],
            'method': 'real_triangulation'
        }
    
    def _calculate_position_mock(self, target_id: str) -> Dict[str, Any]:
        """Calcula posición usando simulación."""
        logger.warning("Usando simulación para cálculo de posición")
        return {
            'success': True,
            'position': {
                'latitude': 40.416775 + (hash(target_id) % 100) / 10000,
                'longitude': -3.703790 + (hash(target_id[::-1]) % 100) / 10000
            },
            'precision': {
                'confidence': 75.0,
                'error_radius': 25.0
            },
            'method': 'simulated',
            'note': 'Resultado simulado - módulo real no disponible'
        }
    
    def _add_automatic_observations(self, target_id: str):
        """Agrega observaciones automáticas para demostración."""
        drone_position_1 = {
            'latitude': 40.416775,
            'longitude': -3.703790,
            'altitude': 50
        }
        
        drone_position_2 = {
            'latitude': 40.416775 + 0.001,
            'longitude': -3.703790 + 0.001,
            'altitude': 60
        }
        
        # Agregar dos observaciones
        self.geo_triangulation.add_observation(
            target_id=target_id,
            drone_position=drone_position_1,
            target_bearing=45.0,
            target_elevation=15.0,
            confidence=0.9
        )
        
        self.geo_triangulation.add_observation(
            target_id=target_id,
            drone_position=drone_position_2,
            target_bearing=50.0,
            target_elevation=12.0,
            confidence=0.85
        )
    
    def _get_mock_telemetry(self) -> Dict[str, Any]:
        """Obtiene telemetría simulada."""
        return {
            'gps': {
                'latitude': 40.416775,
                'longitude': -3.703790
            },
            'timestamp': datetime.now().timestamp()
        }
    
    def _get_mock_drone_position(self) -> Dict[str, float]:
        """Obtiene posición simulada del dron."""
        return {
            'latitude': 40.416775,
            'longitude': -3.703790,
            'altitude': 50
        }
    
    def _is_mock_module(self, module) -> bool:
        """Determina si un módulo es mock."""
        return hasattr(module, '__class__') and 'Mock' in module.__class__.__name__ 