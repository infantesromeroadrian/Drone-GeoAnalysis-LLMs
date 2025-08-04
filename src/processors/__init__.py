"""
Módulo para procesamiento de imágenes y video en tiempo real.

Este módulo proporciona funcionalidades de:
- Detección de cambios entre imágenes de la misma zona geográfica
- Procesamiento de video en tiempo real desde drones
- Análisis visual continuo con threading optimizado
"""

from .change_detector import ChangeDetector
from .video_processor import VideoProcessor

__all__ = ['ChangeDetector', 'VideoProcessor']

# Versión del módulo
__version__ = '1.0.0'

# Metadatos del módulo
__author__ = 'Drone Geo Analysis Team'
__description__ = 'Módulo de procesamiento de imágenes y video en tiempo real' 