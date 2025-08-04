# 🧪 Sistema de Testing de Controladores

Este directorio contiene tests específicos para cada controlador del proyecto Drone Geo Analysis. El sistema permite identificar exactamente qué función o clase falla cuando hay problemas.

## 📁 Estructura

```
tests/controllers_test/
├── __init__.py                      # Inicialización del módulo
├── README.md                        # Esta documentación
├── run_controller_tests.py          # Script principal de ejecución
├── test_analysis_controller.py      # Tests para analysis_controller.py
├── test_drone_controller.py         # Tests para drone_controller.py
├── test_geo_controller.py           # Tests para geo_controller.py
└── test_mission_controller.py       # Tests para mission_controller.py
```

## 🚀 Cómo Ejecutar Tests

### Ejecutar Todos los Tests de Controladores

```bash
# Desde la raíz del proyecto
python tests/controllers_test/run_controller_tests.py
```

### Ejecutar Tests de un Controlador Específico

```bash
# Tests específicos para analysis_controller
python tests/controllers_test/run_controller_tests.py analysis

# Tests específicos para drone_controller
python tests/controllers_test/run_controller_tests.py drone

# Tests específicos para geo_controller
python tests/controllers_test/run_controller_tests.py geo

# Tests específicos para mission_controller
python tests/controllers_test/run_controller_tests.py mission
```

### Ejecutar con pytest Directamente

```bash
# Ejecutar un archivo específico
pytest tests/controllers_test/test_analysis_controller.py -v

# Ejecutar todos los tests del directorio
pytest tests/controllers_test/ -v

# Ejecutar con más detalles en caso de fallo
pytest tests/controllers_test/test_drone_controller.py -v --tb=long
```

## 🔍 Qué Se Prueba en Cada Controlador

### AnalysisController (`test_analysis_controller.py`)
- ✅ Inicialización del controlador
- ✅ Endpoint `/analyze` (POST) - casos de éxito y error
- ✅ Endpoint `/results/<filename>` (GET)
- ✅ Endpoint `/api/analysis/status` (GET)
- ✅ Función `_extract_analysis_params()`
- ✅ Manejo de errores (servicio no inicializado, excepciones)
- ✅ Validación de parámetros

### DroneController (`test_drone_controller.py`)
- ✅ Inicialización del controlador
- ✅ Endpoint `/api/drone/connect` (POST)
- ✅ Endpoint `/api/drone/disconnect` (POST)
- ✅ Endpoint `/api/drone/takeoff` (POST) - con altitud default y personalizada
- ✅ Endpoint `/api/drone/land` (POST)
- ✅ Endpoint `/api/drone/stream/start` (POST)
- ✅ Endpoint `/api/drone/stream/stop` (POST)
- ✅ Endpoint `/api/drone/telemetry` (GET)
- ✅ Endpoint `/api/drone/simulate/paths` (GET)
- ✅ Endpoint `/api/drone/simulate/start` (POST)
- ✅ Manejo masivo de errores en todos los endpoints

### GeoController (`test_geo_controller.py`)
- ✅ Inicialización del controlador
- ✅ Endpoint `/api/geo/reference/add` (POST)
- ✅ Endpoint `/api/geo/changes/detect` (POST)
- ✅ Endpoint `/api/geo/target/create` (POST)
- ✅ Endpoint `/api/geo/position/calculate` (POST)
- ✅ Endpoint `/api/geo/observation/add` (POST)
- ✅ Endpoint `/api/geo/targets/status` (GET)
- ✅ Función `_extract_observation_params()`
- ✅ Validaciones de campos requeridos

### MissionController (`test_mission_controller.py`)
- ✅ Inicialización del controlador
- ✅ Endpoint `/api/missions/` (GET)
- ✅ Endpoint `/api/missions/start` (POST)
- ✅ Endpoint `/api/missions/abort` (POST)
- ✅ Endpoint `/api/missions/llm/create` (POST)
- ✅ Endpoint `/api/missions/llm/adaptive` (POST)
- ✅ Endpoint `/api/missions/llm/list` (GET)
- ✅ Endpoint `/api/missions/cartography/upload` (POST)
- ✅ Endpoint `/api/missions/cartography/areas` (GET)

## 📊 Interpretación de Resultados

### Salida del Script

El script `run_controller_tests.py` proporciona:

1. **Estado de Archivos**: Qué tests existen y cuáles faltan
2. **Ejecución Individual**: Resultado de cada archivo de test
3. **Detalles de Fallos**: Stdout y stderr cuando hay errores
4. **Resumen Final**: Estadísticas de éxito/fallo
5. **Tasa de Éxito**: Porcentaje de tests que pasan

### Ejemplo de Salida Exitosa

```
🔥 SISTEMA DE TESTING DE CONTROLADORES
==================================================
📁 Directorio de tests: /path/to/tests/controllers_test
📁 Raíz del proyecto: /path/to/project

📋 ESTADO DE ARCHIVOS DE TEST:
------------------------------
✅ test_analysis_controller.py
✅ test_drone_controller.py
✅ test_geo_controller.py
✅ test_mission_controller.py

🧪 EJECUTANDO: test_analysis_controller.py
----------------------------------------
✅ test_analysis_controller.py: TODOS LOS TESTS PASARON
   ✓ TestAnalysisController::test_init_analysis_controller PASSED
   ✓ TestAnalysisController::test_analyze_endpoint_success PASSED
   ...

📊 RESUMEN FINAL
==================================================
✅ test_analysis_controller.py: ÉXITO
✅ test_drone_controller.py: ÉXITO
✅ test_geo_controller.py: ÉXITO
✅ test_mission_controller.py: ÉXITO

📈 ESTADÍSTICAS:
   Total de archivos: 4
   Exitosos: 4
   Fallidos: 0
   Faltantes: 0
   Tasa de éxito: 100.0%

🎉 ¡TODOS LOS TESTS DE CONTROLADORES PASAN! 🎉
```

## 🛠️ Troubleshooting

### Si un Test Falla

1. **Ejecutar el test específico** para ver detalles:
   ```bash
   pytest tests/controllers_test/test_nombre_controller.py::TestClase::test_metodo_especifico -v --tb=long
   ```

2. **Revisar imports**: Asegurarse de que todos los módulos se importan correctamente
   
3. **Verificar mocks**: Los servicios deben estar mockeados correctamente

4. **Comprobar estructura**: Los controladores deben seguir la estructura esperada

### Errores Comunes

- **Import Error**: Verificar que `src/` esté en el PYTHONPATH
- **Attribute Error**: El controlador puede haber cambiado su estructura
- **Connection Error**: Los mocks no están configurados correctamente

## 🔧 Personalización

### Agregar Nuevos Tests

1. Crear el archivo `test_nuevo_controller.py`
2. Seguir la estructura de los tests existentes
3. Agregar el nombre del archivo a `run_controller_tests.py`
4. Incluir las funciones específicas del controlador

### Modificar Configuración

Los tests usan:
- **pytest** como framework de testing
- **unittest.mock** para mocking
- **Flask test client** para requests HTTP
- **Fixtures** para configuración reutilizable

## 📝 Contribuir

Al agregar nuevos endpoints o funciones a los controladores:

1. **Crear tests correspondientes** inmediatamente
2. **Incluir casos de éxito y error**
3. **Verificar manejo de servicios no inicializados**
4. **Probar validación de parámetros**
5. **Ejecutar el script completo** antes de commit

## 🎯 Objetivo

Este sistema garantiza que:
- ✅ Cada función de controlador tiene tests
- ✅ Se identifican fallos específicos rápidamente  
- ✅ Los cambios no rompen funcionalidad existente
- ✅ El código mantiene calidad enterprise
- ✅ La refactorización es segura y verificable 