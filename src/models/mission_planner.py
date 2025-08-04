#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Planificador principal de misiones con IA.
Clase principal que orquesta la generación de misiones usando LLM.
Refactorizado para cumplir con principios de Single Responsibility.
"""

import logging
from typing import List, Dict, Optional, Tuple

from .llm_client import LLMClient
from .cartography_manager import CartographyManager
from .mission_data_processor import MissionDataProcessor
from .prompt_generator import PromptGenerator
from .mission_validator import validate_mission_safety

# Configurar logger
logger = logging.getLogger(__name__)


class LLMMissionPlanner:
    """
    Planificador de misiones inteligente usando LLM.
    Responsabilidad única: Orquestar la generación de misiones.
    """
    
    def __init__(self):
        """Inicializa el planificador con sus componentes."""
        self.llm_client = LLMClient()
        self.cartography_manager = CartographyManager()
        self.mission_processor = MissionDataProcessor()
        self.prompt_generator = PromptGenerator()
        self.current_mission = None
        
        logger.info("LLMMissionPlanner inicializado")
    
    def create_mission_from_command(self, natural_command: str, 
                                  area_name: Optional[str] = None) -> Optional[Dict]:
        """
        Crea una misión a partir de un comando en lenguaje natural.
        
        Args:
            natural_command: Comando en lenguaje natural
            area_name: Nombre del área cargada (opcional)
            
        Returns:
            Dict: Misión generada o None si falla
        """
        try:
            # Preparar información del área
            area_info, center_coords = self._prepare_area_info(area_name)
            
            # Crear prompts
            system_prompt = self.prompt_generator.build_system_prompt()
            user_prompt = self.prompt_generator.build_user_prompt(
                natural_command, area_info
            )
            
            # Obtener respuesta del LLM
            response_content = self.llm_client.create_chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.3)
            
            # Procesar y enriquecer la misión
            provider_info = self.llm_client.get_provider_info()
            mission_data = self.mission_processor.process_mission_response(
                response_content, natural_command, area_name, center_coords,
                provider_info["provider"], provider_info["model"]
            )
            
            # Guardar misión
            self.mission_processor.save_mission(mission_data)
            
            self.current_mission = mission_data
            logger.info(f"Misión creada: {mission_data['mission_name']}")
            return mission_data
            
        except Exception as e:
            logger.error(f"Error creando misión: {e}")
            return None
    

    
    def load_cartography(self, file_path: str, area_name: str) -> bool:
        """
        Carga cartografía desde archivo.
        
        Args:
            file_path: Ruta al archivo de cartografía
            area_name: Nombre del área
            
        Returns:
            bool: True si se cargó correctamente
        """
        return self.cartography_manager.load_cartography(file_path, area_name)
    

    
    def get_area_center_coordinates(self, area_name: str) -> Optional[Tuple[float, float]]:
        """Obtiene las coordenadas del centro de un área cargada."""
        area = self.cartography_manager.get_loaded_area(area_name)
        if not area:
            return None
            
        return self.mission_processor.get_area_center_coordinates(area)
    
    def _prepare_area_info(self, area_name: Optional[str]) -> Tuple[str, Optional[Tuple[float, float]]]:
        """Prepara la información del área para la generación de misión."""
        area_info = ""
        center_coordinates = None
        
        if area_name and self.cartography_manager.is_area_loaded(area_name):
            area = self.cartography_manager.get_loaded_area(area_name)
            center_coordinates = self.get_area_center_coordinates(area_name)
            
            if center_coordinates:
                area_info = self.mission_processor.prepare_area_info(
                    area, center_coordinates
                )
        
        return area_info, center_coordinates
    

    
    def get_available_missions(self) -> List[Dict]:
        """Obtiene lista de misiones disponibles."""
        return self.mission_processor.get_available_missions()
    

    
    def validate_mission(self, mission: Dict) -> List[str]:
        """
        Valida la seguridad de una misión.
        Delegada al módulo de validación.
        """
        return validate_mission_safety(mission) 