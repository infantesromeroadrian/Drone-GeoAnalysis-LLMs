# Sistema de Testing - Módulo Processors

Este directorio contiene el sistema completo de testing para el módulo `/processors` del proyecto Drone Geo Analysis.

## 📋 Contenido

### Archivos de Test
- `test_change_detector.py` - Tests para la clase ChangeDetector (20 tests)
- `test_video_processor.py` - Tests para la clase VideoProcessor (18 tests)
- `run_processors_tests.py` - Script ejecutor principal con estadísticas

### Componentes Testeados

#### 🔍 ChangeDetector
- **Inicialización y configuración**: Sensibilidad, diccionarios internos
- **Generación de IDs**: Precisión en coordenadas geográficas
- **Validación de referencias**: Existencia de imágenes de referencia
- **Procesamiento de imágenes**: Mocking de OpenCV para evitar dependencias
- **Métricas de cambio**: Cálculos de porcentajes y detección de cambios significativos
- **Gestión de imágenes**: Almacenamiento, recuperación y eliminación

#### 🎥 VideoProcessor
- **Inicialización y configuración**: Intervalos de análisis, colas de datos
- **Control de procesamiento**: Estados de inicio y parada
- **Threading seguro**: Validación de lógica sin threads reales
- **Throttling**: Control de frecuencia de procesamiento
- **Análisis de frames**: Preparación de datos y ejecución de análisis
- **Manejo de colas**: Frames y resultados de análisis

## 🚀 Ejecución de Tests

### Todos los Tests
```bash
# Desde el contenedor Docker
docker-compose exec drone-geo-app python tests/processors_test/run_processors_tests.py

# Desde el sistema local
python tests/processors_test/run_processors_tests.py
```

### Tests Específicos
```bash
# Solo ChangeDetector
docker-compose exec drone-geo-app python tests/processors_test/run_processors_tests.py change_detector

# Solo VideoProcessor
docker-compose exec drone-geo-app python tests/processors_test/run_processors_tests.py video_processor
```

### Tests Individuales
```bash
# Test directo de un módulo
docker-compose exec drone-geo-app python tests/processors_test/test_change_detector.py
docker-compose exec drone-geo-app python tests/processors_test/test_video_processor.py
```

## 📊 Salida Esperada

### Ejecución Exitosa Completa
```
🎬 SISTEMA DE TESTING DE PROCESSORS
============================================================

🔧 Ejecutando tests de change_detector...
✓ change_detector: 20/20 tests exitosos (100.0%)

🔧 Ejecutando tests de video_processor...
✓ video_processor: 18/18 tests exitosos (100.0%)

📈 ESTADÍSTICAS FINALES:
   Total archivos: 2
   Total tests: 38
   Exitosos: 38
   Fallidos: 0
   Errores: 0
   Tasa de éxito: 100.0%
   Tiempo total: 0.45s

🎉 ¡TODOS LOS TESTS DE PROCESSORS PASAN! 🎉
```

### Ejecución Específica
```
🎬 EJECUTANDO TESTS DE CHANGE_DETECTOR
============================================================
✓ change_detector: 20/20 tests exitosos (100.0%)
   ⏱️  Tiempo: 0.23s
```

## 🔧 Configuración Técnica

### Dependencias Principales
```python
import unittest
from unittest.mock import patch, MagicMock, Mock
import numpy as np
import cv2  # Mockeado para evitar dependencias
import threading
import queue
import time
```

### Mocking Strategy
- **OpenCV (cv2)**: Completamente mockeado para evitar dependencias de sistema
- **Threading**: Tests de lógica sin threads reales para evitar problemas de timing
- **GeoAnalyzer**: Mock del analizador geográfico para tests aislados
- **VideoCapture**: Simulación de captura de video sin hardware real

## 🧪 Estrategia de Testing

### ChangeDetector Tests
1. **Inicialización**: Configuraciones por defecto y personalizadas
2. **IDs de ubicación**: Generación y precisión de coordenadas
3. **Validación**: Existencia y gestión de referencias
4. **Métricas**: Cálculos de porcentajes de cambio
5. **Gestión**: CRUD de imágenes de referencia

### VideoProcessor Tests
1. **Configuración**: Intervalos y inicialización de componentes
2. **Control**: Estados de procesamiento
3. **Throttling**: Lógica de control de frecuencia
4. **Análisis**: Preparación y ejecución de análisis de frames
5. **Colas**: Manejo de datos de frames y resultados

## 🎯 Identificación de Errores

### Tipos de Errores Detectados
- **Fallos de inicialización**: Configuraciones incorrectas
- **Errores de validación**: Referencias inexistentes
- **Problemas de threading**: Estados inconsistentes
- **Errores de procesamiento**: Fallos en análisis
- **Problemas de memoria**: Gestión incorrecta de colas

### Debugging
```python
# Ejemplo de salida de error
❌ FALLOS DETECTADOS:
   • test_change_detector_init_default: AssertionError en línea 45
   • test_process_captured_frame: Mock no llamado correctamente
```

## 📁 Estructura de Archivos

```
tests/processors_test/
├── __init__.py                    # Inicialización del módulo
├── test_change_detector.py       # 20 tests para ChangeDetector
├── test_video_processor.py       # 18 tests para VideoProcessor  
├── run_processors_tests.py       # Script ejecutor principal
└── README.md                     # Esta documentación
```

## ⚠️ Limitaciones Conocidas

### Mocking de Dependencias
- Los tests no verifican funcionalidad real de OpenCV
- Threading se testea solo a nivel lógico, no concurrencia real
- Análisis de imágenes simulado sin procesamiento real

### Casos No Cubiertos
- Performance con videos de alta resolución
- Comportamiento con streams de red reales
- Manejo de memoria con datasets grandes
- Integración completa con sistema de archivos

## 🔄 Mantenimiento

### Agregar Nuevos Tests
1. Añadir método `test_*` en la clase correspondiente
2. Seguir el patrón de naming: `test_componente_caso_esperado`
3. Incluir `print("✓ test_name: EXITOSO")` al final
4. Actualizar contador de tests en este README

### Modificar Tests Existentes
1. Mantener compatibilidad con el formato de salida
2. Preservar el patrón de mocking para dependencias externas
3. Actualizar documentación si cambia la funcionalidad

## 🏆 Métricas de Calidad
- **Cobertura**: 38+ tests individuales
- **Éxito esperado**: 100% en sistema funcional
- **Tiempo ejecución**: < 1 segundo total
- **Aislamiento**: Tests independientes sin dependencias externas 