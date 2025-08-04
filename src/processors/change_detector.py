#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detector de cambios entre imágenes de la misma zona geográfica.
"""

import cv2
import numpy as np
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

class ChangeDetector:
    """Detector de cambios entre imágenes de la misma zona geográfica."""
    
    def __init__(self, sensitivity: float = 0.2):
        """
        Inicializa el detector de cambios.
        
        Args:
            sensitivity: Sensibilidad de detección (0.0-1.0)
        """
        self.sensitivity = sensitivity
        self.reference_images = {}  # Diccionario de imágenes de referencia por coordenadas
        logger.info(f"Detector de cambios inicializado (sensibilidad: {sensitivity})")
    
    def add_reference_image(self, image_data: bytes, coordinates: Dict[str, float], 
                           metadata: Dict[str, Any]) -> str:
        """
        Añade una imagen de referencia para una ubicación.
        
        Args:
            image_data: Datos de la imagen en bytes
            coordinates: Coordenadas geográficas (latitud, longitud)
            metadata: Metadatos adicionales
            
        Returns:
            ID de referencia
        """
        try:
            # Generar ID de ubicación
            location_id = self._generate_location_id(coordinates)
            
            # Procesar imagen
            processed_image = self._process_reference_image(image_data)
            if processed_image is None:
                return ""
            
            # Guardar imagen de referencia
            self._store_reference_image(location_id, processed_image, coordinates, metadata)
            
            logger.info(f"Imagen de referencia añadida para ubicación: {location_id}")
            return location_id
        except Exception as e:
            logger.error(f"Error al añadir imagen de referencia: {str(e)}")
            return ""
    
    def _generate_location_id(self, coordinates: Dict[str, float]) -> str:
        """Genera un ID único para la ubicación."""
        return f"{coordinates['latitude']:.5f}_{coordinates['longitude']:.5f}"
    
    def _process_reference_image(self, image_data: bytes) -> Optional[Dict[str, np.ndarray]]:
        """Procesa la imagen de referencia."""
        try:
            # Decodificar imagen
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convertir a escala de grises y aplicar blur para reducir ruido
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (21, 21), 0)
            
            return {"original": image, "processed": blur}
        except Exception as e:
            logger.error(f"Error al procesar imagen de referencia: {str(e)}")
            return None
    
    def _store_reference_image(self, location_id: str, processed_image: Dict[str, np.ndarray], 
                             coordinates: Dict[str, float], metadata: Dict[str, Any]) -> None:
        """Almacena la imagen de referencia procesada."""
        self.reference_images[location_id] = {
            "image": processed_image["processed"],
            "original": processed_image["original"],
            "metadata": metadata,
            "coordinates": coordinates
        }
    
    def detect_changes(self, image_data: bytes, location_id: str) -> Dict[str, Any]:
        """
        Detecta cambios entre la imagen actual y la de referencia.
        
        Args:
            image_data: Datos de la imagen actual en bytes
            location_id: ID de la ubicación de referencia
            
        Returns:
            Diccionario con los resultados de la detección
        """
        try:
            # Validar referencia
            if not self._validate_reference(location_id):
                return {"error": "Ubicación de referencia no encontrada"}
            
            # Procesar imagen actual
            current_image_data = self._process_current_image(image_data)
            if current_image_data is None:
                return {"error": "Error al procesar imagen actual"}
            
            # Detectar diferencias
            difference_data = self._calculate_differences(location_id, current_image_data)
            
            # Analizar contornos
            contour_data = self._analyze_contours(difference_data, current_image_data["original"])
            
            # Calcular métricas
            metrics = self._calculate_change_metrics(difference_data, contour_data)
            
            # Crear imagen con cambios marcados
            changes_image_bytes = self._create_changes_visualization(
                current_image_data["original"], contour_data["significant_contours"]
            )
            
            # Construir resultado
            return self._build_detection_result(location_id, metrics, changes_image_bytes, contour_data)
            
        except Exception as e:
            logger.error(f"Error en detección de cambios: {str(e)}")
            return {"error": str(e)}
    
    def _validate_reference(self, location_id: str) -> bool:
        """Valida que existe la imagen de referencia."""
        return location_id in self.reference_images
    
    def _process_current_image(self, image_data: bytes) -> Optional[Dict[str, np.ndarray]]:
        """Procesa la imagen actual para comparación."""
        try:
            # Decodificar imagen actual
            nparr = np.frombuffer(image_data, np.uint8)
            current_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convertir a escala de grises y aplicar blur
            gray = cv2.cvtColor(current_image, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (21, 21), 0)
            
            return {"original": current_image, "processed": blur}
        except Exception as e:
            logger.error(f"Error al procesar imagen actual: {str(e)}")
            return None
    
    def _calculate_differences(self, location_id: str, current_image_data: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Calcula las diferencias entre imágenes."""
        reference = self.reference_images[location_id]
        
        # Calcular diferencia absoluta entre imágenes
        frame_delta = cv2.absdiff(reference["image"], current_image_data["processed"])
        
        # Aplicar umbral para destacar diferencias
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Dilatar imagen umbralizada para llenar huecos
        dilated = cv2.dilate(thresh, None, iterations=2)
        
        return {"delta": frame_delta, "threshold": thresh, "dilated": dilated}
    
    def _analyze_contours(self, difference_data: Dict[str, np.ndarray], 
                         current_image: np.ndarray) -> Dict[str, Any]:
        """Analiza los contornos de las áreas de cambio."""
        # Encontrar contornos de las áreas de cambio
        contours, _ = cv2.findContours(
            difference_data["dilated"].copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Filtrar contornos por tamaño
        min_area = current_image.shape[0] * current_image.shape[1] * 0.005  # 0.5% del área total
        significant_contours = [c for c in contours if cv2.contourArea(c) > min_area]
        
        return {
            "all_contours": contours,
            "significant_contours": significant_contours,
            "min_area": min_area
        }
    
    def _calculate_change_metrics(self, difference_data: Dict[str, np.ndarray], 
                                contour_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula las métricas de cambio."""
        thresh = difference_data["threshold"]
        
        # Calcular porcentaje de cambio
        change_pixels = np.sum(thresh > 0)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        change_percentage = (change_pixels / total_pixels) * 100
        
        # Determinar si hay cambios significativos
        has_significant_changes = change_percentage > (self.sensitivity * 100)
        
        return {
            "change_percentage": change_percentage,
            "has_significant_changes": has_significant_changes,
            "significant_areas": len(contour_data["significant_contours"])
        }
    
    def _create_changes_visualization(self, current_image: np.ndarray, 
                                    significant_contours: List) -> bytes:
        """Crea una visualización de los cambios detectados."""
        # Crear imagen con cambios marcados
        changes_image = current_image.copy()
        for contour in significant_contours:
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(changes_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Codificar imagen resultante
        _, buffer = cv2.imencode('.jpg', changes_image)
        return buffer.tobytes()
    
    def _build_detection_result(self, location_id: str, metrics: Dict[str, float], 
                              changes_image_bytes: bytes, contour_data: Dict[str, Any]) -> Dict[str, Any]:
        """Construye el resultado final de la detección."""
        reference = self.reference_images[location_id]
        
        result = {
            "location_id": location_id,
            "has_changes": metrics["has_significant_changes"],
            "change_percentage": metrics["change_percentage"],
            "significant_areas": metrics["significant_areas"],
            "changes_image": changes_image_bytes,
            "timestamp": reference["metadata"].get("timestamp", 0)
        }
        
        logger.info(f"Detección de cambios completada: {metrics['change_percentage']:.2f}% de cambio")
        return result
    
    def get_reference_image(self, location_id: str) -> Optional[bytes]:
        """
        Obtiene la imagen de referencia para una ubicación.
        
        Args:
            location_id: ID de la ubicación
            
        Returns:
            Datos de la imagen de referencia o None si no existe
        """
        if location_id not in self.reference_images:
            return None
        
        reference = self.reference_images[location_id]
        _, buffer = cv2.imencode('.jpg', reference["original"])
        return buffer.tobytes()
    
    def remove_reference_image(self, location_id: str) -> bool:
        """
        Elimina una imagen de referencia.
        
        Args:
            location_id: ID de la ubicación
            
        Returns:
            True si se eliminó correctamente
        """
        if location_id not in self.reference_images:
            return False
        
        del self.reference_images[location_id]
        logger.info(f"Imagen de referencia eliminada: {location_id}")
        return True 