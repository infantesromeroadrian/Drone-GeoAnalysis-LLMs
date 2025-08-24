#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo para detección de objetos usando YOLO 11.
Responsabilidad única: Coordinación de la detección de objetos.
"""

import logging
from typing import Dict, List, Any, Optional

from src.utils.image_processor import ImageProcessor
from src.utils.yolo_model_manager import YoloModelManager
from src.utils.yolo_result_formatter import YoloResultFormatter
from src.utils.image_annotator import ImageAnnotator

logger = logging.getLogger(__name__)


class YoloObjectDetector:
    """
    Detector de objetos YOLO coordinador.
    Responsabilidad única: Coordinación de la detección usando componentes.
    """
    
    def __init__(self, confidence_threshold: float = 0.5, 
                 nms_threshold: float = 0.4):
        """
        Inicializa el detector YOLO.
        
        Args:
            confidence_threshold: Umbral de confianza por defecto
            nms_threshold: Umbral NMS por defecto
        """
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        
        # Inicializar componentes
        self.image_processor = ImageProcessor()
        self.model_manager = YoloModelManager()
        self.result_formatter = YoloResultFormatter()
        self.image_annotator = ImageAnnotator(self.image_processor)
        
        # Inicializar modelo
        self._initialize_components()
        
        logger.info("Detector YOLO 11 coordinador inicializado")
    
    def _initialize_components(self) -> None:
        """Inicializa los componentes del detector."""
        success = self.model_manager.initialize_model()
        if not success:
            logger.warning("Modelo YOLO no inicializado correctamente")
    
    def detect_objects(self, image_data: bytes, 
                      confidence_threshold: Optional[float] = None,
                      nms_threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Detecta objetos en una imagen.
        
        Args:
            image_data: Datos de la imagen en bytes
            confidence_threshold: Umbral de confianza (opcional)
            nms_threshold: Umbral NMS (opcional)
            
        Returns:
            Diccionario con resultados de detección
        """
        # Validar modelo
        if not self.model_manager.is_model_ready():
            return self.result_formatter.format_error_response(
                "YOLO 11 no está disponible", 
                self.model_manager.is_initialized
            )
        
        # Configurar parámetros
        conf_threshold = confidence_threshold or self.confidence_threshold
        nms_threshold = nms_threshold or self.nms_threshold
        
        try:
            # Procesar imagen
            image = self._process_input_image(image_data)
            if image is None:
                return self.result_formatter.format_error_response(
                    "Error procesando imagen"
                )
            
            # Ejecutar detección
            results = self._run_detection(image, conf_threshold, nms_threshold)
            
            # Procesar resultados
            detections = self._process_detections(results[0], image.shape)
            
            # Anotar imagen
            annotated_image = self._annotate_image(image, results[0])
            
            return self.result_formatter.format_response(
                success=True,
                detections=detections,
                annotated_image=annotated_image,
                conf_threshold=conf_threshold,
                nms_threshold=nms_threshold
            )
            
        except Exception as e:
            logger.error(f"Error en detección YOLO: {str(e)}")
            return self.result_formatter.format_error_response(str(e))
    
    def _process_input_image(self, image_data: bytes):
        """
        Procesa la imagen de entrada.
        
        Args:
            image_data: Datos de imagen en bytes
            
        Returns:
            Array numpy con la imagen procesada
        """
        return self.image_processor.bytes_to_array(image_data)
    
    def _run_detection(self, image, conf_threshold: float, nms_threshold: float):
        """
        Ejecuta la detección con el modelo.
        
        Args:
            image: Imagen procesada
            conf_threshold: Umbral de confianza
            nms_threshold: Umbral NMS
            
        Returns:
            Resultados de la detección
        """
        return self.model_manager.predict(
            image, conf_threshold, nms_threshold
        )
    
    def _process_detections(self, results, image_shape) -> List[Dict[str, Any]]:
        """
        Procesa los resultados de detección.
        
        Args:
            results: Resultados de YOLO
            image_shape: Forma de la imagen
            
        Returns:
            Lista de detecciones formateadas
        """
        detections = []
        
        if results.boxes is not None:
            boxes = results.boxes.cpu().numpy()
            class_names = self.model_manager.get_class_names()
            
            for i, box in enumerate(boxes):
                detection = self.result_formatter.format_detection(
                    box, class_names, i, image_shape
                )
                detections.append(detection)
        
        return detections
    
    def _annotate_image(self, image, yolo_results) -> str:
        """
        Anota la imagen con las detecciones.
        
        Args:
            image: Imagen original
            yolo_results: Resultados de YOLO
            
        Returns:
            Imagen anotada en base64
        """
        return self.image_annotator.annotate_yolo_results(image, yolo_results)
    
    def get_available_classes(self) -> List[str]:
        """
        Obtiene lista de clases disponibles para detección.
        
        Returns:
            Lista de nombres de clases
        """
        return self.model_manager.get_available_classes()
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Obtiene información del modelo YOLO.
        
        Returns:
            Información del modelo
        """
        return self.result_formatter.format_model_info(
            self.model_manager.is_initialized,
            self.model_manager.get_class_names(),
            self.confidence_threshold,
            self.nms_threshold
        )
    
    def is_initialized(self) -> bool:
        """
        Verifica si el detector está inicializado.
        
        Returns:
            True si está inicializado
        """
        return self.model_manager.is_model_ready()
    
    def set_thresholds(self, confidence: Optional[float] = None, nms: Optional[float] = None) -> None:
        """
        Configura los umbrales del detector.
        
        Args:
            confidence: Nuevo umbral de confianza
            nms: Nuevo umbral NMS
        """
        if confidence is not None:
            self.confidence_threshold = confidence
        if nms is not None:
            self.nms_threshold = nms
        
        logger.info(f"Umbrales actualizados: conf={self.confidence_threshold}, "
                   f"nms={self.nms_threshold}") 