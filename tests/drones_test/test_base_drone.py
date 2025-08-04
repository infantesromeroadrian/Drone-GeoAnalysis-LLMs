#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para base_drone.py
Prueba la clase abstracta BaseDrone y el patrón Abstract Factory.
"""

import sys
import os
import pytest
from abc import ABC

# Configuración de path para importar módulos desde src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.drones.base_drone import BaseDrone

class TestBaseDrone:
    """Clase de tests para BaseDrone"""
    
    def test_base_drone_is_abstract(self):
        """Prueba que BaseDrone es una clase abstracta"""
        assert issubclass(BaseDrone, ABC)
        with pytest.raises(TypeError):
            BaseDrone()
    
    def test_abstract_methods_defined(self):
        """Prueba que todos los métodos abstractos están definidos"""
        expected_methods = {
            "connect", "disconnect", "take_off", "land", "move_to",
            "capture_image", "start_video_stream", "stop_video_stream", 
            "get_telemetry", "execute_mission"
        }
        actual_methods = set(BaseDrone.__abstractmethods__)
        assert expected_methods == actual_methods
