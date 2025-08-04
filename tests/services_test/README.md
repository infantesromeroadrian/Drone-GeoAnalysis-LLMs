# Sistema de Testing - Módulo Services

Este directorio contiene el sistema completo de testing para el módulo `/services` del proyecto Drone Geo Analysis.

## 📋 Contenido

### Archivos de Test
- `test_analysis_service.py` - Tests para AnalysisService (18+ tests)
- `test_drone_service.py` - Tests para DroneService (29+ tests)  
- `test_geo_service.py` - Tests para GeoService (30+ tests)
- `test_mission_service.py` - Tests para MissionService (26+ tests)
- `run_services_tests.py` - Script ejecutor principal con estadísticas avanzadas

### Servicios Testeados

#### 🔬 AnalysisService
- **Análisis de imágenes**: Procesamiento y codificación base64
- **Gestión de metadatos**: Combinación de datos de imagen y configuración
- **Filtros de confianza**: Validación de umbrales y advertencias
- **Manejo de archivos**: Guardado temporal y resultados
- **Servicios de archivos**: Servir resultados guardados
- **Estados de análisis**: Tracking de progreso

#### 🚁 DroneService  
- **Conexión y control**: Estados de conexión y desconexión
- **Operaciones de vuelo**: Despegue, aterrizaje con validación de altitud
- **Streaming de video**: Inicio y parada de transmisión
- **Telemetría**: Obtención de datos de sensores
- **Simulaciones**: Rutas predefinidas y gestión de simulaciones
- **Validación de seguridad**: Límites de altitud y posición

#### 🌍 GeoService
- **Triangulación**: Real y simulada con observaciones múltiples
- **Detección de cambios**: Correlación real y mock  
- **Gestión de objetivos**: Creación, seguimiento y estados
- **Imágenes de referencia**: Agregado y validación
- **Observaciones**: Manejo manual y automático
- **Cálculos geográficos**: Posicionamiento y precisión

#### 🎯 MissionService
- **Misiones LLM**: Creación con comandos naturales
- **Control adaptativo**: Decisiones basadas en situación
- **Cartografía**: Carga y validación de archivos GeoJSON
- **Gestión de áreas**: Tracking de áreas cargadas
- **Validación de seguridad**: Warnings y verificaciones
- **Misiones básicas**: Gestión de misiones predefinidas

## 🚀 Ejecución de Tests

### Todos los Tests
```bash
# Desde el contenedor Docker
docker-compose exec drone-geo-app python tests/services_test/run_services_tests.py

# Desde el sistema local
python tests/services_test/run_services_tests.py
```

### Tests por Servicio
```bash
# AnalysisService
docker-compose exec drone-geo-app python tests/services_test/run_services_tests.py analysis_service

# DroneService
docker-compose exec drone-geo-app python tests/services_test/run_services_tests.py drone_service

# GeoService  
docker-compose exec drone-geo-app python tests/services_test/run_services_tests.py geo_service

# MissionService
docker-compose exec drone-geo-app python tests/services_test/run_services_tests.py mission_service
```

### Tests Individuales
```bash
# Test directo de un servicio
docker-compose exec drone-geo-app python tests/services_test/test_analysis_service.py
docker-compose exec drone-geo-app python tests/services_test/test_drone_service.py
docker-compose exec drone-geo-app python tests/services_test/test_geo_service.py
docker-compose exec drone-geo-app python tests/services_test/test_mission_service.py
```

## 📊 Salida Esperada

### Ejecución Exitosa Completa
```
🔧 SISTEMA DE TESTING DE SERVICES
============================================================

🔬 Ejecutando tests de analysis_service...
✓ analysis_service: 18/18 tests exitosos (100.0%)

🚁 Ejecutando tests de drone_service...
✓ drone_service: 29/29 tests exitosos (100.0%)

🌍 Ejecutando tests de geo_service...
✓ geo_service: 30/30 tests exitosos (100.0%)

🎯 Ejecutando tests de mission_service...
✓ mission_service: 26/26 tests exitosos (100.0%)

📈 ESTADÍSTICAS FINALES:
   Total servicios: 4
   Total tests: 103
   Exitosos: 103
   Fallidos: 0
   Errores: 0
   Tasa de éxito: 100.0%
   Tiempo total: 1.23s
   Promedio por servicio: 0.31s

🎉 ¡TODOS LOS TESTS DE SERVICES PASAN! 🎉

🏆 RANKING DE SERVICIOS:
   🥇 🌍 geo_service: 100.0% (30 tests)
   🥈 🚁 drone_service: 100.0% (29 tests)
   🥉 🎯 mission_service: 100.0% (26 tests)
   4️⃣ 🔬 analysis_service: 100.0% (18 tests)
```

### Ejecución Específica
```
🔬 EJECUTANDO TESTS DE ANALYSIS SERVICE
============================================================
✓ analysis_service: 18/18 tests exitosos (100.0%)
   ⏱️  Tiempo: 0.28s
```

## 🔧 Configuración Técnica

### Dependencias Principales
```python
import unittest
from unittest.mock import patch, MagicMock, Mock, mock_open
import tempfile
import json
from datetime import datetime
import time
from typing import Dict, Any
```

### Estrategia de Mocking
- **Componentes externos**: Todos los servicios dependientes mockeados
- **Sistema de archivos**: Mock de operaciones de E/S
- **APIs externas**: Simulación de respuestas de LLM y análisis
- **Threading**: Lógica sin concurrencia real para estabilidad
- **Flask objects**: Mock de archivos y requests

## 🧪 Estrategia de Testing

### AnalysisService Tests
1. **Inicialización**: Configuración de analizador
2. **Procesamiento**: Guardado temporal y metadatos
3. **Codificación**: Base64 con fallbacks
4. **Filtros**: Umbrales de confianza
5. **Resultados**: Guardado y servido de archivos

### DroneService Tests  
1. **Conexión**: Estados y errores de conexión
2. **Vuelo**: Validación de altitud y operaciones
3. **Video**: Streaming y control de procesador
4. **Telemetría**: Obtención de datos de sensores
5. **Simulación**: Rutas y gestión de simulaciones

### GeoService Tests
1. **Triangulación**: Real vs mock, observaciones múltiples
2. **Detección**: Cambios con correlación
3. **Objetivos**: Creación y seguimiento
4. **Referencias**: Gestión de imágenes
5. **Estados**: Tracking de progreso

### MissionService Tests
1. **LLM**: Creación y validación de misiones
2. **Control**: Adaptación basada en situación
3. **Archivos**: Carga y validación de cartografía
4. **Áreas**: Gestión de regiones cargadas
5. **Seguridad**: Validaciones y warnings

## 🎯 Identificación de Errores

### Tipos de Errores Detectados
- **Fallos de inicialización**: Dependencias incorrectas
- **Errores de validación**: Parámetros inválidos
- **Problemas de E/O**: Archivos y streams
- **Errores de lógica**: Algoritmos y cálculos
- **Problemas de integración**: Comunicación entre servicios

### Debugging Avanzado
```python
# Ejemplo de salida de error detallada
❌ FALLOS DETECTADOS:
   • test_analyze_image_encode_error: AssertionError en línea 156
   • test_upload_cartography_html_content: Mock no configurado correctamente
```

## 📁 Estructura de Archivos

```
tests/services_test/
├── __init__.py                     # Inicialización del módulo
├── test_analysis_service.py        # 18+ tests para AnalysisService
├── test_drone_service.py           # 29+ tests para DroneService
├── test_geo_service.py             # 30+ tests para GeoService  
├── test_mission_service.py         # 26+ tests para MissionService
├── run_services_tests.py           # Script ejecutor principal
└── README.md                       # Esta documentación
```

## ⚠️ Limitaciones Conocidas

### Mocking de Dependencias
- Los tests no verifican funcionalidad real de APIs externas
- LLM interactions completamente simuladas
- Análisis de imágenes sin procesamiento real
- Threading testeado solo a nivel lógico

### Casos No Cubiertos  
- Performance con datasets grandes
- Integración completa con sistemas reales
- Comportamiento con APIs externas lentas
- Manejo de memoria con misiones complejas

## 🔄 Mantenimiento

### Agregar Nuevos Tests
1. Añadir método `test_*` en la clase correspondiente
2. Seguir el patrón de naming: `test_servicio_caso_esperado`
3. Incluir `print("✓ test_name: EXITOSO")` al final
4. Actualizar contador de tests en este README

### Modificar Tests Existentes
1. Mantener compatibilidad con el formato de salida
2. Preservar el patrón de mocking para dependencias externas
3. Actualizar documentación si cambia la funcionalidad

## 🏆 Características Avanzadas

### Sistema de Ranking
- Clasificación automática por tasa de éxito
- Distribución de tests por servicio
- Métricas de tiempo de ejecución
- Comparación entre servicios

### Estadísticas Detalladas
- **Total tests**: 103+ tests individuales
- **Cobertura**: 4 servicios completos
- **Tiempo promedio**: < 0.5s por servicio
- **Precisión**: Identificación exacta de fallos

### Modos de Ejecución
- **Completo**: Todos los servicios con ranking
- **Específico**: Servicio individual con detalles
- **Individual**: Test directo con output inmediato
- **Ayuda**: Documentación integrada

## 🚀 Métricas de Calidad
- **Cobertura**: 103+ tests individuales
- **Éxito esperado**: 100% en sistema funcional
- **Tiempo ejecución**: < 2 segundos total
- **Aislamiento**: Tests independientes sin dependencias externas
- **Precisión**: Identificación exacta de funciones que fallan
