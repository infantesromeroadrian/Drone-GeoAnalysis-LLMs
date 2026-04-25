#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo para gestión del modelo YOLO.
Responsabilidad única: Carga, inicialización y manejo del modelo YOLO.
"""

import os
import logging
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class YoloModelManager:
    """
    Gestor del modelo YOLO con responsabilidad única.
    Responsabilidad única: Manejo del ciclo de vida del modelo.
    """
    
    # Constantes de configuración
    MODEL_PATHS = [
        '/root/.cache/ultralytics/yolo11n.pt',
        '/app/yolo11n.pt',
        'yolo11n.pt'
    ]
    
    DEFAULT_MODEL_NAME = 'yolo11n.pt'
    
    def __init__(self):
        """Inicializa el gestor de modelos."""
        self.model = None
        self.class_names = {}
        self.is_initialized = False
        
    def initialize_model(self) -> bool:
        """
        Inicializa el modelo YOLO.
        
        Returns:
            True si la inicialización fue exitosa, False en caso contrario
        """
        try:
            # Importar ultralytics
            from ultralytics import YOLO  # type: ignore
            
            logger.info("Initializing YOLO 11n...")

            # Buscar modelo en ubicaciones conocidas
            model_path = self._find_model_path()

            if not model_path:
                logger.error("YOLO 11n model not found")
                return False

            # Cargar modelo
            self.model = YOLO(model_path)
            self.class_names = self.model.names
            self.is_initialized = True

            logger.info("Model loaded from: %s", model_path)
            logger.info("Available classes: %d", len(self.class_names))

            return True

        except ImportError as e:
            logger.error("Ultralytics unavailable: %s", e)
            logger.error("Install with: pip install ultralytics")
            return False

        except Exception as e:
            logger.error("Error initializing model: %s", e)
            return self._try_auto_download()
    
    def _find_model_path(self) -> Optional[str]:
        """
        Busca el modelo en las rutas conocidas.
        
        Returns:
            Ruta del modelo si se encuentra, None en caso contrario
        """
        for path in self.MODEL_PATHS:
            if os.path.exists(path):
                logger.info("Model found at: %s", path)
                return path

        # Si no se encuentra, usar el nombre por defecto (auto-descarga)
        logger.info("Using auto-download")
        return self.DEFAULT_MODEL_NAME
    
    def _try_auto_download(self) -> bool:
        """
        Intenta descargar automáticamente el modelo.
        
        Returns:
            True si la descarga fue exitosa, False en caso contrario
        """
        try:
            from ultralytics import YOLO  # type: ignore
            
            logger.info("Downloading YOLO 11n model...")

            # Descargar modelo
            self.model = YOLO(self.DEFAULT_MODEL_NAME)
            self.class_names = self.model.names
            self.is_initialized = True

            logger.info("Model downloaded and initialized")
            return True

        except Exception as e:
            logger.error("Error downloading model: %s", e)
            logger.error("Check internet connection")
            return False
    
    def predict(self, image, confidence_threshold: float = 0.5, 
                nms_threshold: float = 0.4):
        """
        Ejecuta predicción con el modelo.
        
        Args:
            image: Imagen para procesar
            confidence_threshold: Umbral de confianza
            nms_threshold: Umbral NMS
            
        Returns:
            Resultados de la predicción
        """
        if not self.is_initialized:
            raise RuntimeError("Modelo no inicializado")
        
        return self.model(image, conf=confidence_threshold, iou=nms_threshold)  # type: ignore
    
    def get_class_names(self) -> Dict[int, str]:
        """
        Obtiene nombres de clases del modelo.
        
        Returns:
            Diccionario con nombres de clases
        """
        return self.class_names
    
    def get_available_classes(self) -> List[str]:
        """
        Obtiene lista de clases disponibles.
        
        Returns:
            Lista de nombres de clases
        """
        return list(self.class_names.values()) if self.is_initialized else []
    
    def is_model_ready(self) -> bool:
        """
        Verifica si el modelo está listo para usar.
        
        Returns:
            True si el modelo está inicializado y listo
        """
        return self.is_initialized and self.model is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Obtiene información básica del modelo.
        
        Returns:
            Diccionario con información del modelo
        """
        return {
            'model_name': 'YOLO 11n',
            'is_initialized': self.is_initialized,
            'total_classes': len(self.class_names) if self.is_initialized else 0,
            'has_model': self.model is not None
        } 