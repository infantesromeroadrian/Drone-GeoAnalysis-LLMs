"""
Módulo para geolocalización avanzada y análisis espacial.

Este módulo proporciona funcionalidades de:
- Triangulación geográfica basada en múltiples observaciones desde drones
- Correlación de imágenes con referencias satelitales
- Conversión de coordenadas píxel a coordenadas reales
"""

from .geo_triangulation import GeoTriangulation
from .geo_correlator import GeoCorrelator

__all__ = ['GeoTriangulation', 'GeoCorrelator']

# Versión del módulo
__version__ = '1.0.0'

# Metadatos del módulo
__author__ = 'Drone Geo Analysis Team'
__description__ = 'Módulo de geolocalización avanzada para análisis de drones' 