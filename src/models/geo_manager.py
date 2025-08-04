#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de geolocalización para el sistema.
Responsabilidad única: Gestionar estado de geolocalización, referencias e imágenes.
"""

import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GeolocationManager:
    """
    Gestor de geolocalización para manejar referencias e imágenes.
    Responsabilidad única: Gestionar estado de geolocalización.
    """
    
    def __init__(self):
        """Inicializa el gestor de geolocalización."""
        self.current_reference_image = None
        self.reference_images = {}
        self.targets = {}
        logger.info("Gestor de geolocalización inicializado")
    
    def add_reference_image(self, drone_telemetry: Dict[str, Any]) -> str:
        """
        Añade una imagen de referencia.
        
        Args:
            drone_telemetry: Datos de telemetría del dron
            
        Returns:
            ID de la referencia creada
        """
        ref_id = f"ref_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.reference_images[ref_id] = {
            'timestamp': datetime.now().isoformat(),
            'location': drone_telemetry.get('gps', {})
        }
        self.current_reference_image = ref_id
        logger.info(f"Imagen de referencia añadida: {ref_id}")
        return ref_id
    
    def create_target(self) -> str:
        """
        Crea un nuevo objetivo para triangulación.
        
        Returns:
            ID del objetivo creado
        """
        target_id = f"target_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.targets[target_id] = {
            'captures': [],
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Objetivo creado: {target_id}")
        return target_id
    
    def get_reference_images(self) -> Dict[str, Any]:
        """Obtiene todas las imágenes de referencia."""
        return self.reference_images
    
    def get_targets(self) -> Dict[str, Any]:
        """Obtiene todos los objetivos."""
        return self.targets 