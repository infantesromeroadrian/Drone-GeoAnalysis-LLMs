#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clase base abstracta para todos los controladores de drones.
"""

from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

class BaseDrone(ABC):
    """
    Abstract Factory pattern for drone controllers.
    
    This class implements the Abstract Factory design pattern to provide
    a uniform interface for controlling different drone manufacturers' hardware.
    
    Pattern Components:
    - BaseDrone: Abstract Factory interface defining common operations
    - Concrete Implementations: ParrotAnafiController, DJIDroneController, etc.
    - Products: Consistent drone control operations across hardware
    
    Design Rationale:
    - Enables easy integration of new drone manufacturers
    - Provides consistent API regardless of underlying hardware
    - Facilitates testing with mock implementations
    - Supports hot-swapping of drone types in missions
    
    Usage:
        drone = ParrotAnafiController()  # Concrete factory
        drone.connect()
        drone.take_off(50)
        drone.capture_image()
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """Establece conexión con el dron."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Desconecta del dron."""
        pass
    
    @abstractmethod
    def take_off(self, altitude: float) -> bool:
        """Despega el dron hasta la altitud especificada."""
        pass
    
    @abstractmethod
    def land(self) -> bool:
        """Aterriza el dron."""
        pass
    
    @abstractmethod
    def move_to(self, latitude: float, longitude: float, altitude: float) -> bool:
        """Mueve el dron a las coordenadas especificadas."""
        pass
    
    @abstractmethod
    def capture_image(self) -> str:
        """Captura una imagen y devuelve la ruta al archivo."""
        pass
    
    @abstractmethod
    def start_video_stream(self) -> str:
        """Inicia la transmisión de video y devuelve el URL del stream."""
        pass
    
    @abstractmethod
    def stop_video_stream(self) -> bool:
        """Detiene la transmisión de video."""
        pass
    
    @abstractmethod
    def get_telemetry(self) -> Dict[str, Any]:
        """Obtiene datos telemétricos del dron."""
        pass
    
    @abstractmethod
    def execute_mission(self, mission_data: Dict[str, Any]) -> bool:
        """Ejecuta una misión pre-programada."""
        pass 