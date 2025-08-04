# 🚁 Sistema de Testing de Drones

Este directorio contiene tests específicos para cada componente del módulo de drones.

## 🚀 Cómo Ejecutar Tests

```bash
# Todos los tests
docker-compose exec drone-geo-app python tests/drones_test/run_drone_tests.py

# Test específico  
docker-compose exec drone-geo-app python tests/drones_test/run_drone_tests.py dji_controller
```

## 🔍 Componentes Probados

### BaseDrone
- ✅ Clase abstracta correcta
- ✅ Métodos abstractos definidos  
- ✅ Patrón Abstract Factory

### DJIDroneController  
- ✅ Herencia de BaseDrone
- ✅ Conexión y desconexión
- ✅ Operaciones de vuelo
- ✅ Captura de imágenes
- ✅ Sistema de telemetría
- ✅ Ejecución de misiones
