#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelos de datos para el sistema de planificación de misiones.
Siguiendo principios de Single Responsibility y encapsulación.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple


@dataclass
class Waypoint:
    """
    Modelo para representar un waypoint de misión.
    Encapsula coordenadas GPS, altitud y acciones específicas.
    """
    latitude: float
    longitude: float
    altitude: float
    action: str = "navigate"  # navigate, hover, scan, land, etc.
    duration: float = 0.0  # tiempo en segundos
    description: str = ""


@dataclass
class MissionArea:
    """
    Modelo para representar un área de misión geográfica.
    Incluye límites, restricciones y puntos de interés.
    """
    name: str
    boundaries: List[Tuple[float, float]]  # Lista de (lat, lng)
    restrictions: List[str] = field(default_factory=list)
    points_of_interest: List[Dict] = field(default_factory=list)


@dataclass
class MissionMetadata:
    """
    Metadatos para una misión de dron.
    Información de tracking y configuración.
    """
    mission_id: str
    created_at: str
    status: str
    area_name: str
    original_command: str
    llm_provider: str
    llm_model: str 