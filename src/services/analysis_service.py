#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de análisis de imágenes para lógica de negocio.
Responsabilidad única: Gestionar análisis geográfico y detección de objetos.
"""

import logging
import os
import tempfile
from datetime import datetime
from flask import send_from_directory
from typing import Dict, Any, Optional, List

from src.utils.helpers import get_image_metadata, save_analysis_results_with_filename
from src.models.yolo_detector import YoloObjectDetector

logger = logging.getLogger(__name__)

class AnalysisService:
    """
    Servicio que encapsula la lógica de negocio para análisis de imágenes.
    Maneja el procesamiento y almacenamiento de resultados.
    """
    
    def __init__(self, geo_analyzer, yolo_detector: Optional[YoloObjectDetector] = None):
        """
        Inicializa el servicio de análisis.
        
        Args:
            geo_analyzer: Instancia del analizador geográfico
            yolo_detector: Instancia del detector YOLO 11 (opcional)
        """
        self.analyzer = geo_analyzer
        self.yolo_detector = yolo_detector or YoloObjectDetector()
        logger.info("Servicio de análisis inicializado")
    
    def analyze_image(self, image_file, config_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa una imagen y retorna los resultados del análisis geográfico.
        Ahora incluye detección YOLO para enriquecer el análisis.
        
        Args:
            image_file: Archivo de imagen Flask
            config_params: Parámetros de configuración del análisis
            
        Returns:
            Diccionario con resultados del análisis geográfico enriquecido
        """
        try:
            # Guardar imagen en directorio temporal
            temp_path = self._save_temp_image(image_file)
            
            # Obtener metadatos y agregar configuración
            metadata = self._prepare_metadata(temp_path, config_params)
            
            # PASO 1: Ejecutar detección YOLO para obtener contexto de objetos
            yolo_context = self._get_yolo_context_for_geographic_analysis(temp_path)
            
            # PASO 2: Codificar imagen en base64 para GPT-4 Vision
            encoded_result = self._encode_image(temp_path)
            if not encoded_result:
                return {
                    'error': 'Error al procesar la imagen. Formato no compatible.',
                    'status': 'error'
                }
            
            encoded_image, image_format = encoded_result
            
            # PASO 3: Agregar contexto YOLO a los metadatos
            metadata['yolo_context'] = yolo_context
            
            # PASO 4: Analizar la imagen con GPT-4 Vision (enriquecido con YOLO)
            results = self.analyzer.analyze_image(encoded_image, metadata, image_format)
            
            # PASO 5: Aplicar filtro de confianza si es necesario
            self._apply_confidence_filter(results, config_params.get('confidence_threshold', 0))
            
            # PASO 6: Agregar información YOLO a los resultados finales
            results['yolo_detected_objects'] = yolo_context
            results['analysis_type'] = 'hybrid_geographic_with_object_detection'
            
            # PASO 7: Guardar resultados
            save_path = self._save_results(results)
            
            return {
                'results': results,
                'saved_path': save_path,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Error en análisis híbrido: {str(e)}")
            return {'error': str(e), 'status': 'error'}
    
    def analyze_objects_yolo(self, image_file, config_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detecta objetos en una imagen usando YOLO 11.
        
        Args:
            image_file: Archivo de imagen Flask
            config_params: Parámetros de configuración del análisis
            
        Returns:
            Diccionario con resultados de detección de objetos
        """
        try:
            # Guardar imagen en directorio temporal
            temp_path = self._save_temp_image(image_file)
            
            # Leer imagen como bytes
            image_bytes = self._read_image_as_bytes(temp_path)
            if not image_bytes:
                return {
                    'error': 'Error al procesar la imagen. Formato no compatible.',
                    'status': 'error'
                }
            
            # Obtener parámetros de configuración
            confidence_threshold = config_params.get('confidence_threshold', 0.5)
            nms_threshold = config_params.get('nms_threshold', 0.4)
            
            # Ejecutar detección YOLO
            results = self.yolo_detector.detect_objects(
                image_bytes,
                confidence_threshold=confidence_threshold,
                nms_threshold=nms_threshold
            )
            
            # Añadir metadatos de la imagen
            metadata = self._prepare_metadata(temp_path, config_params)
            results['image_metadata'] = metadata
            
            # Guardar resultados
            save_path = self._save_yolo_results(results)
            
            return {
                'results': results,
                'saved_path': save_path,
                'status': 'completed',
                'analysis_type': 'yolo_detection'
            }
            
        except Exception as e:
            logger.error(f"Error en análisis YOLO: {str(e)}")
            return {'error': str(e), 'status': 'error'}
    
    def get_yolo_model_info(self) -> Dict[str, Any]:
        """
        Obtiene información del modelo YOLO.
        
        Returns:
            Información del modelo YOLO
        """
        try:
            return self.yolo_detector.get_model_info()
        except Exception as e:
            logger.error(f"Error obteniendo información del modelo YOLO: {str(e)}")
            return {'error': str(e), 'is_initialized': False}
    
    def serve_result_file(self, filename: str):
        """
        Sirve archivos de resultados guardados.
        
        Args:
            filename: Nombre del archivo a servir
            
        Returns:
            Respuesta Flask con el archivo
        """
        results_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "results"
        )
        return send_from_directory(results_dir, filename)
    
    def get_analysis_status(self, analysis_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de un análisis en progreso.
        
        Args:
            analysis_id: ID del análisis
            
        Returns:
            Estado del análisis
        """
        # En una implementación real, esto consultaría una base de datos
        # Aquí simulamos para demostración
        return {
            'id': analysis_id,
            'status': 'processing',
            'progress': 70,
            'estimated_time_remaining': '30 segundos'
        }
    
    def _save_temp_image(self, image_file) -> str:
        """Guarda la imagen en un directorio temporal."""
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, image_file.filename)
        image_file.save(temp_path)
        return temp_path
    
    def _prepare_metadata(self, temp_path: str, config_params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara metadatos combinando información de imagen y configuración."""
        metadata = get_image_metadata(temp_path)
        metadata.update(config_params)
        return metadata
    
    def _encode_image(self, temp_path: str):
        """Codifica la imagen en base64."""
        try:
            from src.utils.helpers import encode_image_to_base64
            return encode_image_to_base64(temp_path)
        except ImportError:
            # Fallback si no está disponible
            import base64
            with open(temp_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            return encoded, 'jpeg'
    
    def _apply_confidence_filter(self, results: Dict[str, Any], confidence_threshold: float):
        """Aplica filtro de confianza a los resultados."""
        if confidence_threshold > 0:
            if results.get('confidence', 0) < confidence_threshold:
                results['warning'] = (
                    f"Resultados por debajo del umbral de confianza ({confidence_threshold}%)"
                )
    
    def _save_results(self, results: Dict[str, Any]) -> str:
        """Guarda los resultados del análisis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{timestamp}.json"
        return save_analysis_results_with_filename(results, filename)
    
    def _read_image_as_bytes(self, temp_path: str) -> bytes:
        """
        Lee la imagen como bytes para procesamiento YOLO.
        
        Args:
            temp_path: Ruta temporal de la imagen
            
        Returns:
            Datos de la imagen en bytes
        """
        try:
            with open(temp_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error leyendo imagen como bytes: {str(e)}")
            return b''
    
    def _save_yolo_results(self, results: Dict[str, Any]) -> str:
        """
        Guarda los resultados del análisis YOLO.
        
        Args:
            results: Resultados de detección YOLO
            
        Returns:
            Ruta del archivo guardado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"yolo_detection_{timestamp}.json"
        return save_analysis_results_with_filename(results, filename)
    
    def _get_yolo_context_for_geographic_analysis(self, temp_path: str) -> Dict[str, Any]:
        """
        Ejecuta YOLO para obtener contexto de objetos para el análisis geográfico.
        
        Args:
            temp_path: Ruta temporal de la imagen
            
        Returns:
            Diccionario con contexto de objetos detectados
        """
        try:
            # Leer imagen como bytes
            image_bytes = self._read_image_as_bytes(temp_path)
            if not image_bytes:
                logger.warning("No se pudo procesar imagen para contexto YOLO")
                return {"error": "No se pudo procesar imagen"}
            
            # Ejecutar detección YOLO con umbrales optimizados para contexto
            yolo_results = self.yolo_detector.detect_objects(
                image_bytes,
                confidence_threshold=0.3,  # Umbral más bajo para más contexto
                nms_threshold=0.4
            )
            
            if not yolo_results.get('success', False):
                logger.warning("YOLO no disponible para contexto geográfico")
                return {"error": "YOLO no disponible"}
            
            # Extraer información relevante para análisis geográfico
            context = {
                "total_objects": yolo_results.get('total_objects', 0),
                "object_summary": self._create_object_summary(yolo_results.get('detections', [])),
                "prominent_objects": self._get_prominent_objects(yolo_results.get('detections', [])),
                "geographic_indicators": self._extract_geographic_indicators(yolo_results.get('detections', []))
            }
            
            logger.info(f"Contexto YOLO generado: {context['total_objects']} objetos detectados")
            return context
            
        except Exception as e:
            logger.warning(f"Error obteniendo contexto YOLO: {str(e)}")
            return {"error": f"Error contexto YOLO: {str(e)}"}
    
    def _create_object_summary(self, detections: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Crea un resumen de objetos detectados por categoría.
        
        Args:
            detections: Lista de detecciones YOLO
            
        Returns:
            Diccionario con conteo por categoría
        """
        summary = {}
        for detection in detections:
            class_name = detection.get('class_name', 'unknown')
            summary[class_name] = summary.get(class_name, 0) + 1
        return summary
    
    def _get_prominent_objects(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Obtiene los objetos más prominentes (alta confianza y área).
        
        Args:
            detections: Lista de detecciones YOLO
            
        Returns:
            Lista de objetos prominentes
        """
        # Filtrar por confianza alta y área significativa
        prominent = []
        for detection in detections:
            confidence = detection.get('confidence', 0)
            area_percentage = detection.get('area_percentage', 0)
            
            if confidence >= 0.7 and area_percentage >= 5.0:
                prominent.append({
                    'class_name': detection.get('class_name'),
                    'confidence': confidence,
                    'area_percentage': area_percentage
                })
        
        # Ordenar por confianza y área
        prominent.sort(key=lambda x: (x['confidence'] + x['area_percentage']/100), reverse=True)
        return prominent[:10]  # Top 10 objetos prominentes
    
    def _extract_geographic_indicators(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extrae indicadores geográficos basados en objetos detectados.
        
        Args:
            detections: Lista de detecciones YOLO
            
        Returns:
            Diccionario con indicadores geográficos
        """
        indicators = {
            "vehicles": [],
            "urban_elements": [],
            "natural_elements": [],
            "people_indicators": [],
            "transportation": []
        }
        
        # Mapeo de objetos a categorías geográficas
        for detection in detections:
            class_name = detection.get('class_name', '').lower()
            confidence = detection.get('confidence', 0)
            
            # Vehículos (indican tipo de infraestructura)
            if class_name in ['car', 'truck', 'bus', 'motorcycle']:
                indicators["vehicles"].append({
                    'type': class_name,
                    'confidence': confidence
                })
            
            # Elementos urbanos
            elif class_name in ['traffic_light', 'stop_sign', 'bench', 'fire_hydrant']:
                indicators["urban_elements"].append({
                    'type': class_name,
                    'confidence': confidence
                })
            
            # Elementos naturales
            elif class_name in ['bird', 'cat', 'dog', 'horse']:
                indicators["natural_elements"].append({
                    'type': class_name,
                    'confidence': confidence
                })
            
            # Indicadores de personas (densidad, actividad)
            elif class_name == 'person':
                indicators["people_indicators"].append({
                    'confidence': confidence,
                    'area_percentage': detection.get('area_percentage', 0)
                })
            
            # Transporte
            elif class_name in ['bicycle', 'train', 'airplane', 'boat']:
                indicators["transportation"].append({
                    'type': class_name,
                    'confidence': confidence
                })
        
        return indicators 