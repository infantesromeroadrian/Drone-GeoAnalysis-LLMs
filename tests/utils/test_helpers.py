#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas para el módulo helpers.py
"""

import os
import json
import base64
import tempfile
import pytest
from unittest.mock import patch, mock_open
from PIL import Image

# Importar las funciones a probar
from src.utils.helpers import (
    encode_image_to_base64,
    get_image_metadata,
    format_geo_results,
    save_analysis_results,
    save_analysis_results_with_filename,
    get_project_root,
    get_results_directory,
    get_logs_directory,
    get_missions_directory
)

# Fixture para crear un archivo de imagen temporal para pruebas
@pytest.fixture
def temp_image_file():
    """Crea un archivo de imagen temporal para las pruebas."""
    # Crear una imagen simple para los tests
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        # Crear imagen de prueba de 100x100 pixeles
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name)
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Limpiar después de las pruebas
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)

# Tests para encode_image_to_base64
def test_encode_image_to_base64_success(temp_image_file):
    """Prueba la codificación exitosa de una imagen a base64."""
    result = encode_image_to_base64(temp_image_file)
    assert result is not None
    assert isinstance(result, tuple)
    assert len(result) == 2
    
    encoded, image_format = result
    assert isinstance(encoded, str)
    assert isinstance(image_format, str)
    assert image_format in ['jpeg', 'png', 'gif', 'webp']
    
    # Verificar que es una cadena base64 válida
    try:
        base64.b64decode(encoded)
        valid = True
    except Exception:
        valid = False
    assert valid

def test_encode_image_to_base64_error():
    """Prueba el manejo de errores al codificar una imagen inexistente."""
    result = encode_image_to_base64("ruta/inexistente.jpg")
    assert result is None

# Tests para get_image_metadata
def test_get_image_metadata_success(temp_image_file):
    """Prueba la obtención de metadatos de una imagen existente."""
    metadata = get_image_metadata(temp_image_file)
    assert metadata["filename"] == os.path.basename(temp_image_file)
    assert metadata["path"] == temp_image_file
    assert metadata["size"] > 0
    assert metadata["dimensions"] == (100, 100)
    assert metadata["format"] == "JPEG"

def test_get_image_metadata_error():
    """Prueba el manejo de errores al obtener metadatos de una imagen inexistente."""
    metadata = get_image_metadata("ruta/inexistente.jpg")
    assert metadata["size"] == 0
    assert metadata["dimensions"] == (0, 0)
    assert metadata["format"] == "unknown"

# Tests para format_geo_results
def test_format_geo_results_complete():
    """Prueba el formateo de resultados completos."""
    mock_results = {
        "country": "España",
        "city": "Madrid",
        "district": "Centro",
        "neighborhood": "Sol",
        "street": "Gran Vía",
        "confidence": 0.85,
        "supporting_evidence": ["landmark1", "landmark2"],
        "possible_alternatives": ["Barcelona", "Valencia"]
    }
    
    formatted = format_geo_results(mock_results)
    assert formatted["location"]["country"] == "España"
    assert formatted["location"]["city"] == "Madrid"
    assert formatted["confidence"] == 0.85
    assert "landmark1" in formatted["supporting_evidence"]
    assert "Barcelona" in formatted["possible_alternatives"]

def test_format_geo_results_partial():
    """Prueba el formateo de resultados parciales."""
    mock_results = {
        "country": "España",
        "confidence": 0.45,
    }
    
    formatted = format_geo_results(mock_results)
    assert formatted["location"]["country"] == "España"
    assert formatted["location"]["city"] == "No determinado"
    assert formatted["confidence"] == 0.45
    assert formatted["supporting_evidence"] == []

# Tests para save_analysis_results
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
def test_save_analysis_results_success(mock_file, mock_makedirs, mock_exists):
    """Prueba el guardado exitoso de resultados."""
    mock_exists.return_value = False
    
    results = {"test": "data"}
    image_path = "/tmp/test_image.jpg"
    
    output_path = save_analysis_results(results, image_path)
    
    # Verificar que se creó el directorio de resultados
    mock_makedirs.assert_called_once()
    
    # Verificar que se escribió el archivo
    mock_file.assert_called_once()
    
    # Verificar que la ruta de salida contiene el nombre base
    assert "test_image" in output_path

@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", side_effect=PermissionError("Permission denied"))
def test_save_analysis_results_error(mock_file, mock_makedirs, mock_exists):
    """Prueba el manejo de errores al guardar resultados."""
    mock_exists.return_value = True
    
    results = {"test": "data"}
    image_path = "/tmp/test_image.jpg"
    
    output_path = save_analysis_results(results, image_path)
    
    # Verificar que no se creó el directorio
    mock_makedirs.assert_not_called()
    
    # Verificar que se intentó escribir el archivo
    mock_file.assert_called_once()
    
    # Verificar que la ruta de salida es vacía debido al error
    assert output_path == ""

# Tests para save_analysis_results_with_filename
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
def test_save_analysis_results_with_filename_success(mock_file, mock_makedirs, mock_exists):
    """Prueba el guardado exitoso de resultados con nombre específico."""
    mock_exists.return_value = False
    
    results = {"test": "data"}
    filename = "test_analysis.json"
    
    output_path = save_analysis_results_with_filename(results, filename)
    
    # Verificar que se creó el directorio de resultados
    mock_makedirs.assert_called_once()
    
    # Verificar que se escribió el archivo
    mock_file.assert_called_once()
    
    # Verificar que la ruta de salida contiene el nombre especificado
    assert filename in output_path

# Tests para funciones de utilidad de rutas
def test_get_project_root():
    """Prueba que get_project_root devuelve una ruta válida."""
    root = get_project_root()
    assert isinstance(root, str)
    assert os.path.isabs(root)  # Debe ser una ruta absoluta

@patch("os.makedirs")
@patch("os.path.exists")
def test_get_results_directory(mock_exists, mock_makedirs):
    """Prueba que get_results_directory crea el directorio si no existe."""
    mock_exists.return_value = False
    
    results_dir = get_results_directory()
    
    # Verificar que se llamó makedirs
    mock_makedirs.assert_called_once()
    assert isinstance(results_dir, str)
    assert "results" in results_dir

@patch("os.makedirs")
@patch("os.path.exists")
def test_get_logs_directory(mock_exists, mock_makedirs):
    """Prueba que get_logs_directory crea el directorio si no existe."""
    mock_exists.return_value = False
    
    logs_dir = get_logs_directory()
    
    # Verificar que se llamó makedirs
    mock_makedirs.assert_called_once()
    assert isinstance(logs_dir, str)
    assert "logs" in logs_dir

@patch("os.makedirs")
@patch("os.path.exists")
def test_get_missions_directory(mock_exists, mock_makedirs):
    """Prueba que get_missions_directory crea el directorio si no existe."""
    mock_exists.return_value = False
    
    missions_dir = get_missions_directory()
    
    # Verificar que se llamó makedirs
    mock_makedirs.assert_called_once()
    assert isinstance(missions_dir, str)
    assert "missions" in missions_dir 