# 📋 Documentación de Scripts - Drone Geo Analysis

## 🏗️ Arquitectura General del Proyecto

El proyecto Drone Geo Analysis está organizado en una arquitectura modular siguiendo principios de **Single Responsibility** y **Clean Architecture**. Cada directorio tiene un propósito específico y los scripts están diseñados para ser independientes pero colaborativos.

```
src/
├── main.py                 # Punto de entrada principal de la aplicación
├── app.py                  # [DEPRECATED] - Reemplazado por main.py
├── controllers/            # Controladores HTTP (Flask Blueprints)
├── drones/                 # Gestión y control de hardware de drones
├── geo/                    # Análisis geográfico y triangulación
├── models/                 # Modelos de IA y estructuras de datos
├── processors/             # Procesamiento de imágenes y video
├── services/               # Lógica de negocio empresarial
├── templates/              # Interfaces web (HTML/CSS/JS)
└── utils/                  # Utilidades y funciones auxiliares
```

---

## 📁 `/src/main.py`

**Propósito**: Aplicación principal refactorizada con arquitectura empresarial.

### 🎯 Funcionalidad Principal:
- **Patrón Factory**: Implementa `DroneGeoApp` para crear y configurar la aplicación Flask
- **Orquestación de Componentes**: Inicializa todos los servicios, controladores y módulos
- **Configuración Empresarial**: Manejo de variables de entorno, logging profesional, validación de configuración
- **Inyección de Dependencias**: Conecta servicios con controladores de forma modular

### 🔗 Relaciones:
- **Importa**: Todos los servicios (`DroneService`, `MissionService`, `AnalysisService`, `GeoService`)
- **Importa**: Todos los controladores (blueprints de Flask)
- **Importa**: Modelos principales (`GeoAnalyzer`, `LLMMissionPlanner`, `GeolocationManager`)
- **Usado por**: Sistema de despliegue Docker y scripts de inicio

### ⚙️ Características Técnicas:
- Detección automática de módulos disponibles vs fallback
- Configuración adaptativa para desarrollo y producción
- Integración con waitress para deployment de producción
- Logging rotativo con múltiples handlers

---

## 📁 `/src/controllers/` - Controladores HTTP

Los controladores implementan **Flask Blueprints** para manejar rutas HTTP específicas. Siguen el principio de **Single Responsibility** donde cada controlador maneja un dominio específico.

### 📄 `analysis_controller.py`

**Propósito**: Maneja rutas HTTP para análisis de imágenes geográficas.

#### 🎯 Funcionalidad:
- **Endpoint `/analyze`**: Recibe imágenes via POST y las procesa con IA
- **Endpoint `/results/<filename>`**: Sirve archivos de resultados guardados
- **Endpoint `/api/analysis/status`**: Monitoreo del estado de análisis en progreso
- **Validación de Entrada**: Verifica archivos de imagen y parámetros

#### 🔗 Relaciones:
- **Usa**: `AnalysisService` para lógica de negocio
- **Usa**: `src/utils/helpers.py` para metadatos de imagen
- **Conectado a**: Frontend en `templates/` para análisis de imágenes

#### ⚙️ Parámetros Soportados:
- `confidence_threshold`: Umbral de confianza para resultados
- `model_version`: Versión del modelo AI (default, enhanced, fast)
- `detail_level`: Nivel de detalle en respuestas (normal, high, low)

---

### 📄 `drone_controller.py`

**Propósito**: Maneja rutas HTTP para control de drones en tiempo real.

#### 🎯 Funcionalidad:
- **Control Básico**: `/connect`, `/disconnect`, `/takeoff`, `/land`
- **Video Streaming**: `/stream/start`, `/stream/stop`
- **Telemetría**: `/telemetry` para datos en tiempo real
- **Simulación**: `/simulate/paths`, `/simulate/start` para rutas predefinidas

#### 🔗 Relaciones:
- **Usa**: `DroneService` para lógica de negocio
- **Conectado a**: `src/drones/` para hardware de drones
- **Frontend**: Panel de control en `templates/drone_control.html`

#### ⚙️ Características:
- Validación de altitud (máximo 120m por regulaciones)
- Manejo de errores de conexión de hardware
- Telemetría en formato JSON estructurado

---

### 📄 `geo_controller.py`

**Propósito**: Maneja rutas HTTP para geolocalización y triangulación.

#### 🎯 Funcionalidad:
- **Referencias**: `/reference/add` para imágenes de referencia
- **Detección de Cambios**: `/changes/detect` entre imágenes
- **Triangulación**: `/target/create`, `/position/calculate`
- **Observaciones**: `/observation/add` para datos de triangulación
- **Estado**: `/targets/status` para monitoreo de objetivos

#### 🔗 Relaciones:
- **Usa**: `GeoService` para lógica de negocio
- **Conectado a**: `src/geo/` para algoritmos geográficos
- **Frontend**: Pestañas de geolocalización en panel de control

---

### 📄 `mission_controller.py`

**Propósito**: Maneja rutas HTTP para misiones y planificación LLM.

#### 🎯 Funcionalidad:
- **Misiones Básicas**: `/missions`, `/missions/start`, `/missions/abort`
- **LLM Intelligence**: `/llm/create` para misiones con lenguaje natural
- **Control Adaptativo**: `/llm/adaptive` para decisiones en tiempo real
- **Cartografía**: `/cartography/upload`, `/cartography/areas`

#### 🔗 Relaciones:
- **Usa**: `MissionService` para lógica de negocio
- **Conectado a**: `src/models/mission_planner.py` para IA
- **Frontend**: Pestañas de misiones en panel de control

#### ⚙️ Formatos Soportados:
- **Cartografía**: GeoJSON, JSON
- **Comandos LLM**: Lenguaje natural en español/inglés
- **Archivos**: Upload hasta 16MB

---

### 📄 `__init__.py`

**Propósito**: Exporta todos los blueprints para registro en la aplicación principal.

#### 🔗 Exportaciones:
- `drone_blueprint`
- `mission_blueprint`
- `analysis_blueprint`
- `geo_blueprint`

---

## 📁 `/src/drones/` - Control de Hardware de Drones

### 📄 `base_drone.py`

**Propósito**: Clase abstracta que implementa el patrón **Abstract Factory** para controladores de drones.

#### 🎯 Funcionalidad:
- **Interfaz Uniforme**: Define métodos comunes para todos los tipos de drones
- **Abstracción de Hardware**: Permite intercambiar marcas de drones sin cambiar código
- **Métodos Abstractos**: `connect()`, `disconnect()`, `take_off()`, `land()`, `move_to()`, etc.

#### 🔗 Relaciones:
- **Heredado por**: `DJIDroneController` y futuros controladores (Parrot, Autel, etc.)
- **Usado por**: `DroneService` para operaciones de drones
- **Patrón**: Abstract Factory + Template Method

#### ⚙️ Métodos Definidos:
```python
- connect() -> bool
- disconnect() -> bool
- take_off(altitude: float) -> bool
- land() -> bool
- move_to(lat: float, lng: float, alt: float) -> bool
- capture_image() -> str
- start_video_stream() -> str
- stop_video_stream() -> bool
- get_telemetry() -> Dict[str, Any]
- execute_mission(mission_data: Dict) -> bool
```

---

### 📄 `dji_controller.py`

**Propósito**: Implementación concreta para control de drones DJI.

#### 🎯 Funcionalidad:
- **Control DJI Específico**: Integración con DJI SDK (comentado para desarrollo)
- **Simulación Avanzada**: Telemetría realista, posicionamiento GPS, manejo de estado
- **Operaciones de Vuelo**: Despegue, aterrizaje, navegación, captura de imágenes
- **Gestión de Misiones**: Ejecución de waypoints con acciones específicas

#### 🔗 Relaciones:
- **Hereda de**: `BaseDrone`
- **Usado por**: `DroneService`
- **Integración**: DJI Mobile SDK (en implementación real)
- **Conectado a**: `VideoProcessor` para streaming

#### ⚙️ Características Técnicas:
- **Telemetría Completa**: Batería, GPS, velocidad, orientación, señal
- **Posicionamiento Dinámico**: Actualización en tiempo real
- **Misiones Complejas**: Waypoints con acciones (foto, video, hover)
- **Simulación Realista**: Para desarrollo sin hardware físico

---

### 📄 `__init__.py`

**Propósito**: Módulo de inicialización para gestión de drones.

---

## 📁 `/src/geo/` - Análisis Geográfico

### 📄 `geo_correlator.py`

**Propósito**: Correlaciona imágenes de drones con referencias satelitales para validación geográfica.

#### 🎯 Funcionalidad:
- **Correlación Satelital**: Compara imágenes de drone con imágenes satelitales
- **Corrección de Coordenadas**: Ajusta GPS usando correlación visual
- **Cache Inteligente**: Almacena imágenes satelitales para optimización
- **Conversión Pixel-GPS**: Transforma coordenadas de píxel a coordenadas reales

#### 🔗 Relaciones:
- **Usado por**: `GeoService` para validación de posición
- **APIs Externas**: Servicios de imágenes satelitales
- **Cache**: `cache/satellite/` para almacenamiento local

#### ⚙️ Algoritmos Implementados:
- **Correlación Visual**: Comparación de características entre imágenes
- **Transformación Geográfica**: Cálculos de rotación y escala
- **Validación GPS**: Verificación de precisión de coordenadas
- **Factor de Confianza**: Métrica de calidad de correlación

---

### 📄 `geo_triangulation.py`

**Propósito**: Sistema de triangulación geográfica para localización precisa de objetivos.

#### 🎯 Funcionalidad:
- **Triangulación Multi-punto**: Calcula posición usando múltiples observaciones
- **Gestión de Objetivos**: Crea y rastrea objetivos específicos
- **Observaciones**: Registra rumbo, elevación y confianza desde diferentes posiciones
- **Cálculos Precisos**: Algoritmos geográficos para intersección de líneas de rumbo

#### 🔗 Relaciones:
- **Usado por**: `GeoService` para localización de objetivos
- **Conectado a**: Panel de geolocalización en frontend
- **Algoritmos**: Matemáticas geográficas con corrección de curvatura terrestre

#### ⚙️ Características Técnicas:
- **Mínimo 2 Observaciones**: Requerimiento para cálculo válido
- **Precisión Sub-métrica**: Dependiendo de calidad de observaciones
- **Gestión de Estados**: Tracking de objetivos activos/inactivos
- **Validación Automática**: Verificación de consistencia geográfica

---

### 📄 `__init__.py`

**Propósito**: Exporta las clases principales del módulo geográfico.

#### 🔗 Exportaciones:
- `GeoTriangulation`
- `GeoCorrelator`

---

## 📁 `/src/models/` - Modelos de IA y Datos

### 📄 `geo_analyzer.py`

**Propósito**: Modelo principal de análisis geográfico usando GPT-4 Vision.

#### 🎯 Funcionalidad:
- **Análisis OSINT**: Identificación de ubicaciones usando inteligencia artificial
- **GPT-4 Vision**: Procesamiento de imágenes con análisis visual avanzado
- **Multi-Provider**: Soporte para OpenAI y Docker Models con fallback automático
- **Extracción Estructurada**: Parsing robusto de respuestas JSON del LLM

#### 🔗 Relaciones:
- **Usado por**: `AnalysisService` y `VideoProcessor`
- **APIs**: OpenAI GPT-4 Vision, Docker Models locales
- **Configuración**: `src/utils/config.py` para proveedores LLM

#### ⚙️ Capacidades de Análisis:
- **Identificación Geográfica**: País, ciudad, distrito, barrio, calle
- **Coordenadas GPS**: Latitud y longitud estimadas
- **Evidencia Visual**: Lista de elementos que respaldan la identificación
- **Alternativas**: Ubicaciones posibles con diferentes niveles de confianza
- **Nivel de Confianza**: Porcentaje de certeza en la identificación

---

### 📄 `geo_manager.py`

**Propósito**: Gestor de estado para referencias de geolocalización e imágenes.

#### 🎯 Funcionalidad:
- **Gestión de Referencias**: Almacena imágenes de referencia para comparación
- **Tracking de Objetivos**: Mantiene estado de objetivos de triangulación
- **Metadatos**: Timestamps, ubicaciones, estado de cada elemento

#### 🔗 Relaciones:
- **Usado por**: `GeoService` para gestión de estado
- **Conectado a**: `GeoTriangulation` y `GeoCorrelator`

---

### 📄 `mission_models.py`

**Propósito**: Modelos de datos para el sistema de planificación de misiones.

#### 🎯 Estructuras de Datos:
- **`Waypoint`**: Coordenadas GPS, altitud, acciones específicas
- **`MissionArea`**: Área geográfica con límites, restricciones y POIs
- **`MissionMetadata`**: Información de tracking y configuración

#### 🔗 Relaciones:
- **Usado por**: `LLMMissionPlanner` para estructurar misiones
- **Conectado a**: Sistema de validación de misiones

---

### 📄 `mission_parser.py`

**Propósito**: Parser robusto de respuestas JSON desde LLM para misiones.

#### 🎯 Funcionalidad:
- **Extracción Multi-formato**: JSON directo, markdown, regex, índices
- **Robustez**: Maneja respuestas malformadas del LLM
- **Logging Detallado**: Debugging de errores de parsing

#### 🔗 Relaciones:
- **Usado por**: `LLMMissionPlanner` para procesar respuestas IA
- **Maneja**: Salidas de GPT-4 y modelos locales

---

### 📄 `mission_planner.py`

**Propósito**: Planificador principal de misiones con inteligencia artificial.

#### 🎯 Funcionalidad:
- **Generación LLM**: Crea misiones desde comandos en lenguaje natural
- **Multi-Provider**: OpenAI GPT-4 y Docker Models locales
- **Cartografía**: Carga y procesa archivos GeoJSON
- **Validación**: Verifica seguridad y viabilidad de misiones

#### 🔗 Relaciones:
- **Usado por**: `MissionService` para lógica de negocio
- **Importa**: `mission_parser`, `mission_validator`, `mission_utils`
- **APIs**: OpenAI, modelos locales via Docker

#### ⚙️ Capacidades:
- **Comandos Naturales**: "Patrulla el perímetro norte a 50m de altura"
- **Cartografía Inteligente**: Integración con mapas GeoJSON
- **Waypoints Automáticos**: Generación de rutas optimizadas
- **Validación de Seguridad**: Altitudes, distancias, restricciones aéreas

---

### 📄 `mission_utils.py`

**Propósito**: Utilidades matemáticas y geográficas para misiones.

#### 🎯 Funcionalidad:
- **Cálculos Geográficos**: Distancias, centros de área, verificación de límites
- **Generación de Grillas**: Patrones de vuelo automáticos
- **Estimaciones**: Tiempo de vuelo, consumo de batería

#### 🔗 Relaciones:
- **Usado por**: `LLMMissionPlanner` para cálculos geográficos
- **Funciones Puras**: Sin efectos secundarios, altamente testeable

---

### 📄 `mission_validator.py`

**Propósito**: Validador de seguridad para misiones de drones.

#### 🎯 Funcionalidad:
- **Validación de Altitud**: Límites legales (120m máximo)
- **Distancias**: Verificación de seguridad entre waypoints
- **Coordenadas**: Validación de rangos GPS válidos
- **Duración**: Estimaciones vs capacidad de batería

#### 🔗 Relaciones:
- **Usado por**: `LLMMissionPlanner` y `MissionService`
- **Estándares**: Regulaciones aéreas internacionales

---

### 📄 `__init__.py`

**Propósito**: Exporta todas las clases y funciones del módulo de modelos.

#### 🔗 Exportaciones Principales:
- `GeoAnalyzer`, `LLMMissionPlanner`, `GeolocationManager`
- Modelos de datos y utilidades de misiones

---

## 📁 `/src/processors/` - Procesamiento Multimedia

### 📄 `change_detector.py`

**Propósito**: Detector de cambios entre imágenes de la misma zona geográfica.

#### 🎯 Funcionalidad:
- **Detección de Cambios**: Compara imágenes usando OpenCV
- **Análisis de Contornos**: Identifica áreas específicas de cambio
- **Filtrado Inteligente**: Elimina ruido y cambios menores
- **Visualización**: Genera imágenes con cambios resaltados

#### 🔗 Relaciones:
- **Usado por**: `GeoService` para análisis temporal
- **Dependencias**: OpenCV, NumPy
- **Conectado a**: Sistema de referencias geográficas

#### ⚙️ Algoritmos:
- **Diferencia Absoluta**: Comparación pixel por pixel
- **Umbralización**: Filtrado de cambios significativos
- **Morfología**: Operaciones de dilatación para consolidar áreas
- **Análisis de Contornos**: Detección de formas y áreas cambiadas

---

### 📄 `video_processor.py`

**Propósito**: Procesador de video en tiempo real desde drones.

#### 🎯 Funcionalidad:
- **Streaming en Tiempo Real**: Procesamiento de video continuo
- **Threading Optimizado**: Captura y análisis en paralelo
- **Análisis Periódico**: Frames analizados con IA cada intervalo configurable
- **Queue Management**: Gestión eficiente de buffers de video

#### 🔗 Relaciones:
- **Usado por**: `DroneService` para streaming
- **Usa**: `GeoAnalyzer` para análisis de frames
- **Dependencias**: OpenCV, threading, queue

#### ⚙️ Características Técnicas:
- **Multi-threading**: Threads separados para captura y análisis
- **Throttling**: Control de frecuencia para optimización de CPU
- **Memory Management**: Gestión eficiente de memoria para streams largos
- **Error Recovery**: Manejo robusto de errores de stream

---

### 📄 `__init__.py`

**Propósito**: Exporta las clases principales del módulo de procesamiento.

#### 🔗 Exportaciones:
- `ChangeDetector`
- `VideoProcessor`

---

## 📁 `/src/services/` - Lógica de Negocio Empresarial

Los servicios implementan la **lógica de negocio** principal y actúan como intermediarios entre controladores y modelos.

### 📄 `analysis_service.py`

**Propósito**: Servicio empresarial para análisis de imágenes geográficas.

#### 🎯 Funcionalidad:
- **Orquestación de Análisis**: Coordina todos los pasos del análisis
- **Gestión de Archivos**: Manejo de uploads, metadatos, resultados
- **Filtros de Confianza**: Aplicación de umbrales de calidad
- **Persistencia**: Almacenamiento de resultados con timestamps

#### 🔗 Relaciones:
- **Usado por**: `AnalysisController`
- **Usa**: `GeoAnalyzer` para IA, `helpers.py` para utilidades
- **Conectado a**: Sistema de archivos para resultados

---

### 📄 `drone_service.py`

**Propósito**: Servicio empresarial para operaciones de drones.

#### 🎯 Funcionalidad:
- **Control de Vuelo**: Operaciones de alto nivel (despegue, aterrizaje, navegación)
- **Gestión de Streaming**: Coordinación entre drone y procesador de video
- **Telemetría**: Agregación y formato de datos de sensores
- **Simulaciones**: Rutas predefinidas para entrenamiento

#### 🔗 Relaciones:
- **Usado por**: `DroneController`
- **Usa**: `DJIDroneController`, `VideoProcessor`
- **Validaciones**: Altitud máxima, seguridad de vuelo

---

### 📄 `geo_service.py`

**Propósito**: Servicio empresarial para geolocalización y triangulación.

#### 🎯 Funcionalidad:
- **Triangulación Empresarial**: Orchestación de múltiples observaciones
- **Detección de Cambios**: Coordinación entre referencias y análisis actual
- **Gestión de Objetivos**: Lifecycle completo de objetivos de triangulación
- **Fallback Inteligente**: Simulación cuando módulos reales no están disponibles

#### 🔗 Relaciones:
- **Usado por**: `GeoController`
- **Usa**: `GeolocationManager`, `GeoTriangulation`, `GeoCorrelator`
- **Detecta**: Módulos mock vs reales automáticamente

---

### 📄 `mission_service.py`

**Propósito**: Servicio empresarial para misiones y planificación LLM.

#### 🎯 Funcionalidad:
- **Orquestación de Misiones**: Gestión completa del ciclo de vida de misiones
- **Integración LLM**: Coordinación con planificador de IA
- **Cartografía**: Upload y procesamiento de archivos GeoJSON
- **Control Adaptativo**: Decisiones en tiempo real usando IA

#### 🔗 Relaciones:
- **Usado por**: `MissionController`
- **Usa**: `LLMMissionPlanner`, controladores de drone
- **Validación**: `mission_validator` para seguridad

---

### 📄 `__init__.py`

**Propósito**: Exporta todos los servicios empresariales.

#### 🔗 Exportaciones:
- `DroneService`, `MissionService`, `AnalysisService`, `GeoService`

---

## 📁 `/src/templates/` - Interfaces Web

### 📄 `drone_control.html`

**Propósito**: Panel de control principal completo para operaciones de drones.

#### 🎯 Funcionalidad:
- **Control de Drones**: Interfaz completa para operaciones de vuelo
- **Misiones LLM**: Creación de misiones con lenguaje natural
- **Geolocalización**: Tools de triangulación y correlación
- **Análisis Visual**: Upload y procesamiento de imágenes
- **Simulación**: Testing de rutas de vuelo

#### 🔗 Características Frontend:
- **Mapa Interactivo**: Leaflet.js para visualización geográfica
- **Telemetría 3D**: Indicadores visuales avanzados (dron 3D, brújula, gauges)
- **Real-time**: Actualización de datos en tiempo real
- **Responsive**: Adaptativo para diferentes dispositivos

---

### 📄 `index.html`

**Propósito**: Página principal del sistema con overview de capacidades.

#### 🎯 Funcionalidad:
- **Landing Page**: Presentación profesional del sistema
- **Upload Básico**: Análisis rápido de imágenes
- **Navegación**: Links a herramientas especializadas
- **Demo**: Funcionalidad de prueba integrada

---

### 📄 `mission_instructions.html`

**Propósito**: Documentación y guía de uso para misiones LLM.

#### 🎯 Funcionalidad:
- **Tutorial Step-by-Step**: Guía completa de uso
- **Solución de Problemas**: Debugging y troubleshooting
- **Ejemplos**: Comandos de ejemplo para misiones
- **Funciones Debug**: Tools para desarrolladores

---

### 📄 `web_index.html`

**Propósito**: Interfaz optimizada para análisis rápido de imágenes.

#### 🎯 Funcionalidad:
- **Upload Simplificado**: Drag & drop para imágenes
- **Análisis Instantáneo**: Resultados inmediatos con IA
- **Resultados Estructurados**: Presentación clara de datos
- **Responsive**: Optimizado para uso móvil

---

## 📁 `/src/utils/` - Utilidades y Helpers

### 📄 `config.py`

**Propósito**: Gestión centralizada de configuración de la aplicación.

#### 🎯 Funcionalidad:
- **Logging Setup**: Configuración profesional de logs con rotación
- **Multi-Provider LLM**: Configuración para OpenAI y Docker Models
- **Environment Detection**: Auto-detección de entorno (dev/prod)
- **Validation**: Verificación de configuraciones críticas

#### 🔗 Configuraciones Disponibles:
- **OpenAI**: GPT-4, GPT-4 Vision con parámetros optimizados
- **Docker Models**: Modelos locales con timeouts extendidos
- **Logging**: Archivos rotativos con timestamps

---

### 📄 `helpers.py`

**Propósito**: Funciones auxiliares para operaciones comunes del sistema.

#### 🎯 Funcionalidad:
- **Gestión de Directorios**: Creación automática de directorios de proyecto
- **Procesamiento de Imágenes**: Conversión a base64, metadatos, formato
- **Conversión de Formatos**: AVIF/HEIC → JPEG para compatibilidad OpenAI
- **Persistencia**: Guardado de resultados con formato JSON

#### 🔗 Funciones Principales:
```python
- get_project_root() -> str
- get_results_directory() -> str
- get_logs_directory() -> str
- get_missions_directory() -> str
- encode_image_to_base64(path) -> Tuple[str, str]
- get_image_metadata(path) -> Dict
- save_analysis_results(results, path) -> str
```

#### ⚙️ Capacidades Técnicas:
- **Auto-conversión**: Formatos incompatibles → JPEG
- **Gestión de Memoria**: Optimización para imágenes grandes
- **Error Handling**: Manejo robusto de errores de archivo
- **Cross-platform**: Compatible con Windows, Linux, macOS

---

## 🔄 Flujo de Datos y Relaciones

### 🎯 Flujo Principal de Análisis:
```
Usuario → templates/ → controllers/ → services/ → models/ → APIs Externas
                                   ↓
                            utils/ ← processors/ ← drones/geo/
```

### 🔗 Dependencias Críticas:
1. **Controllers** dependen de **Services** (inyección de dependencias)
2. **Services** orquestan **Models** y **Processors**
3. **Models** usan **Utils** para configuración y helpers
4. **Drones/Geo** proporcionan datos en tiempo real
5. **Templates** consumen APIs via AJAX/Fetch

### ⚙️ Patrones de Diseño Implementados:
- **Abstract Factory**: `BaseDrone` para diferentes marcas de drones
- **Factory Pattern**: `DroneGeoApp` para crear aplicación
- **Service Layer**: Separación de lógica de negocio
- **Dependency Injection**: Servicios inyectados en controladores
- **Template Method**: Estructura común en modelos de IA
- **Observer Pattern**: Updates en tiempo real de telemetría

---

## 🚀 Próximos Desarrollos

### 🔮 Expansiones Planificadas:
- **Nuevos Controladores de Drones**: Parrot, Autel, custom hardware
- **Modelos de IA Adicionales**: Claude, Gemini, modelos especializados
- **Procesadores Avanzados**: Reconocimiento facial, detección de vehículos
- **Servicios de Integración**: APIs gubernamentales, servicios meteorológicos
- **Templates Especializados**: Dashboards específicos por tipo de misión

---

*Documentación actualizada para Drone Geo Analysis v1.0 - Sistema Empresarial de Análisis Geográfico con Drones* 