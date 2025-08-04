#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Procesador de datos de misión.
Responsabilidad única: Procesar y enriquecer datos de misión.
"""

import json
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.utils.helpers import get_missions_directory
from .mission_models import MissionArea
from .mission_parser import extract_json_from_response
from .mission_utils import calculate_area_center

logger = logging.getLogger(__name__)


class MissionDataProcessor:
    """
    Procesador para enriquecer y gestionar datos de misión.
    """
    
    def __init__(self):
        """Inicializa el procesador de datos de misión."""
        self.missions_dir = get_missions_directory()
        logger.info("MissionDataProcessor inicializado")
    
    def process_mission_response(self, 
                               response_content: str,
                               natural_command: str,
                               area_name: Optional[str],
                               center_coordinates: Optional[Tuple[float, float]],
                               llm_provider: str,
                               llm_model: str) -> Dict:
        """
        Procesa la respuesta del LLM y enriquece la misión.
        
        Args:
            response_content: Respuesta del LLM
            natural_command: Comando original del usuario
            area_name: Nombre del área (opcional)
            center_coordinates: Coordenadas del centro (opcional)
            llm_provider: Proveedor LLM utilizado
            llm_model: Modelo LLM utilizado
            
        Returns:
            Dict: Datos de misión procesados y enriquecidos
        """
        # Parsear respuesta JSON
        mission_data = extract_json_from_response(response_content)
        
        # Añadir metadatos
        self._add_metadata(mission_data, natural_command, area_name,
                          llm_provider, llm_model)
        
        # Añadir coordenadas del centro si están disponibles
        if center_coordinates:
            self._add_center_coordinates(mission_data, center_coordinates)
        
        return mission_data
    
    def _add_metadata(self, 
                     mission_data: Dict,
                     natural_command: str,
                     area_name: Optional[str],
                     llm_provider: str,
                     llm_model: str) -> None:
        """Añade metadatos básicos a la misión."""
        mission_data['id'] = str(uuid.uuid4())
        mission_data['created_at'] = datetime.now().isoformat()
        mission_data['status'] = 'planned'
        mission_data['area_name'] = area_name
        mission_data['original_command'] = natural_command
        mission_data['llm_provider'] = llm_provider
        mission_data['llm_model'] = llm_model
    
    def _add_center_coordinates(self, 
                              mission_data: Dict,
                              center_coordinates: Tuple[float, float]) -> None:
        """Añade coordenadas del centro del área."""
        mission_data['area_center'] = {
            'latitude': center_coordinates[0],
            'longitude': center_coordinates[1]
        }
    
    def save_mission(self, mission_data: Dict) -> None:
        """
        Guarda la misión en archivo JSON.
        
        Args:
            mission_data: Datos de la misión a guardar
        """
        mission_file = os.path.join(
            self.missions_dir, 
            f"mission_{mission_data['id']}.json"
        )
        
        with open(mission_file, 'w', encoding='utf-8') as f:
            json.dump(mission_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Misión guardada: {mission_file}")
    
    def get_available_missions(self) -> List[Dict]:
        """
        Obtiene lista de misiones disponibles.
        
        Returns:
            List[Dict]: Lista de información básica de misiones
        """
        missions = []
        
        for filename in os.listdir(self.missions_dir):
            if filename.startswith('mission_') and filename.endswith('.json'):
                try:
                    mission_info = self._load_mission_info(filename)
                    if mission_info:
                        missions.append(mission_info)
                except Exception as e:
                    logger.error(f"Error cargando misión {filename}: {e}")
        
        return missions
    
    def _load_mission_info(self, filename: str) -> Optional[Dict]:
        """
        Carga información básica de una misión.
        
        Args:
            filename: Nombre del archivo de misión
            
        Returns:
            Dict: Información básica de la misión o None si falla
        """
        try:
            with open(os.path.join(self.missions_dir, filename), 
                     'r', encoding='utf-8') as f:
                mission = json.load(f)
                return {
                    'id': mission['id'],
                    'name': mission['mission_name'],
                    'description': mission['description'],
                    'status': mission.get('status', 'planned'),
                    'created_at': mission['created_at']
                }
        except Exception:
            return None
    
    def prepare_area_info(self, 
                         area: Optional[MissionArea],
                         center_coordinates: Optional[Tuple[float, float]]) -> str:
        """
        Prepara la información del área para la generación de misión.
        
        Args:
            area: Área cargada (opcional)
            center_coordinates: Coordenadas del centro (opcional)
            
        Returns:
            str: Información formateada del área
        """
        if not area or not center_coordinates:
            return ""
        
        return f"""
        ÁREA GEOGRÁFICA ESPECÍFICA: {area.name}
        
        COORDENADAS DEL CENTRO: 
        - Latitud: {center_coordinates[0]:.6f}
        - Longitud: {center_coordinates[1]:.6f}
        
        LÍMITES DEL ÁREA: {area.boundaries}
        
        PUNTOS DE INTERÉS: {area.points_of_interest}
        
        INSTRUCCIONES:
        - Usar coordenadas específicas del área
        - Generar waypoints dentro del área
        - Radio máximo: 2km desde el centro
        """
    
    def get_area_center_coordinates(self, area: MissionArea) -> Optional[Tuple[float, float]]:
        """
        Obtiene las coordenadas del centro de un área.
        
        Args:
            area: Área de la misión
            
        Returns:
            Tuple[float, float]: Coordenadas del centro (lat, lng) o None
        """
        return calculate_area_center(area) 