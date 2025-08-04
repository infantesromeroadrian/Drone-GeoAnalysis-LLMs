#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Correlaciona imágenes del dron con referencias satelitales.
"""

import logging
import requests
import json
import os
import time
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class GeoCorrelator:
    """Correlaciona imágenes del dron con referencias satelitales."""
    
    def __init__(self, api_key: Optional[str] = None, satellite_api_url: Optional[str] = None):
        """
        Inicializa el correlador geográfico.
        
        Args:
            api_key: Clave API para servicios satelitales
            satellite_api_url: URL de la API de imágenes satelitales
        """
        self.api_key = api_key or os.environ.get("SATELLITE_API_KEY", "")
        self.satellite_api_url = satellite_api_url or "https://api.satellite-imagery.com/v1"
        self.cache_dir = self._setup_cache_directory()
        
        logger.info("Correlador geográfico inicializado")
    
    def _setup_cache_directory(self) -> str:
        """Configura y crea el directorio de caché."""
        # Usar directorio raíz del proyecto de forma más robusta
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        cache_dir = os.path.join(project_root, "cache", "satellite")
        
        # Crear directorio si no existe
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        return cache_dir
    
    def get_satellite_image(self, latitude: float, longitude: float, 
                          zoom_level: int = 17) -> Optional[bytes]:
        """
        Obtiene una imagen satelital para coordenadas específicas.
        
        Args:
            latitude: Latitud
            longitude: Longitud
            zoom_level: Nivel de zoom (1-22)
            
        Returns:
            Datos de la imagen satelital en bytes o None
        """
        try:
            cache_file = self._get_cache_filename(latitude, longitude, zoom_level)
            
            # Comprobar caché primero
            cached_image = self._load_from_cache(cache_file)
            if cached_image:
                return cached_image
            
            # Simular obtención de imagen satelital
            logger.info(f"Simulando obtención de imagen satelital para: {latitude}, {longitude}")
            return None  # Prototipo - implementación real pendiente
            
        except Exception as e:
            logger.error(f"Error al obtener imagen satelital: {str(e)}")
            return None
    
    def _get_cache_filename(self, latitude: float, longitude: float, zoom_level: int) -> str:
        """Genera nombre de archivo para caché."""
        return os.path.join(
            self.cache_dir, 
            f"sat_{latitude:.5f}_{longitude:.5f}_{zoom_level}.jpg"
        )
    
    def _load_from_cache(self, cache_file: str) -> Optional[bytes]:
        """Carga imagen desde caché si existe."""
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return f.read()
        return None
    
    def correlate_drone_image(self, drone_image: bytes, drone_telemetry: Dict[str, Any], 
                            confidence_threshold: float = 0.6) -> Dict[str, Any]:
        """
        Correlaciona una imagen de dron con imágenes satelitales.
        
        Args:
            drone_image: Imagen del dron en bytes
            drone_telemetry: Datos telemétricos del dron
            confidence_threshold: Umbral de confianza para correlación
            
        Returns:
            Resultados de la correlación
        """
        try:
            # Validar datos GPS
            gps_data = self._extract_gps_data(drone_telemetry)
            if "error" in gps_data:
                return gps_data
            
            # Obtener imagen satelital de referencia
            satellite_image = self.get_satellite_image(
                gps_data["latitude"], gps_data["longitude"]
            )
            
            # Realizar correlación
            correlation_result = self._perform_correlation(
                drone_image, satellite_image, gps_data, drone_telemetry
            )
            
            # Evaluar confianza y agregar metadata
            return self._finalize_correlation_result(
                correlation_result, confidence_threshold
            )
            
        except Exception as e:
            logger.error(f"Error en correlación de imagen: {str(e)}")
            return {"error": str(e)}
    
    def _extract_gps_data(self, drone_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae y valida datos GPS de la telemetría."""
        gps = drone_telemetry.get("gps", {})
        latitude = gps.get("latitude")
        longitude = gps.get("longitude")
        
        if not latitude or not longitude:
            return {"error": "Datos GPS no disponibles en telemetría"}
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "altitude": drone_telemetry.get("altitude", 0)
        }
    
    def _perform_correlation(self, drone_image: bytes, satellite_image: Optional[bytes], 
                           gps_data: Dict[str, float], drone_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Realiza la correlación entre imágenes."""
        if not satellite_image:
            logger.warning("No se pudo obtener imagen satelital de referencia")
        
        # Calcular área de cobertura
        coverage_radius = gps_data["altitude"] * 0.5  # Simplificado
        
        # Simular correlación (implementación real pendiente)
        correlation_confidence = 0.85
        
        # Generar coordenadas corregidas
        corrected_coordinates = {
            "latitude": gps_data["latitude"] + 0.0001,
            "longitude": gps_data["longitude"] - 0.0002
        }
        
        return {
            "original_coordinates": {
                "latitude": gps_data["latitude"],
                "longitude": gps_data["longitude"]
            },
            "corrected_coordinates": corrected_coordinates,
            "confidence": correlation_confidence,
            "coverage_radius_meters": coverage_radius,
            "timestamp": time.time()
        }
    
    def _finalize_correlation_result(self, result: Dict[str, Any], 
                                   confidence_threshold: float) -> Dict[str, Any]:
        """Finaliza el resultado con metadata de confianza."""
        confidence = result["confidence"]
        
        if confidence >= confidence_threshold:
            result["status"] = "high_confidence"
            result["message"] = "Correlación exitosa"
        else:
            result["status"] = "low_confidence"
            result["message"] = "Correlación débil, usar con precaución"
        
        logger.info(f"Correlación completada con confianza: {confidence:.2f}")
        return result
    
    def calculate_real_coordinates(self, pixel_coords: Tuple[int, int], 
                                 drone_telemetry: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcula coordenadas reales a partir de coordenadas de píxel en la imagen.
        
        Args:
            pixel_coords: Coordenadas de píxel (x, y)
            drone_telemetry: Datos telemétricos del dron
            
        Returns:
            Coordenadas reales {latitude, longitude}
        """
        # Extraer datos de telemetría
        telemetry_data = self._extract_telemetry_data(drone_telemetry)
        
        # Calcular transformación de coordenadas
        return self._transform_pixel_to_coordinates(pixel_coords, telemetry_data)
    
    def _extract_telemetry_data(self, drone_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae datos relevantes de la telemetría."""
        gps = drone_telemetry.get("gps", {})
        orientation = drone_telemetry.get("orientation", {"yaw": 0, "pitch": 0, "roll": 0})
        
        return {
            "latitude": gps.get("latitude", 0),
            "longitude": gps.get("longitude", 0),
            "altitude": drone_telemetry.get("altitude", 100),
            "yaw": orientation.get("yaw", 0),
            "pitch": orientation.get("pitch", 0),
            "roll": orientation.get("roll", 0)
        }
    
    def _transform_pixel_to_coordinates(self, pixel_coords: Tuple[int, int], 
                                      telemetry_data: Dict[str, Any]) -> Dict[str, float]:
        """Transforma coordenadas de píxel a coordenadas GPS."""
        x, y = pixel_coords
        
        # Calcular factor de escala basado en altitud
        scale_factor = telemetry_data["altitude"] / 1000  # Simplificado
        
        # Aplicar rotación por orientación del dron
        rotated_coords = self._apply_rotation(x, y, telemetry_data["yaw"])
        
        # Convertir a offset de coordenadas
        lat_offset, lng_offset = self._calculate_coordinate_offsets(
            rotated_coords, scale_factor
        )
        
        # Calcular coordenadas finales
        target_latitude = telemetry_data["latitude"] - lat_offset
        target_longitude = telemetry_data["longitude"] + lng_offset
        
        return {
            "latitude": target_latitude,
            "longitude": target_longitude,
            "altitude": telemetry_data["altitude"],
            "accuracy_meters": scale_factor * 10
        }
    
    def _apply_rotation(self, x: float, y: float, yaw_degrees: float) -> Tuple[float, float]:
        """Aplica rotación por orientación del dron."""
        yaw_rad = np.radians(yaw_degrees)
        
        x_rotated = x * np.cos(yaw_rad) - y * np.sin(yaw_rad)
        y_rotated = x * np.sin(yaw_rad) + y * np.cos(yaw_rad)
        
        return x_rotated, y_rotated
    
    def _calculate_coordinate_offsets(self, rotated_coords: Tuple[float, float], 
                                    scale_factor: float) -> Tuple[float, float]:
        """Calcula offsets de coordenadas GPS."""
        x_rotated, y_rotated = rotated_coords
        
        # Factores simplificados para simulación
        lat_offset = y_rotated * scale_factor * 0.00001
        lng_offset = x_rotated * scale_factor * 0.00001
        
        return lat_offset, lng_offset 