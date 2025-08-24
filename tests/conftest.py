#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración global para las pruebas de pytest.
Define fixtures comunes para todos los tests.
"""

import os
import sys
import pytest
import tempfile
from PIL import Image

# Agregar la ruta raíz del proyecto al PYTHONPATH
# Esto permite importar módulos de forma absoluta en los tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def project_root():
    """Devuelve la ruta raíz del proyecto."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def sample_image():
    """Crea una imagen de muestra para usar en las pruebas."""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        # Crear imagen de prueba de 100x100 pixeles
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name)
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Limpiar después de las pruebas
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)

@pytest.fixture
def sample_geo_data():
    """Proporciona datos de muestra para análisis geográfico."""
    return {
        "country": "España",
        "city": "Madrid",
        "district": "Centro",
        "confidence": 0.85,
        "supporting_evidence": ["landmark1", "landmark2"],
        "possible_alternatives": ["Barcelona", "Valencia"]
    } 