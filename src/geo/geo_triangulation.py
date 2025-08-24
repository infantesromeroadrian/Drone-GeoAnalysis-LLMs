#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Triangulación geográfica basada en múltiples capturas del dron.
"""

import numpy as np
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class GeoTriangulation:
    """Triangulación geográfica basada en múltiples capturas del dron."""
    
    def __init__(self):
        """Inicializa el sistema de triangulación."""
        self.observations = {}  # Observaciones organizadas por ID de objetivo
        logger.info("Sistema de triangulación geográfica inicializado")
    
    def add_observation(self, target_id: str, drone_position: Dict[str, float], 
                       target_bearing: float, target_elevation: float, 
                       confidence: float = 1.0) -> str:
        """
        Añade una observación para triangulación.
        
        Args:
            target_id: Identificador del objetivo
            drone_position: Posición del dron {latitude, longitude, altitude}
            target_bearing: Rumbo hacia el objetivo en grados (0-360)
            target_elevation: Ángulo de elevación hacia el objetivo en grados
            confidence: Confianza en la medición (0-1)
            
        Returns:
            ID de la observación
        """
        if target_id not in self.observations:
            self.observations[target_id] = []
        
        # Generar ID único para esta observación
        observation_id = f"{target_id}_{len(self.observations[target_id])}"
        
        # Guardar observación
        self.observations[target_id].append({
            "id": observation_id,
            "drone_position": drone_position,
            "target_bearing": target_bearing,
            "target_elevation": target_elevation,
            "confidence": confidence,
            "timestamp": time.time()
        })
        
        logger.info(f"Observación añadida para objetivo {target_id}: {observation_id}")
        return observation_id
    
    def calculate_position(self, target_id: str) -> Dict[str, Any]:
        """
        Calcula la posición de un objetivo basándose en múltiples observaciones.
        
        Args:
            target_id: Identificador del objetivo
            
        Returns:
            Posición calculada y metadatos
        """
        # Validar datos de entrada
        validation_result = self._validate_observations(target_id)
        if "error" in validation_result:
            return validation_result
        
        observations = self.observations[target_id]
        
        # Extraer y procesar datos de observaciones
        observation_data = self._extract_observation_data(observations)
        
        # Calcular estimaciones de posición
        estimated_points = self._calculate_estimated_points(observation_data)
        
        # Calcular promedio ponderado
        weighted_position = self._calculate_weighted_average(
            estimated_points, observation_data["weights"]
        )
        
        # Calcular métricas de precisión
        precision_metrics = self._calculate_precision_metrics(
            estimated_points, weighted_position, len(observations)
        )
        
        # Construir resultado final
        return self._build_result(target_id, weighted_position, precision_metrics, len(observations))
    
    def _validate_observations(self, target_id: str) -> Dict[str, Any]:
        """Valida que existan suficientes observaciones."""
        if target_id not in self.observations:
            return {"error": f"Objetivo {target_id} no encontrado"}
        
        observation_count = len(self.observations[target_id])
        if observation_count < 2:
            return {"error": f"Se requieren al menos 2 observaciones (actual: {observation_count})"}
        
        return {"valid": True}
    
    def _extract_observation_data(self, observations: List[Dict]) -> Dict[str, np.ndarray]:
        """Extrae datos relevantes de las observaciones."""
        positions = []
        bearings = []
        elevations = []
        weights = []
        
        for obs in observations:
            pos = obs["drone_position"]
            positions.append([pos["latitude"], pos["longitude"], pos["altitude"]])
            bearings.append(obs["target_bearing"])
            elevations.append(obs["target_elevation"])
            weights.append(obs["confidence"])
        
        return {
            "positions": np.array(positions),
            "bearings": np.array(bearings),
            "elevations": np.array(elevations),
            "weights": np.array(weights)
        }
    
    def _calculate_estimated_points(self, observation_data: Dict[str, np.ndarray]) -> np.ndarray:
        """Calcula puntos estimados de posición desde cada observación."""
        positions = observation_data["positions"]
        bearings = observation_data["bearings"]
        elevations = observation_data["elevations"]
        
        earth_radius = 6371000  # Radio de la Tierra en metros
        estimated_points = []
        
        for i in range(len(positions)):
            lat, lon, alt = positions[i]
            bearing = np.radians(bearings[i])
            elevation = np.radians(elevations[i])
            
            # Calcular distancia estimada
            distance = self._estimate_distance(alt, elevation)
            
            # Calcular nueva posición
            target_coords = self._calculate_target_coordinates(
                lat, lon, bearing, distance, earth_radius
            )
            
            estimated_points.append(target_coords)
        
        return np.array(estimated_points)
    
    def _estimate_distance(self, altitude: float, elevation: float) -> float:
        """Estima la distancia al objetivo basada en altitud y elevación."""
        if elevation > 0:
            distance = altitude / np.sin(elevation)
        else:
            distance = 1000  # Valor por defecto para objetivos bajo el horizonte
        
        # Limitar a un valor razonable
        return min(distance, 10000)  # Máximo 10km
    
    def _calculate_target_coordinates(self, lat: float, lon: float, bearing: float, 
                                    distance: float, earth_radius: float) -> List[float]:
        """Calcula coordenadas del objetivo usando fórmulas geográficas simplificadas."""
        lat_rad = np.radians(lat)
        lon_rad = np.radians(lon)
        
        # Fórmula simplificada para distancias cortas
        target_lat_rad = lat_rad + (distance / earth_radius) * np.cos(bearing)
        target_lon_rad = lon_rad + (distance / earth_radius) * np.sin(bearing) / np.cos(lat_rad)
        
        # Convertir de vuelta a grados
        target_lat = np.degrees(target_lat_rad)
        target_lon = np.degrees(target_lon_rad)
        
        return [target_lat, target_lon]
    
    def _calculate_weighted_average(self, estimated_points: np.ndarray, 
                                  weights: np.ndarray) -> np.ndarray:
        """Calcula el promedio ponderado de los puntos estimados."""
        # Normalizar pesos
        normalized_weights = weights / np.sum(weights)
        
        # Calcular promedio ponderado
        return np.average(estimated_points, axis=0, weights=normalized_weights)
    
    def _calculate_precision_metrics(self, estimated_points: np.ndarray, 
                                   weighted_position: np.ndarray, 
                                   num_observations: int) -> Dict[str, float]:
        """Calcula métricas de precisión basadas en la dispersión de puntos."""
        # Calcular distancias desde el promedio
        distances = np.linalg.norm(estimated_points - weighted_position, axis=1)
        
        max_distance = np.max(distances)
        avg_distance = np.average(distances)
        
        # Calcular confianza basada en dispersión y número de observaciones
        precision_confidence = 100 * (1 - avg_distance / 0.001) * np.tanh(num_observations / 3)
        precision_confidence = max(0, min(99, precision_confidence))
        
        return {
            "meters": float(avg_distance * 111000),  # Conversión aproximada a metros
            "confidence": float(precision_confidence),
            "max_deviation_meters": float(max_distance * 111000)
        }
    
    def _build_result(self, target_id: str, weighted_position: np.ndarray, 
                     precision_metrics: Dict[str, float], observation_count: int) -> Dict[str, Any]:
        """Construye el resultado final de la triangulación."""
        result = {
            "target_id": target_id,
            "position": {
                "latitude": float(weighted_position[0]),
                "longitude": float(weighted_position[1]),
                "altitude": 0  # No estimamos altitud en este ejemplo simplificado
            },
            "precision": precision_metrics,
            "observations_count": observation_count,
            "timestamp": time.time()
        }
        
        logger.info(f"Posición calculada para objetivo {target_id}: {result['position']}")
        return result
    
    def reset_target(self, target_id: str) -> bool:
        """
        Elimina todas las observaciones de un objetivo.
        
        Args:
            target_id: Identificador del objetivo
            
        Returns:
            True si se eliminaron las observaciones
        """
        if target_id in self.observations:
            del self.observations[target_id]
            logger.info(f"Observaciones eliminadas para objetivo {target_id}")
            return True
        return False
    
    def get_all_targets(self) -> List[str]:
        """
        Obtiene todos los IDs de objetivos con observaciones.
        
        Returns:
            Lista de IDs de objetivos
        """
        return list(self.observations.keys())
    
    def create_target(self) -> str:
        """
        Crea un nuevo objetivo con ID único.
        
        Returns:
            ID del nuevo objetivo
        """
        target_id = f"target_{uuid.uuid4().hex[:8]}"
        self.observations[target_id] = []
        logger.info(f"Nuevo objetivo creado: {target_id}")
        return target_id 