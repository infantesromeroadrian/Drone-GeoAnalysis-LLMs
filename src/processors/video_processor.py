#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Procesador de video en tiempo real desde drones.
"""

import cv2
import numpy as np
import threading
import time
import queue
import logging
import base64
from typing import Dict, Any, Optional, List, Tuple

from src.models.geo_analyzer import GeoAnalyzer

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Procesador de video en tiempo real desde drones."""
    
    def __init__(self, analyzer: GeoAnalyzer, analysis_interval: int = 5):
        """
        Inicializa el procesador de video.
        
        Args:
            analyzer: Instancia del analizador geográfico
            analysis_interval: Intervalo entre análisis en segundos
        """
        self.analyzer = analyzer
        self.analysis_interval = analysis_interval
        self.stream_url = None
        self.processing = False
        self.last_frame = None
        self.last_analysis = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.analysis_queue = queue.Queue(maxsize=5)
        self.capture_thread = None
        self.analysis_thread = None
        logger.info("Procesador de video inicializado")
    
    def start_processing(self, stream_url: str) -> bool:
        """
        Inicia el procesamiento del stream de video.
        
        Args:
            stream_url: URL del stream de video
            
        Returns:
            True si se inició correctamente, False en caso contrario
        """
        try:
            self.stream_url = stream_url
            self.processing = True
            
            # Iniciar threads de procesamiento
            self._start_capture_thread()
            self._start_analysis_thread()
            
            logger.info(f"Procesamiento de video iniciado para: {stream_url}")
            return True
        except Exception as e:
            logger.error(f"Error al iniciar procesamiento de video: {str(e)}")
            return False
    
    def _start_capture_thread(self) -> None:
        """Inicia el thread de captura de frames."""
        self.capture_thread = threading.Thread(target=self._capture_frames)
        self.capture_thread.daemon = True
        self.capture_thread.start()
    
    def _start_analysis_thread(self) -> None:
        """Inicia el thread de análisis de frames."""
        self.analysis_thread = threading.Thread(target=self._analyze_frames)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
    
    def stop_processing(self) -> bool:
        """
        Detiene el procesamiento del stream de video.
        
        Returns:
            True si se detuvo correctamente
        """
        self.processing = False
        self._stop_threads()
        
        logger.info("Procesamiento de video detenido")
        return True
    
    def _stop_threads(self) -> None:
        """Detiene los threads de procesamiento."""
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.analysis_thread:
            self.analysis_thread.join(timeout=2.0)
    
    def get_last_frame(self) -> Optional[bytes]:
        """
        Obtiene el último frame capturado.
        
        Returns:
            Último frame en formato JPEG o None
        """
        return self.last_frame
    
    def get_last_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene el último análisis realizado.
        
        Returns:
            Diccionario con los resultados del análisis o None
        """
        return self.last_analysis
    
    def _capture_frames(self):
        """Thread para capturar frames del stream de video."""
        try:
            # Inicializar captura de video
            cap = self._initialize_video_capture()
            if cap is None:
                return
            
            # Bucle principal de captura
            self._run_capture_loop(cap)
            
            # Liberar recursos
            cap.release()
        except Exception as e:
            logger.error(f"Error en thread de captura: {str(e)}")
    
    def _initialize_video_capture(self) -> Optional[cv2.VideoCapture]:
        """Inicializa la captura de video."""
        cap = cv2.VideoCapture(self.stream_url)
        if not cap.isOpened():
            logger.error(f"No se pudo abrir el stream: {self.stream_url}")
            return None
        return cap
    
    def _run_capture_loop(self, cap: cv2.VideoCapture) -> None:
        """Ejecuta el bucle principal de captura de frames."""
        last_frame_time = 0
        
        while self.processing:
            ret, frame = cap.read()
            if not ret:
                self._handle_capture_error()
                continue
            
            # Procesar frame con throttling
            current_time = time.time()
            if self._should_process_frame(current_time, last_frame_time):
                self._process_captured_frame(frame)
                last_frame_time = current_time
    
    def _handle_capture_error(self) -> None:
        """Maneja errores en la captura de frames."""
        logger.warning("Error al leer frame, reintentando...")
        time.sleep(0.5)
    
    def _should_process_frame(self, current_time: float, last_frame_time: float) -> bool:
        """Determina si debe procesar el frame basado en throttling."""
        return current_time - last_frame_time > 0.2  # Procesar solo cada 200ms
                
    def _process_captured_frame(self, frame: np.ndarray) -> None:
        """Procesa un frame capturado."""
        # Convertir frame a JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        jpeg_bytes = buffer.tobytes()
        
        # Actualizar último frame
        self.last_frame = jpeg_bytes
        
        # Añadir a la cola para análisis si hay espacio
        if not self.frame_queue.full():
            self.frame_queue.put(jpeg_bytes)
    
    def _analyze_frames(self):
        """Thread para analizar frames periódicamente."""
        last_analysis_time = 0
        
        while self.processing:
            current_time = time.time()
            
            # Analizar solo en el intervalo especificado
            if self._should_analyze_frame(current_time, last_analysis_time):
                self._perform_frame_analysis(current_time)
                last_analysis_time = current_time
            
            time.sleep(0.1)  # Evitar uso excesivo de CPU
    
    def _should_analyze_frame(self, current_time: float, last_analysis_time: float) -> bool:
        """Determina si debe analizar el frame basado en el intervalo."""
        return current_time - last_analysis_time > self.analysis_interval
    
    def _perform_frame_analysis(self, current_time: float) -> None:
        """Realiza el análisis de un frame."""
        try:
            # Obtener frame más reciente
            frame = self._get_latest_frame()
            if frame is None:
                time.sleep(0.5)
                return
            
            # Preparar datos para análisis
            analysis_data = self._prepare_analysis_data(frame, current_time)
            
            # Ejecutar análisis
            results = self._execute_image_analysis(analysis_data)
            
            # Procesar resultados
            self._process_analysis_results(results, current_time, frame)
            
        except Exception as e:
            logger.error(f"Error en análisis de frame: {str(e)}")
            time.sleep(1.0)  # Esperar un poco antes de reintentar
    
    def _get_latest_frame(self) -> Optional[bytes]:
        """Obtiene el frame más reciente de la cola."""
        frame = None
        while not self.frame_queue.empty():
            frame = self.frame_queue.get()
        return frame
    
    def _prepare_analysis_data(self, frame: bytes, current_time: float) -> Dict[str, Any]:
        """Prepara los datos para el análisis de imagen."""
        # Convertir frame a base64 para el análisis
        base64_image = base64.b64encode(frame).decode('utf-8')
        
        # Crear metadatos
        metadata = {
            "source": "drone_stream",
            "timestamp": current_time,
            "format": "JPEG",
            "dimensions": (640, 480)  # Tamaño aproximado
        }
        
        return {"base64_image": base64_image, "metadata": metadata}
    
    def _execute_image_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta el análisis de imagen usando el analizador."""
        return self.analyzer.analyze_image(
            analysis_data["base64_image"], 
            analysis_data["metadata"], 
            'jpeg'
        )
    
    def _process_analysis_results(self, results: Dict[str, Any], 
                                current_time: float, frame: bytes) -> None:
        """Procesa los resultados del análisis."""
        # Actualizar último análisis
        self.last_analysis = results
        
        # Añadir a la cola de análisis si hay espacio
        if not self.analysis_queue.full():
            self.analysis_queue.put({
                "timestamp": current_time,
                "results": results,
                "frame": frame
            })
        
        logger.info("Análisis de frame completado")