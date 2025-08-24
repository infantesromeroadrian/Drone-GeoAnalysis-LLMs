#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para VideoProcessor del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad del procesador de video:
- Inicialización y configuración
- Control de procesamiento
- Manejo de threads de manera segura
- Validación de estados y métodos auxiliares
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, Mock
import threading
import time
import queue

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.processors.video_processor import VideoProcessor


class TestVideoProcessor(unittest.TestCase):
    """Tests para la clase VideoProcessor."""
    
    def setUp(self):
        """Configurar tests con datos de prueba."""
        # Crear mock del analizador
        self.mock_analyzer = MagicMock()
        self.mock_analyzer.analyze_image.return_value = {"status": "success", "results": "test"}
        
        # Crear instancia de VideoProcessor
        self.processor = VideoProcessor(analyzer=self.mock_analyzer, analysis_interval=2)
        
        # Datos de prueba
        self.sample_stream_url = "rtmp://test.stream.url/live"
        self.fake_frame_data = b"fake_frame_data_12345"
    
    def tearDown(self):
        """Limpiar después de cada test."""
        # Asegurar que el procesamiento esté detenido
        if self.processor.processing:
            self.processor.stop_processing()
            time.sleep(0.1)  # Dar tiempo para que los threads terminen
    
    def test_video_processor_init_default_interval(self):
        """Test: Inicialización con intervalo de análisis por defecto."""
        processor = VideoProcessor(analyzer=self.mock_analyzer)
        
        self.assertEqual(processor.analysis_interval, 5)
        self.assertEqual(processor.analyzer, self.mock_analyzer)
        self.assertIsNone(processor.stream_url)
        self.assertFalse(processor.processing)
        self.assertIsNone(processor.last_frame)
        self.assertIsNone(processor.last_analysis)
        print("✓ test_video_processor_init_default_interval: EXITOSO")
    
    def test_video_processor_init_custom_interval(self):
        """Test: Inicialización con intervalo personalizado."""
        self.assertEqual(self.processor.analysis_interval, 2)
        self.assertEqual(self.processor.analyzer, self.mock_analyzer)
        self.assertIsNone(self.processor.stream_url)
        self.assertFalse(self.processor.processing)
        print("✓ test_video_processor_init_custom_interval: EXITOSO")
    
    def test_frame_queue_initialization(self):
        """Test: Inicialización correcta de las colas."""
        self.assertIsInstance(self.processor.frame_queue, queue.Queue)
        self.assertIsInstance(self.processor.analysis_queue, queue.Queue)
        
        # Verificar tamaños máximos
        self.assertEqual(self.processor.frame_queue.maxsize, 10)
        self.assertEqual(self.processor.analysis_queue.maxsize, 5)
        print("✓ test_frame_queue_initialization: EXITOSO")
    
    @patch('cv2.VideoCapture')
    def test_initialize_video_capture_success(self, mock_video_capture):
        """Test: Inicialización exitosa de captura de video."""
        # Configurar mock
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_video_capture.return_value = mock_cap
        
        result = self.processor._initialize_video_capture()
        
        self.assertIsNotNone(result)
        mock_video_capture.assert_called_once_with(None)  # stream_url es None inicialmente
        mock_cap.isOpened.assert_called_once()
        print("✓ test_initialize_video_capture_success: EXITOSO")
    
    @patch('cv2.VideoCapture')
    def test_initialize_video_capture_failure(self, mock_video_capture):
        """Test: Fallo en inicialización de captura de video."""
        # Configurar mock para fallar
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        result = self.processor._initialize_video_capture()
        
        self.assertIsNone(result)
        print("✓ test_initialize_video_capture_failure: EXITOSO")
    
    def test_should_process_frame_throttling(self):
        """Test: Lógica de throttling para procesamiento de frames."""
        current_time = time.time()
        
        # Primer frame - debe procesar (diferencia > 0.2s)
        result1 = self.processor._should_process_frame(current_time, current_time - 0.3)
        self.assertTrue(result1)
        
        # Segundo frame muy reciente - no debe procesar (diferencia < 0.2s)
        result2 = self.processor._should_process_frame(current_time, current_time - 0.1)
        self.assertFalse(result2)
        
        print("✓ test_should_process_frame_throttling: EXITOSO")
    
    def test_should_analyze_frame_interval(self):
        """Test: Lógica de intervalo para análisis de frames."""
        current_time = time.time()
        
        # Primer análisis - debe analizar (diferencia > analysis_interval)
        result1 = self.processor._should_analyze_frame(current_time, current_time - 3)
        self.assertTrue(result1)  # 3s > 2s (analysis_interval)
        
        # Análisis muy reciente - no debe analizar
        result2 = self.processor._should_analyze_frame(current_time, current_time - 1)
        self.assertFalse(result2)  # 1s < 2s (analysis_interval)
        
        print("✓ test_should_analyze_frame_interval: EXITOSO")
    
    @patch('cv2.imencode')
    def test_process_captured_frame(self, mock_imencode):
        """Test: Procesamiento de frame capturado."""
        # Configurar mock
        mock_buffer = MagicMock()
        mock_buffer.tobytes.return_value = self.fake_frame_data
        mock_imencode.return_value = (True, mock_buffer)
        
        # Simular frame (numpy array)
        import numpy as np
        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Procesar frame
        self.processor._process_captured_frame(fake_frame)
        
        # Verificar que se actualizó last_frame
        self.assertEqual(self.processor.last_frame, self.fake_frame_data)
        mock_imencode.assert_called_once_with('.jpg', fake_frame)
        print("✓ test_process_captured_frame: EXITOSO")
    
    def test_get_latest_frame_empty_queue(self):
        """Test: Obtener frame más reciente de cola vacía."""
        result = self.processor._get_latest_frame()
        
        self.assertIsNone(result)
        print("✓ test_get_latest_frame_empty_queue: EXITOSO")
    
    def test_get_latest_frame_with_data(self):
        """Test: Obtener frame más reciente de cola con datos."""
        # Agregar frames a la cola
        self.processor.frame_queue.put(b"frame1")
        self.processor.frame_queue.put(b"frame2")
        self.processor.frame_queue.put(b"frame3")
        
        # Obtener el más reciente
        result = self.processor._get_latest_frame()
        
        # Debe devolver el último frame
        self.assertEqual(result, b"frame3")
        
        # La cola debe quedar vacía
        self.assertTrue(self.processor.frame_queue.empty())
        print("✓ test_get_latest_frame_with_data: EXITOSO")
    
    def test_prepare_analysis_data(self):
        """Test: Preparación de datos para análisis."""
        current_time = time.time()
        
        result = self.processor._prepare_analysis_data(self.fake_frame_data, current_time)
        
        self.assertIn("base64_image", result)
        self.assertIn("metadata", result)
        
        # Verificar metadatos
        metadata = result["metadata"]
        self.assertEqual(metadata["source"], "drone_stream")
        self.assertEqual(metadata["timestamp"], current_time)
        self.assertEqual(metadata["format"], "JPEG")
        self.assertEqual(metadata["dimensions"], (640, 480))
        
        print("✓ test_prepare_analysis_data: EXITOSO")
    
    def test_execute_image_analysis(self):
        """Test: Ejecución de análisis de imagen."""
        analysis_data = {
            "base64_image": "fake_base64_data",
            "metadata": {"timestamp": time.time()}
        }
        
        result = self.processor._execute_image_analysis(analysis_data)
        
        # Verificar que se llamó al analizador
        self.mock_analyzer.analyze_image.assert_called_once_with(
            "fake_base64_data", analysis_data["metadata"], 'jpeg'
        )
        
        # Verificar resultado
        self.assertEqual(result["status"], "success")
        print("✓ test_execute_image_analysis: EXITOSO")
    
    def test_process_analysis_results(self):
        """Test: Procesamiento de resultados de análisis."""
        results = {"analysis": "test_results", "confidence": 0.95}
        current_time = time.time()
        
        self.processor._process_analysis_results(results, current_time, self.fake_frame_data)
        
        # Verificar que se actualizó last_analysis
        self.assertEqual(self.processor.last_analysis, results)
        
        # Verificar que se agregó a la cola de análisis si no está llena
        if not self.processor.analysis_queue.full():
            analysis_item = self.processor.analysis_queue.get_nowait()
            self.assertEqual(analysis_item["results"], results)
            self.assertEqual(analysis_item["timestamp"], current_time)
            self.assertEqual(analysis_item["frame"], self.fake_frame_data)
        
        print("✓ test_process_analysis_results: EXITOSO")
    
    def test_get_last_frame_none(self):
        """Test: Obtener último frame cuando no hay ninguno."""
        result = self.processor.get_last_frame()
        
        self.assertIsNone(result)
        print("✓ test_get_last_frame_none: EXITOSO")
    
    def test_get_last_frame_with_data(self):
        """Test: Obtener último frame cuando hay datos."""
        self.processor.last_frame = self.fake_frame_data
        
        result = self.processor.get_last_frame()
        
        self.assertEqual(result, self.fake_frame_data)
        print("✓ test_get_last_frame_with_data: EXITOSO")
    
    def test_get_last_analysis_none(self):
        """Test: Obtener último análisis cuando no hay ninguno."""
        result = self.processor.get_last_analysis()
        
        self.assertIsNone(result)
        print("✓ test_get_last_analysis_none: EXITOSO")
    
    def test_get_last_analysis_with_data(self):
        """Test: Obtener último análisis cuando hay datos."""
        test_analysis = {"result": "test_analysis", "timestamp": time.time()}
        self.processor.last_analysis = test_analysis
        
        result = self.processor.get_last_analysis()
        
        self.assertEqual(result, test_analysis)
        print("✓ test_get_last_analysis_with_data: EXITOSO")
    
    def test_stop_processing_when_not_processing(self):
        """Test: Detener procesamiento cuando no está activo."""
        # Asegurar que no está procesando
        self.processor.processing = False
        
        result = self.processor.stop_processing()
        
        self.assertTrue(result)
        self.assertFalse(self.processor.processing)
        print("✓ test_stop_processing_when_not_processing: EXITOSO")
    
    def test_handle_capture_error(self):
        """Test: Manejo de errores en captura de frames."""
        # Este método solo hace logging y sleep, no retorna nada
        # Testeamos que no genere excepciones
        try:
            with patch('time.sleep') as mock_sleep:
                self.processor._handle_capture_error()
                mock_sleep.assert_called_once_with(0.5)
            print("✓ test_handle_capture_error: EXITOSO")
        except Exception as e:
            self.fail(f"_handle_capture_error raised exception: {e}")


if __name__ == '__main__':
    print("🧪 EJECUTANDO TESTS DE VIDEO PROCESSOR")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestVideoProcessor)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE VIDEO PROCESSOR:")
    print(f"   Tests ejecutados: {total_tests}")
    print(f"   Exitosos: {passed}")
    print(f"   Fallidos: {failures}")
    print(f"   Errores: {errors}")
    print(f"   Tasa de éxito: {(passed/total_tests)*100:.1f}%")
    
    if failures > 0 or errors > 0:
        print(f"\n❌ FALLOS DETECTADOS:")
        for failure in result.failures:
            print(f"   • {failure[0]}")
        for error in result.errors:
            print(f"   • {error[0]}")
    else:
        print(f"\n🎉 ¡TODOS LOS TESTS DE VIDEO PROCESSOR PASAN! 🎉") 