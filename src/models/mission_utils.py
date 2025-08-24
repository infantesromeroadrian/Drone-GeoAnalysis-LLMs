#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades matemáticas y geográficas para misiones de drones.
Funciones puras para cálculos de distancia y geometría.
"""

import math
from typing import Tuple, List, Optional, Dict
from .mission_models import MissionArea


def calculate_distance(point1: Tuple[float, float], 
                      point2: Tuple[float, float]) -> float:
    """
    Calcula distancia entre dos puntos GPS en metros usando fórmula haversine.
    
    Args:
        point1: Tupla (latitud, longitud) del primer punto
        point2: Tupla (latitud, longitud) del segundo punto
        
    Returns:
        float: Distancia en metros
    """
    lat1, lon1 = math.radians(point1[0]), math.radians(point1[1])
    lat2, lon2 = math.radians(point2[0]), math.radians(point2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000  # Radio de la Tierra en metros
    
    return c * r


def calculate_area_center(area: MissionArea) -> Optional[Tuple[float, float]]:
    """
    Calcula el centro geográfico de un área de misión.
    
    Args:
        area: Área de misión con boundaries definidos
        
    Returns:
        Tuple[float, float]: (latitud, longitud) del centro o None
    """
    if not area.boundaries:
        # Si no hay boundaries, usar el primer POI
        if area.points_of_interest:
            return area.points_of_interest[0]['coordinates']
        return None
    
    # Calcular centro de los boundaries
    lats = [coord[0] for coord in area.boundaries]
    lngs = [coord[1] for coord in area.boundaries]
    
    center_lat = sum(lats) / len(lats)
    center_lng = sum(lngs) / len(lngs)
    
    return (center_lat, center_lng)


def calculate_total_mission_distance(waypoints: List[Dict]) -> float:
    """
    Calcula la distancia total de una misión basada en waypoints.
    
    Args:
        waypoints: Lista de waypoints con coordenadas
        
    Returns:
        float: Distancia total en metros
    """
    if len(waypoints) < 2:
        return 0.0
    
    total_distance = 0.0
    
    for i in range(1, len(waypoints)):
        prev_wp = waypoints[i-1]
        curr_wp = waypoints[i]
        
        distance = calculate_distance(
            (prev_wp['latitude'], prev_wp['longitude']),
            (curr_wp['latitude'], curr_wp['longitude'])
        )
        total_distance += distance
    
    return total_distance


def estimate_flight_time(distance_meters: float, 
                        average_speed_ms: float = 10.0) -> float:
    """
    Estima el tiempo de vuelo basado en distancia y velocidad promedio.
    
    Args:
        distance_meters: Distancia total en metros
        average_speed_ms: Velocidad promedio en m/s (default: 10 m/s)
        
    Returns:
        float: Tiempo estimado en segundos
    """
    if distance_meters <= 0 or average_speed_ms <= 0:
        return 0.0
    
    return distance_meters / average_speed_ms


def is_point_in_boundaries(point: Tuple[float, float], 
                          boundaries: List[Tuple[float, float]]) -> bool:
    """
    Verifica si un punto está dentro de los límites geográficos.
    Usa algoritmo de ray casting.
    
    Args:
        point: Punto a verificar (lat, lng)
        boundaries: Lista de puntos que forman el polígono
        
    Returns:
        bool: True si el punto está dentro
    """
    if len(boundaries) < 3:
        return False
    
    x, y = point
    n = len(boundaries)
    inside = False
    
    p1x, p1y = boundaries[0]
    for i in range(1, n + 1):
        p2x, p2y = boundaries[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside


def generate_grid_waypoints(area: MissionArea, 
                           grid_spacing: float = 100.0,
                           altitude: float = 50.0) -> List[Dict]:
    """
    Genera waypoints en patrón de grilla dentro de un área.
    
    Args:
        area: Área de misión
        grid_spacing: Espaciado de la grilla en metros
        altitude: Altitud de vuelo en metros
        
    Returns:
        List[Dict]: Lista de waypoints generados
    """
    if not area.boundaries:
        return []
    
    # Calcular bounding box
    lats = [coord[0] for coord in area.boundaries]
    lngs = [coord[1] for coord in area.boundaries]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)
    
    # Convertir espaciado a grados (aproximadamente)
    lat_spacing = grid_spacing / 111000  # 1 grado ≈ 111km
    lng_spacing = grid_spacing / (111000 * math.cos(math.radians(min_lat)))
    
    waypoints = []
    current_lat = min_lat
    
    while current_lat <= max_lat:
        current_lng = min_lng
        while current_lng <= max_lng:
            point = (current_lat, current_lng)
            
            # Verificar si el punto está dentro del área
            if is_point_in_boundaries(point, area.boundaries):
                waypoint = {
                    'latitude': current_lat,
                    'longitude': current_lng,
                    'altitude': altitude,
                    'action': 'scan',
                    'duration': 5.0,
                    'description': f'Grid scan point'
                }
                waypoints.append(waypoint)
            
            current_lng += lng_spacing
        current_lat += lat_spacing
    
    return waypoints 