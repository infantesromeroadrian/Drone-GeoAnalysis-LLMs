#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo para procesamiento de imágenes.
Responsabilidad única: Operaciones de procesamiento de imágenes.
"""

import cv2
import numpy as np
import base64
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Procesador de imágenes con funciones puras.
    Responsabilidad única: Transformaciones de imágenes.
    """
    
    @staticmethod
    def bytes_to_array(image_data: bytes) -> Optional[np.ndarray]:
        """
        Convierte bytes de imagen a array numpy.
        
        Args:
            image_data: Datos de imagen en bytes
            
        Returns:
            Array numpy con la imagen o None si hay error
        """
        try:
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("No se pudo decodificar la imagen")
                return None
                
            # Convertir de BGR a RGB para YOLO
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
        except Exception as e:
            logger.error(f"Error procesando imagen: {str(e)}")
            return None
    
    @staticmethod
    def array_to_base64(image: np.ndarray) -> str:
        """
        Convierte array numpy a base64.
        
        Args:
            image: Imagen en formato numpy
            
        Returns:
            Imagen codificada en base64
        """
        try:
            # Convertir RGB a BGR para OpenCV
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            # Codificar imagen
            _, buffer = cv2.imencode('.jpg', image_bgr)
            image_bytes = buffer.tobytes()
            
            # Convertir a base64
            return base64.b64encode(image_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error convirtiendo imagen a base64: {str(e)}")
            return ""
    
    @staticmethod
    def get_image_dimensions(image: np.ndarray) -> Tuple[int, ...]:
        """
        Obtiene dimensiones de la imagen.
        
        Args:
            image: Imagen en formato numpy
            
        Returns:
            Tupla con (height, width) o (height, width, channels)
        """
        return image.shape
    
    @staticmethod
    def draw_bounding_box(image: np.ndarray, x1: int, y1: int, 
                         x2: int, y2: int, color: Tuple[int, int, int] = (0, 255, 0),
                         thickness: int = 2) -> np.ndarray:
        """
        Dibuja un bounding box en la imagen.
        
        Args:
            image: Imagen donde dibujar
            x1, y1, x2, y2: Coordenadas del bounding box
            color: Color del bounding box en RGB
            thickness: Grosor de la línea
            
        Returns:
            Imagen con bounding box dibujado
        """
        return cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
    
    @staticmethod
    def draw_label(image: np.ndarray, text: str, x: int, y: int,
                  font_scale: float = 0.6, thickness: int = 2,
                  text_color: Tuple[int, int, int] = (0, 0, 0),
                  bg_color: Tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
        """
        Dibuja texto con fondo en la imagen.
        
        Args:
            image: Imagen donde dibujar
            text: Texto a dibujar
            x, y: Coordenadas del texto
            font_scale: Escala de la fuente
            thickness: Grosor del texto
            text_color: Color del texto en RGB
            bg_color: Color del fondo en RGB
            
        Returns:
            Imagen con texto dibujado
        """
        # Obtener tamaño del texto
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 
                                   font_scale, thickness)[0]
        
        # Dibujar fondo
        cv2.rectangle(image, (x, y - text_size[1] - 10),
                     (x + text_size[0], y), bg_color, -1)
        
        # Dibujar texto
        cv2.putText(image, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX,
                   font_scale, text_color, thickness)
        
        return image 