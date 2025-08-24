#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de configuración para la aplicación.
Gestiona la configuración de logging y otras utilidades.
"""

import os
import logging
from datetime import datetime
from .helpers import get_logs_directory

def setup_logging():
    """Configura el sistema de logging para la aplicación."""
    # Usar la función de utilidad para obtener el directorio de logs
    logs_dir = get_logs_directory()
    
    # Nombre del archivo de log con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"geo_analysis_{timestamp}.log")
    
    # Configuración básica de logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Reducir verbosidad de bibliotecas externas
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

def get_openai_config():
    """Obtiene la configuración para la API de OpenAI."""
    return {
        "api_key": os.environ.get("OPENAI_API_KEY"),
        "model": "gpt-4.1", # Usar el modelo más reciente disponible
        "temperature": 0.3,            # Baja temperatura para respuestas precisas
        "max_tokens": 2000,            # Límite de tokens para la respuesta
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }

def get_docker_model_config():
    """Obtiene la configuración para Docker Model Runner."""
    return {
        "base_url": os.environ.get("DOCKER_MODEL_URL", "http://model-runner.docker.internal/engines/llama.cpp/v1/"),
        "api_key": os.environ.get("DOCKER_MODEL_API_KEY", "modelrunner"),  # Docker Model Runner usa esta key por defecto
        "model": os.environ.get("DOCKER_MODEL_NAME", "ai/llama3.2:latest"),
        "temperature": 0.3,
        "max_tokens": 2000,
        "timeout": 120,  # Modelos locales pueden tomar más tiempo
    }

def get_llm_config():
    """
    Obtiene la configuración del LLM según la variable de entorno LLM_PROVIDER.
    Por defecto usa Docker Models si está disponible, sino OpenAI.
    """
    provider = os.environ.get("LLM_PROVIDER", "docker").lower()
    
    if provider == "docker":
        return {
            "provider": "docker",
            "config": get_docker_model_config()
        }
    elif provider == "openai":
        return {
            "provider": "openai", 
            "config": get_openai_config()
        }
    else:
        # Por defecto intentar Docker Models
        return {
            "provider": "docker",
            "config": get_docker_model_config()
        } 