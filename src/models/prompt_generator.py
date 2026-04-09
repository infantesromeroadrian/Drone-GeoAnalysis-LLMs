#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de prompts para LLM.
Responsabilidad única: Generar prompts para creación de misiones.
"""

import logging

logger = logging.getLogger(__name__)


class PromptGenerator:
    """
    Generador de prompts para comunicación con LLM.
    """
    
    def __init__(self):
        """Inicializa el generador de prompts."""
        logger.info("PromptGenerator inicializado")
    
    def build_system_prompt(self) -> str:
        """
        Construye el prompt de sistema para generación de misiones.
        
        Returns:
            str: Prompt de sistema estructurado
        """
        return """
        Eres un experto en planificación de misiones de drones militares.
        Convierte comandos naturales en misiones de vuelo estructuradas.
        
        REGLAS CRITICAS:
        1. Usar coordenadas especificas del area si se proporciona
        2. Cada waypoint DEBE tener coordenadas GPS UNICAS - NUNCA repitas las mismas lat/lng
        3. Distribuir waypoints geograficamente (min 50-100m entre cada uno)
        4. Crear rutas logicas con puntos progresivos
        5. Si hay N puntos de interes, genera exactamente N waypoints (uno por punto)
        6. Verifica que no haya dos waypoints con las mismas coordenadas antes de responder
        
        Responde ÚNICAMENTE con JSON válido:
        {
            "mission_name": "string",
            "description": "string", 
            "estimated_duration": number,
            "waypoints": [
                {
                    "latitude": number,
                    "longitude": number,
                    "altitude": number,
                    "action": "string",
                    "duration": number,
                    "description": "string"
                }
            ],
            "safety_considerations": ["string"],
            "success_criteria": ["string"],
            "area_used": "string"
        }
        
        Acciones: navigate, hover, scan, photograph, patrol, land, takeoff
        """
    
    def build_user_prompt(self, natural_command: str, area_info: str) -> str:
        """
        Construye el prompt del usuario para generación de misiones.
        
        Args:
            natural_command: Comando en lenguaje natural
            area_info: Información del área (si está disponible)
            
        Returns:
            str: Prompt del usuario estructurado
        """
        area_context = (area_info if area_info else 
                       "ÁREA: No especificada - usar coordenadas apropiadas")
        
        return f"""
        Comando: {natural_command}
        
        {area_context}
        
        Genera una misión detallada para este comando.
        """ 