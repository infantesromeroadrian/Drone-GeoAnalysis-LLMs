#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de drones para lógica de negocio.
Responsabilidad única: Gestionar operaciones y simulaciones de drones.
"""

import logging
import time
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class DroneService:
    """
    Servicio que encapsula la lógica de negocio para operaciones de drones.
    Maneja tanto drones reales como simulaciones.
    """
    
    def __init__(self, drone_controller, video_processor):
        """
        Inicializa el servicio de drones.
        
        Args:
            drone_controller: Controlador de dron (real o mock)
            video_processor: Procesador de video
        """
        self.drone_controller = drone_controller
        self.video_processor = video_processor
        logger.info("Servicio de drones inicializado")
    
    def connect(self) -> Dict[str, Any]:
        """Conecta con el dron y retorna el estado."""
        try:
            success = self.drone_controller.connect()
            
            if success:
                # Obtener posición inicial después de conectar
                position = self._get_current_position()
                return {
                    'success': True,
                    'position': position
                }
            else:
                return {'success': False, 'error': 'Error al conectar con el dron'}
                
        except Exception as e:
            logger.error(f"Error en conexión: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def disconnect(self) -> Dict[str, Any]:
        """Desconecta del dron."""
        try:
            success = self.drone_controller.disconnect()
            return {'success': success}
            
        except Exception as e:
            logger.error(f"Error en desconexión: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def takeoff(self, altitude: float) -> Dict[str, Any]:
        """Despega el dron a la altitud especificada."""
        try:
            # Validar altitud
            if not self._validate_altitude(altitude):
                return {
                    'success': False, 
                    'error': f'Altitud inválida: {altitude}m. Máximo permitido: 120m'
                }
            
            success = self.drone_controller.take_off(altitude)
            return {'success': success}
            
        except Exception as e:
            logger.error(f"Error en despegue: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def land(self) -> Dict[str, Any]:
        """Aterriza el dron."""
        try:
            success = self.drone_controller.land()
            return {'success': success}
            
        except Exception as e:
            logger.error(f"Error en aterrizaje: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def start_video_stream(self) -> Dict[str, Any]:
        """Inicia la transmisión de video."""
        try:
            stream_url = self.drone_controller.start_video_stream()
            success = self.video_processor.start_processing(stream_url)
            
            return {'success': success}
            
        except Exception as e:
            logger.error(f"Error iniciando stream: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def stop_video_stream(self) -> Dict[str, Any]:
        """Detiene la transmisión de video."""
        try:
            self.video_processor.stop_processing()
            success = self.drone_controller.stop_video_stream()
            
            return {'success': success}
            
        except Exception as e:
            logger.error(f"Error deteniendo stream: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Obtiene datos de telemetría del dron."""
        try:
            telemetry = self.drone_controller.get_telemetry()
            return {'success': True, 'telemetry': telemetry}
            
        except Exception as e:
            logger.error(f"Error obteniendo telemetría: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_simulation_paths(self) -> Dict[str, Any]:
        """Obtiene rutas predefinidas para simulación."""
        try:
            paths = self._generate_simulation_paths()
            return {'success': True, 'paths': paths}
            
        except Exception as e:
            logger.error(f"Error obteniendo rutas: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def start_simulation(self, path_id: str) -> Dict[str, Any]:
        """Inicia una simulación de vuelo."""
        try:
            simulation_id = f'sim_{int(time.time())}'
            return {
                'success': True,
                'message': f'Simulación iniciada para ruta {path_id}',
                'simulation_id': simulation_id
            }
            
        except Exception as e:
            logger.error(f"Error iniciando simulación: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_current_position(self) -> Dict[str, float]:
        """Obtiene la posición actual del dron."""
        try:
            return {
                'latitude': self.drone_controller.current_position["latitude"],
                'longitude': self.drone_controller.current_position["longitude"]
            }
        except:
            # Posición por defecto si no se puede obtener
            return {'latitude': 40.416775, 'longitude': -3.703790}
    
    def _validate_altitude(self, altitude: float) -> bool:
        """Valida que la altitud esté dentro de límites legales."""
        return 0 < altitude <= 120.0  # Límite legal de 120m
    
    def _generate_simulation_paths(self) -> List[Dict[str, Any]]:
        """Genera rutas de simulación predefinidas."""
        return [
            {
                "id": "route_1",
                "name": "Reconocimiento urbano",
                "description": "Ruta de reconocimiento urbano básico",
                "waypoints": [
                    {"lat": 40.416775, "lng": -3.703790, "alt": 50},
                    {"lat": 40.415800, "lng": -3.702500, "alt": 80},
                    {"lat": 40.414900, "lng": -3.704000, "alt": 100},
                    {"lat": 40.416200, "lng": -3.705500, "alt": 80},
                    {"lat": 40.417500, "lng": -3.704800, "alt": 50},
                    {"lat": 40.416775, "lng": -3.703790, "alt": 30}
                ]
            },
            {
                "id": "route_2",
                "name": "Patrulla perimetral",
                "description": "Ruta circular para vigilancia de perímetro",
                "waypoints": [
                    {"lat": 40.416775, "lng": -3.703790, "alt": 50},
                    {"lat": 40.417900, "lng": -3.702000, "alt": 60},
                    {"lat": 40.419100, "lng": -3.703400, "alt": 70},
                    {"lat": 40.418400, "lng": -3.705900, "alt": 70},
                    {"lat": 40.416500, "lng": -3.706200, "alt": 60},
                    {"lat": 40.415200, "lng": -3.704900, "alt": 50},
                    {"lat": 40.416775, "lng": -3.703790, "alt": 40}
                ]
            },
            {
                "id": "route_3",
                "name": "Exploración en zigzag",
                "description": "Patrón de búsqueda en zigzag para cubrir área",
                "waypoints": [
                    {"lat": 40.416775, "lng": -3.703790, "alt": 60},
                    {"lat": 40.417800, "lng": -3.702500, "alt": 80},
                    {"lat": 40.418700, "lng": -3.704200, "alt": 100},
                    {"lat": 40.417600, "lng": -3.705800, "alt": 100},
                    {"lat": 40.416500, "lng": -3.707100, "alt": 80},
                    {"lat": 40.415400, "lng": -3.705700, "alt": 60},
                    {"lat": 40.414300, "lng": -3.704200, "alt": 50},
                    {"lat": 40.415500, "lng": -3.702800, "alt": 40},
                    {"lat": 40.416775, "lng": -3.703790, "alt": 30}
                ]
            }
        ] 