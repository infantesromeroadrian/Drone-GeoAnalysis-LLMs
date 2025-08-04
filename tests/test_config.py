#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas para el módulo config.py
"""

import os
import logging
import pytest
from unittest.mock import patch, MagicMock

from src.utils.config import setup_logging, get_openai_config

def test_setup_logging_creates_directory(tmpdir):
    """Prueba que la función setup_logging crea el directorio de logs si no existe."""
    # Configurar un directorio temporal para las pruebas
    logs_dir = os.path.join(tmpdir, "logs")
    
    # Parchar para usar el directorio temporal
    with patch('os.path.dirname', return_value=str(tmpdir)):
        # Llamar a la función de configuración de logging
        logger = setup_logging()
        
        # Verificar que se creó el directorio de logs
        assert os.path.exists(logs_dir)
        
        # Verificar que devuelve un logger válido
        assert isinstance(logger, logging.Logger)

def test_setup_logging_handlers():
    """Prueba que la función setup_logging configura los handlers correctamente."""
    # Llamar a la función de configuración de logging
    with patch('logging.FileHandler'):
        with patch('logging.StreamHandler'):
            logger = setup_logging()
            
            # Verificar que el nivel de logging del logger específico
            # Nota: el nivel puede ser NOTSET (0) para loggers específicos
            # ya que heredan la configuración del root logger
            assert isinstance(logger, logging.Logger)
            
            # Verificar que el root logger tiene handlers configurados
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0
            
            # Verificar que el root logger tiene el nivel correcto
            assert root_logger.level == logging.INFO

def test_get_openai_config():
    """Prueba que la función get_openai_config devuelve la configuración correcta."""
    # Configurar variable de entorno para la prueba
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        config = get_openai_config()
        
        # Verificar los valores de configuración
        assert config["api_key"] == "test_key"
        assert config["model"] == "gpt-4.1"
        assert config["temperature"] == 0.3
        assert config["max_tokens"] == 2000
        assert "top_p" in config
        assert "frequency_penalty" in config
        assert "presence_penalty" in config 