#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de cartografía para cargar y procesar datos geográficos.
Responsabilidad única: Manejar la carga y procesamiento de cartografía.
"""

import json
import os
import logging
from typing import Dict, List, Tuple, Optional

from src.utils.helpers import get_project_root
from .mission_models import MissionArea

logger = logging.getLogger(__name__)


class CartographyManager:
    """
    Gestor para cargar y procesar datos de cartografía.
    Soporta múltiples formatos: GeoJSON, KML.
    """
    
    def __init__(self):
        """Inicializa el gestor de cartografía."""
        self.cartography_dir = os.path.join(get_project_root(), 
                                          "cartography")
        self.loaded_areas = {}
        self._setup_directories()
        
        logger.info("CartographyManager inicializado")
    
    def _setup_directories(self) -> None:
        """Configura los directorios necesarios."""
        os.makedirs(self.cartography_dir, exist_ok=True)
    
    def load_cartography(self, file_path: str, area_name: str) -> bool:
        """
        Carga cartografía desde archivo.
        
        Args:
            file_path: Ruta al archivo de cartografía
            area_name: Nombre del área
            
        Returns:
            bool: True si se cargó correctamente
        """
        try:
            if file_path.endswith(('.geojson', '.json')):
                return self._load_geojson_cartography(file_path, area_name)
            elif file_path.endswith('.kml'):
                logger.warning("Soporte KML no implementado")
                return False
                
        except Exception as e:
            logger.error(f"Error cargando cartografía: {e}")
            return False
        
        return False
    
    def _load_geojson_cartography(self, file_path: str, 
                                 area_name: str) -> bool:
        """Carga cartografía desde archivo GeoJSON."""
        try:
            logger.info(f"Cargando GeoJSON desde: {file_path}")
            
            if not self._validate_file_exists(file_path):
                return False
            
            geo_data = self._read_json_file(file_path)
            if not geo_data:
                return False
            
            if not self._validate_geojson_structure(geo_data):
                return False
            
            area = self._process_geojson(geo_data, area_name)
            self.loaded_areas[area_name] = area
            
            logger.info(f"Área '{area_name}' cargada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error procesando GeoJSON: {e}", exc_info=True)
            return False
    
    def _validate_file_exists(self, file_path: str) -> bool:
        """Valida que el archivo existe."""
        if not os.path.exists(file_path):
            logger.error(f"Archivo no encontrado: {file_path}")
            return False
        return True
    
    def _read_json_file(self, file_path: str) -> Optional[Dict]:
        """Lee y parsea archivo JSON."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"Archivo leído, tamaño: {len(content)} caracteres")
                
                if not content.strip():
                    logger.error("Archivo GeoJSON está vacío")
                    return None
                
                return json.loads(content)
                
        except json.JSONDecodeError as json_error:
            logger.error(f"Error parseando JSON: {json_error}")
            return None
    
    def _validate_geojson_structure(self, geo_data: Dict) -> bool:
        """Valida estructura GeoJSON básica."""
        if not isinstance(geo_data, dict):
            logger.error("GeoJSON debe ser un objeto JSON")
            return False
        
        if 'type' not in geo_data:
            logger.error("GeoJSON debe tener un campo 'type'")
            return False
        
        if geo_data.get('type') != 'FeatureCollection':
            logger.warning(f"Tipo GeoJSON inesperado: {geo_data.get('type')}")
        
        return True
    
    def _process_geojson(self, geo_data: Dict, area_name: str) -> MissionArea:
        """Procesa datos GeoJSON y extrae información relevante."""
        boundaries = []
        points_of_interest = []
        
        features = geo_data.get('features', [])
        logger.info(f"Procesando {len(features)} features")
        
        for feature in features:
            self._process_feature(feature, boundaries, points_of_interest)
        
        return MissionArea(
            name=area_name,
            boundaries=boundaries,
            points_of_interest=points_of_interest
        )
    
    def _process_feature(self, feature: Dict, boundaries: List, 
                        points_of_interest: List) -> None:
        """Procesa una feature individual del GeoJSON."""
        geometry = feature.get('geometry', {})
        properties = feature.get('properties', {})
        
        if geometry.get('type') == 'Polygon':
            polygon_boundaries = self._extract_polygon_boundaries(geometry)
            boundaries.extend(polygon_boundaries)
        elif geometry.get('type') == 'Point':
            poi = self._extract_point_of_interest(geometry, properties)
            points_of_interest.append(poi)
    
    def _extract_polygon_boundaries(self, geometry: Dict) -> List[Tuple[float, float]]:
        """Extrae perímetro de un polígono."""
        coords = geometry.get('coordinates', [[]])[0]
        return [(lat, lng) for lng, lat in coords]
    
    def _extract_point_of_interest(self, geometry: Dict, 
                                 properties: Dict) -> Dict:
        """Extrae punto de interés."""
        coords = geometry.get('coordinates', [0, 0])
        return {
            'name': properties.get('name', 'POI'),
            'coordinates': (coords[1], coords[0]),  # lat, lng
            'type': properties.get('type', 'general')
        }
    
    def get_loaded_area(self, area_name: str) -> Optional[MissionArea]:
        """Obtiene un área cargada."""
        return self.loaded_areas.get(area_name)
    
    def get_loaded_areas(self) -> Dict[str, MissionArea]:
        """Obtiene todas las áreas cargadas."""
        return self.loaded_areas.copy()
    
    def is_area_loaded(self, area_name: str) -> bool:
        """Verifica si un área está cargada."""
        return area_name in self.loaded_areas 