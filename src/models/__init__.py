"""
Módulo para modelos de IA y análisis avanzado.
Refactorizado siguiendo principios de Single Responsibility.

Este módulo proporciona funcionalidades de:
- Análisis geográfico de imágenes usando GPT-4 Vision
- Detección de objetos usando YOLO 11
- Planificación inteligente de misiones con LLM
- Procesamiento de comandos en lenguaje natural
- Modelos de datos para misiones
- Validación de seguridad de misiones
- Utilidades geográficas y matemáticas
- Gestión de geolocalización y referencias
"""

from .geo_analyzer import GeoAnalyzer
from .yolo_detector import YoloObjectDetector
from .mission_planner import LLMMissionPlanner
from .mission_models import Waypoint, MissionArea, MissionMetadata
from .mission_parser import extract_json_from_response
from .mission_validator import validate_mission_safety
from .mission_utils import calculate_distance, calculate_area_center
from .geo_manager import GeolocationManager

__all__ = [
    'GeoAnalyzer',
    'YoloObjectDetector',
    'LLMMissionPlanner',
    'Waypoint', 
    'MissionArea', 
    'MissionMetadata',
    'extract_json_from_response',
    'validate_mission_safety',
    'calculate_distance',
    'calculate_area_center',
    'GeolocationManager'
]

# Versión del módulo
__version__ = '1.0.0'

# Metadatos del módulo
__author__ = 'Drone Geo Analysis Team'
__description__ = 'Módulo de modelos de IA para análisis y planificación' 