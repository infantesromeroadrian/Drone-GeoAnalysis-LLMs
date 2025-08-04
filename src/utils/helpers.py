#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo con funciones auxiliares para la herramienta de análisis geográfico.
"""

import os
import base64
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

def get_project_root() -> str:
    """
    Obtiene la ruta raíz del proyecto de forma confiable.
    
    Returns:
        Ruta absoluta del directorio raíz del proyecto
    """
    # Obtener el directorio del archivo actual (helpers.py está en src/utils/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Subir dos niveles: utils -> src -> proyecto
    project_root = os.path.dirname(os.path.dirname(current_dir))
    return project_root

def get_results_directory() -> str:
    """
    Obtiene el directorio de resultados, creándolo si no existe.
    
    Returns:
        Ruta absoluta del directorio de resultados
    """
    results_dir = os.path.join(get_project_root(), "results")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    return results_dir

def get_logs_directory() -> str:
    """
    Obtiene el directorio de logs, creándolo si no existe.
    
    Returns:
        Ruta absoluta del directorio de logs
    """
    logs_dir = os.path.join(get_project_root(), "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    return logs_dir

def get_missions_directory() -> str:
    """
    Obtiene el directorio de misiones, creándolo si no existe.
    
    Returns:
        Ruta absoluta del directorio de misiones
    """
    missions_dir = os.path.join(get_project_root(), "missions")
    if not os.path.exists(missions_dir):
        os.makedirs(missions_dir)
    return missions_dir

def encode_image_to_base64(image_path: str) -> Optional[Tuple[str, str]]:
    """
    Convierte una imagen a formato base64 compatible con OpenAI API.
    Convierte automáticamente formatos no compatibles (AVIF, HEIC, etc.) a JPEG.
    
    Args:
        image_path: Ruta al archivo de imagen
        
    Returns:
        Tuple (base64_string, format) o None si hay error
        format puede ser: 'jpeg', 'png', 'gif', 'webp'
    """
    # Formatos compatibles con OpenAI Vision API
    OPENAI_COMPATIBLE_FORMATS = ['PNG', 'JPEG', 'GIF', 'WEBP']
    
    try:
        # Abrir imagen con PIL para detectar formato
        with Image.open(image_path) as img:
            original_format = img.format
            logger.info(f"Formato original de imagen: {original_format}")
            
            # Si el formato es compatible, usar directamente
            if original_format in OPENAI_COMPATIBLE_FORMATS:
                with open(image_path, "rb") as image_file:
                    base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                    return base64_data, original_format.lower()
            
            # Si no es compatible, convertir a JPEG
            else:
                logger.warning(f"Formato {original_format} no compatible con OpenAI. Convirtiendo a JPEG...")
                
                # Convertir RGBA a RGB si es necesario (para JPEG)
                if img.mode in ('RGBA', 'LA'):
                    # Crear fondo blanco
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])  # Usar canal alpha como máscara
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Guardar en memoria como JPEG
                import io
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=95)
                buffer.seek(0)
                
                # Codificar a base64
                base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                logger.info(f"Imagen convertida exitosamente de {original_format} a JPEG")
                return base64_data, 'jpeg'
                
    except Exception as e:
        logger.error(f"Error al codificar imagen {image_path}: {str(e)}")
        return None

def get_image_metadata(image_path: str) -> Dict[str, Any]:
    """
    Obtiene metadatos básicos de la imagen.
    
    Args:
        image_path: Ruta al archivo de imagen
        
    Returns:
        Diccionario con metadatos
    """
    metadata = {
        "filename": os.path.basename(image_path),
        "path": image_path,
        "size": 0,
        "dimensions": (0, 0),
        "format": "unknown"
    }
    
    try:
        # Obtener tamaño del archivo
        metadata["size"] = os.path.getsize(image_path)
        
        # Obtener dimensiones y formato
        with Image.open(image_path) as img:
            metadata["dimensions"] = img.size
            metadata["format"] = img.format
            
    except Exception as e:
        logger.error(f"Error al obtener metadatos de {image_path}: {str(e)}")
    
    return metadata

def format_geo_results(analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formatea los resultados del análisis para presentación.
    
    Args:
        analysis_results: Resultados brutos del análisis
        
    Returns:
        Resultados formateados listos para presentar
    """
    formatted = {
        "location": {
            "country": analysis_results.get("country", "No determinado"),
            "city": analysis_results.get("city", "No determinado"),
            "district": analysis_results.get("district", "No determinado"),
            "neighborhood": analysis_results.get("neighborhood", "No determinado"),
            "street": analysis_results.get("street", "No determinado")
        },
        "confidence": analysis_results.get("confidence", 0),
        "supporting_evidence": analysis_results.get("supporting_evidence", []),
        "possible_alternatives": analysis_results.get("possible_alternatives", []),
    }
    
    return formatted

def save_analysis_results(results: Dict[str, Any], image_path: str) -> str:
    """
    Guarda los resultados del análisis en un archivo JSON.
    
    Args:
        results: Resultados del análisis
        image_path: Ruta de la imagen analizada
        
    Returns:
        Ruta del archivo JSON generado
    """
    try:
        filename = os.path.basename(image_path)
        base_name = os.path.splitext(filename)[0]
        
        # Crear directorio de resultados si no existe
        results_dir = get_results_directory()
        
        # Guardar resultados
        output_path = os.path.join(results_dir, f"{base_name}_analysis.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
            
        logger.info(f"Resultados guardados en {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error al guardar resultados: {str(e)}")
        return ""

def save_analysis_results_with_filename(results: Dict[str, Any], filename: str) -> str:
    """
    Guarda los resultados del análisis en un archivo JSON con nombre específico.
    
    Args:
        results: Resultados del análisis
        filename: Nombre del archivo JSON a crear
        
    Returns:
        Ruta del archivo JSON generado
    """
    try:
        # Crear directorio de resultados si no existe
        results_dir = get_results_directory()
        
        # Guardar resultados
        output_path = os.path.join(results_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
            
        logger.info(f"Resultados guardados en {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error al guardar resultados: {str(e)}")
        return "" 