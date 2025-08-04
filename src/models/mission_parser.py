#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser de respuestas JSON para misiones de drones.
Maneja la extracción robusta de JSON desde respuestas LLM.
"""

import json
import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def extract_json_from_response(response_content: str) -> Dict:
    """
    Extrae y parsea JSON de una respuesta de LLM de manera robusta.
    
    Args:
        response_content: Contenido de la respuesta del LLM
        
    Returns:
        Dict: JSON parseado
        
    Raises:
        ValueError: Si no se puede extraer JSON válido
    """
    # Intentar parseo directo
    direct_parse = _try_direct_json_parse(response_content)
    if direct_parse:
        return direct_parse
    
    # Intentar parseo desde markdown
    markdown_parse = _try_markdown_json_parse(response_content)
    if markdown_parse:
        return markdown_parse
    
    # Intentar parseo con regex
    regex_parse = _try_regex_json_parse(response_content)
    if regex_parse:
        return regex_parse
    
    # Intentar parseo por índices
    index_parse = _try_index_json_parse(response_content)
    if index_parse:
        return index_parse
    
    # Si todo falla, generar error
    _log_parsing_failure(response_content)
    raise ValueError("No se pudo extraer JSON válido de la respuesta del LLM")


def _try_direct_json_parse(content: str) -> Optional[Dict]:
    """Intenta parsear JSON directamente."""
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        return None


def _try_markdown_json_parse(content: str) -> Optional[Dict]:
    """Intenta extraer JSON desde bloques de código markdown."""
    try:
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content, 
                              re.IGNORECASE)
        if json_match:
            json_content = json_match.group(1).strip()
            logger.info("JSON encontrado en bloque de código markdown")
            return json.loads(json_content)
    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON desde markdown: {e}")
    return None


def _try_regex_json_parse(content: str) -> Optional[Dict]:
    """Intenta extraer JSON usando regex de llaves."""
    try:
        json_match = re.search(r'({[\s\S]*})', content)
        if json_match:
            json_content = json_match.group(1).strip()
            logger.info("JSON encontrado usando regex de llaves")
            return json.loads(json_content)
    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON desde regex: {e}")
    return None


def _try_index_json_parse(content: str) -> Optional[Dict]:
    """Intenta extraer JSON usando índices de llaves."""
    try:
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_content = content[start_idx:end_idx+1]
            logger.info("JSON encontrado usando índices de llaves")
            return json.loads(json_content)
    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON desde índices: {e}")
    return None


def _log_parsing_failure(content: str) -> None:
    """Registra el fallo de parsing para debug."""
    logger.error("No se pudo extraer JSON válido de la respuesta. "
                "Contenido completo:")
    logger.error(f"'{content}'") 