# Sistema de Testing para Módulo /models

## 📋 Descripción

Este directorio contiene el sistema de testing para el módulo `/models` del proyecto **Drone Geo Analysis**. Los tests están diseñados para identificar exactamente qué función falla cuando hay problemas en los componentes de análisis de IA y planificación de misiones.

## 🗂️ Estructura del Directorio

```
tests/models_test/
├── __init__.py                    # Inicialización del módulo
├── test_mission_models.py         # Tests para modelos de datos (dataclasses)
├── test_mission_utils.py          # Tests para utilidades matemáticas y geográficas
├── test_mission_parser.py         # Tests para parser de respuestas JSON
├── test_mission_validator.py      # Tests para validador de seguridad
├── test_geo_manager.py            # Tests para gestor de geolocalización
├── run_models_tests.py            # Script ejecutor principal
└── README.md                     # Esta documentación
```

## 🧪 Componentes Testeados

### 1. MissionModels (test_mission_models.py)
**Funciones principales testeadas:**
- `Waypoint`: Creación de waypoints con parámetros completos y defaults
- `MissionArea`: Creación de áreas de misión con boundaries y POIs
- `MissionMetadata`: Metadatos de misiones con tracking
- Verificación de dataclass fields y funcionalidad

**Total**: 7 tests que cubren modelos de datos básicos.

### 2. MissionUtils (test_mission_utils.py)
**Funciones principales testeadas:**
- `calculate_distance`: Cálculo de distancia haversine entre puntos GPS
- `calculate_area_center`: Cálculo del centro geográfico de áreas
- `calculate_total_mission_distance`: Distancia total de misión
- `estimate_flight_time`: Estimación de tiempo de vuelo
- `is_point_in_boundaries`: Verificación de punto dentro de límites

**Total**: 15 tests que cubren funciones matemáticas y geográficas.

### 3. MissionParser (test_mission_parser.py)
**Funciones principales testeadas:**
- `extract_json_from_response`: Extracción robusta de JSON desde respuestas LLM
- Parseo directo, desde markdown, con regex
- Manejo de casos de error y JSON malformado
- Extracción de múltiples bloques JSON

**Total**: 12 tests que cubren parsing robusto de respuestas.

### 4. MissionValidator (test_mission_validator.py)
**Funciones principales testeadas:**
- `validate_mission_safety`: Validación completa de seguridad
- `validate_mission_duration`: Validación de duración de misión
- Validaciones de altitud, distancia y coordenadas
- Detección de waypoints peligrosos

**Total**: 13 tests que cubren validación de seguridad.

### 5. GeolocationManager (test_geo_manager.py)
**Funciones principales testeadas:**
- `add_reference_image`: Agregar imágenes de referencia
- `create_target`: Crear objetivos para triangulación
- `get_reference_images`: Obtener imágenes de referencia
- `get_targets`: Obtener objetivos
- Gestión de estado de geolocalización

**Total**: 12 tests que cubren gestión de geolocalización.

## 🚀 Comandos de Ejecución

### En Docker (Recomendado)
```bash
# Ejecutar todos los tests de models
docker-compose exec drone-geo-app python tests/models_test/run_models_tests.py

# Ejecutar solo tests de modelos de datos
docker-compose exec drone-geo-app python tests/models_test/run_models_tests.py mission_models

# Ejecutar solo tests de utilidades
docker-compose exec drone-geo-app python tests/models_test/run_models_tests.py mission_utils

# Ejecutar solo tests de parser
docker-compose exec drone-geo-app python tests/models_test/run_models_tests.py mission_parser

# Ejecutar solo tests de validador
docker-compose exec drone-geo-app python tests/models_test/run_models_tests.py mission_validator

# Ejecutar solo tests de geo manager
docker-compose exec drone-geo-app python tests/models_test/run_models_tests.py geo_manager
```

### Ejecución Local
```bash
# Ejecutar todos los tests
python tests/models_test/run_models_tests.py

# Tests individuales
python tests/models_test/test_mission_models.py
python tests/models_test/test_mission_utils.py
python tests/models_test/test_mission_parser.py
python tests/models_test/test_mission_validator.py
python tests/models_test/test_geo_manager.py
```

## 📊 Ejemplo de Salida

### Salida Exitosa
```
🤖 SISTEMA DE TESTING DE MODELS
============================================================
✓ mission_models: 7/7 tests exitosos (100.0%)
✓ mission_utils: 15/15 tests exitosos (100.0%)
✓ mission_parser: 12/12 tests exitosos (100.0%)
✓ mission_validator: 13/13 tests exitosos (100.0%)
✓ geo_manager: 12/12 tests exitosos (100.0%)

📈 ESTADÍSTICAS:
   Total de archivos: 5
   Exitosos: 5 (100%)
   Fallidos: 0
   Tasa de éxito: 100.0%

🎉 ¡TODOS LOS TESTS DE MODELS PASAN! 🎉
```

## 🔧 Configuración de Tests

### Datos de Prueba
Los tests utilizan datos de muestra realistas:
- **Coordenadas GPS**: Nueva York (40.7128, -74.0060)
- **Waypoints**: Secuencias lógicas de navegación
- **Misiones**: Estructuras JSON completas
- **Telemetría**: Datos simulados de drones

### Casos de Test Cubiertos

**✅ Casos de Éxito:**
- Creación correcta de modelos de datos
- Cálculos matemáticos precisos
- Parsing robusto de JSON
- Validaciones de seguridad exitosas
- Gestión correcta de referencias

**❌ Casos de Error:**
- Coordenadas inválidas
- JSON malformado
- Altitudes peligrosas
- Distancias excesivas
- Duraciones excesivas

**🔄 Edge Cases:**
- Valores límite en coordenadas
- Misiones sin waypoints
- Áreas sin boundaries
- Parsing de múltiples JSON
- Validaciones complejas

## 🛠️ Troubleshooting

### Problemas Comunes

1. **ImportError: No module named 'src.models'**
   ```bash
   cd /path/to/Drone-Geo-Analysis
   python tests/models_test/run_models_tests.py
   ```

2. **ModuleNotFoundError: No module named 'dataclasses'**
   ```bash
   # Usar Docker (recomendado)
   docker-compose exec drone-geo-app python tests/models_test/run_models_tests.py
   ```

3. **Tests fallan con errores de parsing JSON**
   - Verificar estructura de respuestas simuladas
   - Comprobar formato de JSON de prueba

4. **Errores de cálculo geográfico**
   - Verificar instalación de bibliotecas matemáticas
   - Comprobar precisión de cálculos trigonométricos

## 📈 Métricas de Calidad

### Cobertura de Código
- **MissionModels**: ~100% de funciones cubiertas
- **MissionUtils**: ~95% de funciones cubiertas
- **MissionParser**: ~90% de casos cubiertos
- **MissionValidator**: ~85% de validaciones cubiertas
- **GeolocationManager**: ~100% de funciones cubiertas

### Tipos de Validación
- ✅ **Unit Testing**: Tests unitarios aislados
- ✅ **Data Validation**: Verificación de estructuras de datos
- ✅ **Mathematical Testing**: Validación de cálculos geográficos
- ✅ **Error Handling**: Manejo robusto de errores
- ✅ **Security Testing**: Validaciones de seguridad

## 🔄 Componentes No Incluidos (Pendientes)

Los siguientes componentes requieren configuración adicional:
- **GeoAnalyzer**: Requiere configuración de OpenAI API
- **MissionPlanner**: Requiere configuración completa de LLM

Estos se pueden agregar cuando se configure el entorno completo de APIs externas.

## 📞 Soporte

Si encuentras problemas con los tests:
1. Verificar que el entorno Docker esté funcionando
2. Comprobar que todas las dependencias estén instaladas
3. Revisar logs de error detallados
4. Consultar documentación individual de cada módulo

---

**Última actualización**: 2024-01-XX  
**Mantenido por**: Drone Geo Analysis Testing Team 