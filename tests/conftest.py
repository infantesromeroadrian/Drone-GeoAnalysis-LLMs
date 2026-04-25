#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración global para las pruebas de pytest.
Define fixtures comunes para todos los tests.
"""

import os
import sys
import time as _time_module
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


# ---------------------------------------------------------------------------
# Polling helpers — reusable across any test that exercises background threads.
# All use 50 ms ticks so they resolve within one interpolation cycle.
# ---------------------------------------------------------------------------

def wait_for_status(executor, expected_status: str, timeout: float = 30.0) -> bool:
    """Poll executor.get_status() until status reaches expected_status or timeout.

    Args:
        executor: MissionExecutor instance with get_status() method.
        expected_status: Target status string ("flying", "completed", "aborted", etc.).
        timeout: Maximum seconds to wait. Returns False on timeout.

    Returns:
        True if status reached expected_status, False on timeout.
    """
    deadline = _time_module.monotonic() + timeout
    while _time_module.monotonic() < deadline:
        if executor.get_status()["status"] == expected_status:
            return True
        _time_module.sleep(0.05)
    return False


def wait_for_waypoint(executor, waypoint_n: int, timeout: float = 30.0) -> bool:
    """Poll executor until current_waypoint reaches waypoint_n or timeout.

    Args:
        executor: MissionExecutor instance with get_status() method.
        waypoint_n: Waypoint index to wait for (0-based, inclusive).
        timeout: Maximum seconds to wait. Returns False on timeout.

    Returns:
        True if current_waypoint >= waypoint_n, False on timeout.
    """
    deadline = _time_module.monotonic() + timeout
    while _time_module.monotonic() < deadline:
        if executor.get_status()["current_waypoint"] >= waypoint_n:
            return True
        _time_module.sleep(0.05)
    return False


def wait_for_call_count(mock_method, expected_count: int, timeout: float = 30.0) -> bool:
    """Poll mock_method.call_count until it reaches expected_count or timeout.

    Args:
        mock_method: unittest.mock.MagicMock (or compatible) with a .call_count attribute.
        expected_count: Minimum call count to wait for.
        timeout: Maximum seconds to wait. Returns False on timeout.

    Returns:
        True if call_count >= expected_count, False on timeout.
    """
    deadline = _time_module.monotonic() + timeout
    while _time_module.monotonic() < deadline:
        if mock_method.call_count >= expected_count:
            return True
        _time_module.sleep(0.05)
    return False