# Sistema de Testing para Módulo /geo

## 📋 Descripción

Este directorio contiene el sistema de testing para el módulo `/geo` del proyecto **Drone Geo Analysis**. Los tests están diseñados para identificar exactamente qué función falla cuando hay problemas.

## 🗂️ Estructura del Directorio

```
tests/geo_test/
├── __init__.py                    # Inicialización del módulo
├── test_geo_correlator.py         # Tests para GeoCorrelator
├── test_geo_triangulation.py      # Tests para GeoTriangulation
├── run_geo_tests.py              # Script ejecutor principal
└── README.md                     # Esta documentación
```

## 🧪 Componentes Testeados

### 1. GeoCorrelator (test_geo_correlator.py)
**Funciones principales testeadas:**
- Inicialización con parámetros y defaults
- Configuración de directorio de caché
- Extracción de datos GPS y telemetría
- Correlación entre imágenes
- Transformación de coordenadas

### 2. GeoTriangulation (test_geo_triangulation.py)
**Funciones principales testeadas:**
- Inicialización del sistema
- Agregar observaciones
- Cálculo de posición
- Gestión de objetivos

## 🚀 Comandos de Ejecución

### En Docker (Recomendado)
```bash
# Ejecutar todos los tests de geo
docker-compose exec drone-geo-app python tests/geo_test/run_geo_tests.py

# Ejecutar solo tests de GeoCorrelator
docker-compose exec drone-geo-app python tests/geo_test/run_geo_tests.py geo_correlator

# Ejecutar solo tests de GeoTriangulation
docker-compose exec drone-geo-app python tests/geo_test/run_geo_tests.py geo_triangulation
```

### Ejecución Local
```bash
# Ejecutar todos los tests
python tests/geo_test/run_geo_tests.py

# Tests individuales
python tests/geo_test/test_geo_correlator.py
python tests/geo_test/test_geo_triangulation.py
```

## 📊 Ejemplo de Salida

### Salida Exitosa
```
🚁 SISTEMA DE TESTING DE GEO
============================================================
✓ geo_correlator: COMPLETADO
✓ geo_triangulation: COMPLETADO

📈 ESTADÍSTICAS:
   Total de archivos: 2
   Exitosos: 2 (100%)
   Fallidos: 0
   Tasa de éxito: 100.0%

🎉 ¡TODOS LOS TESTS DE GEO PASAN! 🎉
```

## 🔧 Troubleshooting

### Problemas Comunes

1. **ImportError: No module named 'src.geo'**
   ```bash
   cd /path/to/Drone-Geo-Analysis
   python tests/geo_test/run_geo_tests.py
   ```

2. **ModuleNotFoundError: No module named 'numpy'**
   ```bash
   # Usar Docker (recomendado)
   docker-compose exec drone-geo-app python tests/geo_test/run_geo_tests.py
   ```

## 📞 Soporte

Si encuentras problemas con los tests:
1. Verificar que el entorno Docker esté funcionando
2. Comprobar que todas las dependencias estén instaladas
3. Revisar logs de error detallados

---

**Última actualización**: 2024-01-XX  
**Mantenido por**: Drone Geo Analysis Testing Team 