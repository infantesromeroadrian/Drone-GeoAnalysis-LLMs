#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo para anotación de imágenes con detecciones.
Responsabilidad única: Anotación visual de resultados de detección.
"""

import numpy as np
import logging
from typing import Dict, List, Any, Tuple
from src.utils.image_processor import ImageProcessor

logger = logging.getLogger(__name__)


class ImageAnnotator:
    """
    Anotador de imágenes con responsabilidad única.
    Responsabilidad única: Anotación visual de detecciones.
    """
    
    # Constantes de configuración
    DEFAULT_COLOR = (0, 255, 0)  # Verde
    DEFAULT_THICKNESS = 2
    DEFAULT_FONT_SCALE = 0.6
    TEXT_COLOR = (0, 0, 0)  # Negro
    
    def __init__(self, image_processor: ImageProcessor):
        """
        Inicializa el anotador.
        
        Args:
            image_processor: Instancia del procesador de imágenes
        """
        self.image_processor = image_processor
    
    def annotate_detections(self, image: np.ndarray, 
                           detections: List[Dict[str, Any]]) -> str:
        """
        Anota una imagen con las detecciones.
        
        Args:
            image: Imagen original
            detections: Lista de detecciones
            
        Returns:
            Imagen anotada codificada en base64
        """
        try:
            # Crear copia para anotar
            annotated_image = image.copy()
            
            # Anotar cada detección
            for detection in detections:
                annotated_image = self._annotate_single_detection(
                    annotated_image, detection
                )
            
            return self.image_processor.array_to_base64(annotated_image)
            
        except Exception as e:
            logger.error(f"Error anotando imagen: {str(e)}")
            return self.image_processor.array_to_base64(image)
    
    def _annotate_single_detection(self, image: np.ndarray, 
                                  detection: Dict[str, Any]) -> np.ndarray:
        """
        Anota una sola detección en la imagen.
        
        Args:
            image: Imagen a anotar
            detection: Datos de la detección
            
        Returns:
            Imagen con la detección anotada
        """
        # Extraer datos de la detección
        bbox = detection['bbox']
        class_name = detection['class_name']
        confidence = detection['confidence']
        
        # Dibujar bounding box
        image = self.image_processor.draw_bounding_box(
            image, bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2'],
            self.DEFAULT_COLOR, self.DEFAULT_THICKNESS
        )
        
        # Crear y dibujar etiqueta
        label = f"{class_name}: {confidence:.2f}"
        image = self.image_processor.draw_label(
            image, label, bbox['x1'], bbox['y1'],
            self.DEFAULT_FONT_SCALE, self.DEFAULT_THICKNESS,
            self.TEXT_COLOR, self.DEFAULT_COLOR
        )
        
        return image
    
    def annotate_yolo_results(self, image: np.ndarray, 
                             yolo_results) -> str:
        """
        Anota imagen directamente con resultados de YOLO.
        
        Args:
            image: Imagen original
            yolo_results: Resultados directos de YOLO
            
        Returns:
            Imagen anotada codificada en base64
        """
        try:
            # Crear copia para anotar
            annotated_image = image.copy()
            
            if yolo_results.boxes is not None:
                boxes = yolo_results.boxes.cpu().numpy()
                class_names = yolo_results.names
                
                for box in boxes:
                    # Extraer datos
                    coords = self._extract_box_coordinates(box)
                    class_info = self._extract_class_info(box, class_names)
                    
                    # Anotar
                    annotated_image = self._draw_box_and_label(
                        annotated_image, coords, class_info
                    )
            
            return self.image_processor.array_to_base64(annotated_image)
            
        except Exception as e:
            logger.error(f"Error anotando resultados YOLO: {str(e)}")
            return self.image_processor.array_to_base64(image)
    
    def _extract_box_coordinates(self, box) -> Tuple[int, int, int, int]:
        """
        Extrae coordenadas del bounding box.
        
        Args:
            box: Datos del bounding box de YOLO
            
        Returns:
            Tupla con coordenadas (x1, y1, x2, y2)
        """
        x1, y1, x2, y2 = box.xyxy[0]
        return int(x1), int(y1), int(x2), int(y2)
    
    def _extract_class_info(self, box, class_names: Dict[int, str]) -> Dict[str, Any]:
        """
        Extrae información de clase y confianza.
        
        Args:
            box: Datos del bounding box de YOLO
            class_names: Diccionario de nombres de clases
            
        Returns:
            Diccionario con información de clase
        """
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        class_name = class_names.get(class_id, f"class_{class_id}")
        
        return {
            'class_name': class_name,
            'confidence': confidence
        }
    
    def _draw_box_and_label(self, image: np.ndarray, 
                           coords: Tuple[int, int, int, int],
                           class_info: Dict[str, Any]) -> np.ndarray:
        """
        Dibuja bounding box y etiqueta en la imagen.
        
        Args:
            image: Imagen donde dibujar
            coords: Coordenadas del bounding box
            class_info: Información de clase
            
        Returns:
            Imagen con anotaciones
        """
        x1, y1, x2, y2 = coords
        
        # Dibujar bounding box
        image = self.image_processor.draw_bounding_box(
            image, x1, y1, x2, y2, self.DEFAULT_COLOR, self.DEFAULT_THICKNESS
        )
        
        # Crear y dibujar etiqueta
        label = f"{class_info['class_name']}: {class_info['confidence']:.2f}"
        image = self.image_processor.draw_label(
            image, label, x1, y1, self.DEFAULT_FONT_SCALE,
            self.DEFAULT_THICKNESS, self.TEXT_COLOR, self.DEFAULT_COLOR
        )
        
        return image 