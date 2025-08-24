#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de seguridad para misiones de drones.
Implementa reglas de seguridad y verificaciones de waypoints.
"""

import logging
from typing import Dict, List
from .mission_utils import calculate_distance

logger = logging.getLogger(__name__)


def validate_mission_safety(mission: Dict) -> List[str]:
    """
    Valida la seguridad completa de una misión.
    
    Args:
        mission: Diccionario con datos de la misión
        
    Returns:
        List[str]: Lista de advertencias de seguridad
    """
    warnings = []
    
    waypoints = mission.get('waypoints', [])
    if not waypoints:
        warnings.append("Misión sin waypoints definidos")
        return warnings
    
    for i, waypoint in enumerate(waypoints):
        waypoint_warnings = _validate_waypoint_safety(waypoint, i, mission)
        warnings.extend(waypoint_warnings)
    
    return warnings


def _validate_waypoint_safety(waypoint: Dict, index: int, 
                             mission: Dict) -> List[str]:
    """
    Valida la seguridad de un waypoint específico.
    
    Args:
        waypoint: Datos del waypoint
        index: Índice del waypoint en la misión
        mission: Datos completos de la misión
        
    Returns:
        List[str]: Advertencias específicas del waypoint
    """
    warnings = []
    
    # Validar altitud
    altitude_warnings = _validate_altitude(waypoint, index)
    warnings.extend(altitude_warnings)
    
    # Validar distancia entre waypoints
    if index > 0:
        distance_warnings = _validate_distance_between_waypoints(
            waypoint, index, mission
        )
        warnings.extend(distance_warnings)
    
    # Validar coordenadas
    coordinate_warnings = _validate_coordinates(waypoint, index)
    warnings.extend(coordinate_warnings)
    
    return warnings


def _validate_altitude(waypoint: Dict, index: int) -> List[str]:
    """Valida la altitud del waypoint."""
    warnings = []
    altitude = waypoint.get('altitude', 0)
    
    # Límite legal en muchos países
    if altitude > 120:  
        warnings.append(
            f"Waypoint {index+1}: Altitud excede límite legal (120m)"
        )
    
    # Altitud mínima de seguridad
    if altitude < 1:
        warnings.append(
            f"Waypoint {index+1}: Altitud muy baja, riesgo de colisión"
        )
    
    return warnings


def _validate_distance_between_waypoints(waypoint: Dict, index: int, 
                                       mission: Dict) -> List[str]:
    """Valida la distancia entre waypoints consecutivos."""
    warnings = []
    
    prev_waypoint = mission['waypoints'][index-1]
    distance = calculate_distance(
        (prev_waypoint['latitude'], prev_waypoint['longitude']),
        (waypoint['latitude'], waypoint['longitude'])
    )
    
    # Distancia máxima recomendada
    if distance > 10000:  # 10km
        warnings.append(
            f"Waypoint {index+1}: Distancia muy larga "
            f"({distance/1000:.1f}km)"
        )
    
    return warnings


def _validate_coordinates(waypoint: Dict, index: int) -> List[str]:
    """Valida las coordenadas GPS del waypoint."""
    warnings = []
    
    latitude = waypoint.get('latitude', 0)
    longitude = waypoint.get('longitude', 0)
    
    # Validar rango de latitud
    if not -90 <= latitude <= 90:
        warnings.append(
            f"Waypoint {index+1}: Latitud inválida ({latitude})"
        )
    
    # Validar rango de longitud
    if not -180 <= longitude <= 180:
        warnings.append(
            f"Waypoint {index+1}: Longitud inválida ({longitude})"
        )
    
    return warnings


def validate_mission_duration(mission: Dict) -> List[str]:
    """
    Valida la duración estimada de la misión.
    
    Args:
        mission: Datos de la misión
        
    Returns:
        List[str]: Advertencias sobre duración
    """
    warnings = []
    
    estimated_duration = mission.get('estimated_duration', 0)
    
    # Duración máxima recomendada (en minutos)
    if estimated_duration > 120:  # 2 horas
        warnings.append(
            f"Duración excesiva: {estimated_duration} minutos. "
            "Considerar división en misiones más cortas."
        )
    
    # Calcular duración real basada en waypoints
    actual_duration = sum(
        wp.get('duration', 0) for wp in mission.get('waypoints', [])
    )
    
    # Verificar coherencia
    if abs(estimated_duration * 60 - actual_duration) > 300:  # 5 min diff
        warnings.append(
            "Discrepancia entre duración estimada y suma de waypoints"
        )
    
    return warnings 