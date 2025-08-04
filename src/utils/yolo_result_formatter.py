#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo para formateo de resultados YOLO.
Responsabilidad única: Formateo y estructuración de resultados de detección.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class YoloResultFormatter:
    """
    Formateador de resultados YOLO con funciones puras.
    Responsabilidad única: Estructuración de datos de detección.
    """
    
    @staticmethod
    def format_detection(box_data: Any, class_names: Dict[int, str], 
                        detection_id: int, image_shape: Tuple[int, int, int]) -> Dict[str, Any]:
        """
        Formatea una detección individual.
        
        Args:
            box_data: Datos del bounding box de YOLO
            class_names: Diccionario de nombres de clases
            detection_id: ID de la detección
            image_shape: Dimensiones de la imagen (height, width, channels)
            
        Returns:
            Diccionario con detección formateada
        """
        # Extraer coordenadas y datos
        x1, y1, x2, y2 = box_data.xyxy[0]
        class_id = int(box_data.cls[0])
        confidence = float(box_data.conf[0])
        class_name = class_names.get(class_id, f"class_{class_id}")
        
        # Calcular dimensiones
        width = x2 - x1
        height = y2 - y1
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Obtener dimensiones de imagen
        img_height, img_width = image_shape[:2]
        
        return {
            'id': detection_id,
            'class_name': class_name,
            'class_id': class_id,
            'confidence': round(confidence, 3),
            'bbox': YoloResultFormatter._format_bbox(
                x1, y1, x2, y2, width, height, center_x, center_y
            ),
            'normalized_bbox': YoloResultFormatter._format_normalized_bbox(
                x1, y1, x2, y2, center_x, center_y, img_width, img_height
            ),
            'area': int(width * height),
            'area_percentage': YoloResultFormatter._calculate_area_percentage(
                width, height, img_width, img_height
            )
        }
    
    @staticmethod
    def _format_bbox(x1: float, y1: float, x2: float, y2: float,
                    width: float, height: float, center_x: float, 
                    center_y: float) -> Dict[str, int]:
        """
        Formatea bounding box absoluto.
        
        Args:
            x1, y1, x2, y2: Coordenadas del bounding box
            width, height: Dimensiones del bounding box
            center_x, center_y: Centro del bounding box
            
        Returns:
            Diccionario con coordenadas absolutas
        """
        return {
            'x1': int(x1),
            'y1': int(y1),
            'x2': int(x2),
            'y2': int(y2),
            'width': int(width),
            'height': int(height),
            'center_x': int(center_x),
            'center_y': int(center_y)
        }
    
    @staticmethod
    def _format_normalized_bbox(x1: float, y1: float, x2: float, y2: float,
                               center_x: float, center_y: float,
                               img_width: int, img_height: int) -> Dict[str, float]:
        """
        Formatea bounding box normalizado.
        
        Args:
            x1, y1, x2, y2: Coordenadas del bounding box
            center_x, center_y: Centro del bounding box
            img_width, img_height: Dimensiones de la imagen
            
        Returns:
            Diccionario con coordenadas normalizadas
        """
        return {
            'x1': round(x1 / img_width, 4),
            'y1': round(y1 / img_height, 4),
            'x2': round(x2 / img_width, 4),
            'y2': round(y2 / img_height, 4),
            'center_x': round(center_x / img_width, 4),
            'center_y': round(center_y / img_height, 4)
        }
    
    @staticmethod
    def _calculate_area_percentage(width: float, height: float,
                                  img_width: int, img_height: int) -> float:
        """
        Calcula el porcentaje de área que ocupa la detección.
        
        Args:
            width, height: Dimensiones del bounding box
            img_width, img_height: Dimensiones de la imagen
            
        Returns:
            Porcentaje de área ocupada
        """
        detection_area = width * height
        total_area = img_width * img_height
        return round((detection_area / total_area) * 100, 2)
    
    @staticmethod
    def format_response(success: bool, detections: List[Dict[str, Any]],
                       annotated_image: str, conf_threshold: float,
                       nms_threshold: float, model_version: str = "YOLO 11n",
                       error_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Formatea la respuesta completa del detector.
        
        Args:
            success: Indica si la detección fue exitosa
            detections: Lista de detecciones
            annotated_image: Imagen anotada en base64
            conf_threshold: Umbral de confianza usado
            nms_threshold: Umbral NMS usado
            model_version: Versión del modelo
            error_message: Mensaje de error si existe
            
        Returns:
            Diccionario con respuesta formateada
        """
        response = {
            'success': success,
            'detections': detections,
            'total_objects': len(detections),
            'annotated_image': annotated_image,
            'model_version': model_version
        }
        
        if success:
            response.update({
                'confidence_threshold': conf_threshold,
                'nms_threshold': nms_threshold
            })
        else:
            response.update({
                'error': error_message,
                'confidence_threshold': None,
                'nms_threshold': None
            })
        
        return response
    
    @staticmethod
    def format_error_response(error_message: str, is_initialized: bool = False) -> Dict[str, Any]:
        """
        Formatea respuesta de error estandarizada.
        
        Args:
            error_message: Mensaje de error
            is_initialized: Si el modelo está inicializado
            
        Returns:
            Diccionario con información de error
        """
        return {
            'success': False,
            'error': error_message,
            'detections': [],
            'total_objects': 0,
            'annotated_image': '',
            'model_version': 'YOLO 11n',
            'confidence_threshold': None,
            'nms_threshold': None,
            'installation_required': not is_initialized,
            'install_command': 'pip install ultralytics torch torchvision' if not is_initialized else None
        }
    
    @staticmethod
    def format_model_info(is_initialized: bool, class_names: Dict[int, str],
                         confidence_threshold: float, nms_threshold: float) -> Dict[str, Any]:
        """
        Formatea información del modelo.
        
        Args:
            is_initialized: Si el modelo está inicializado
            class_names: Diccionario de nombres de clases
            confidence_threshold: Umbral de confianza
            nms_threshold: Umbral NMS
            
        Returns:
            Información del modelo formateada
        """
        info = {
            'model_name': 'YOLO 11n',
            'is_initialized': is_initialized,
            'confidence_threshold': confidence_threshold,
            'nms_threshold': nms_threshold,
        }
        
        if is_initialized:
            info.update({
                'total_classes': len(class_names),
                'available_classes': list(class_names.values())
            })
        else:
            info.update({
                'total_classes': 0,
                'available_classes': [],
                'error': 'YOLO 11 no está inicializado',
                'install_command': 'pip install ultralytics torch torchvision',
                'model_url': 'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt'
            })
        
        return info 