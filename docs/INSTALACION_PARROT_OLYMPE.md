# 🚁 Guía de Instalación - Parrot Olympe SDK

## 📋 Resumen

Esta guía detalla cómo instalar y configurar Parrot Olympe SDK para controlar drones ANAFI desde el proyecto Drone-GeoAnalysis-LLMs.

## 🎯 Drones Compatibles

- **Parrot ANAFI**
- **Parrot ANAFI Thermal**
- **Parrot ANAFI USA**
- **Parrot ANAFI AI**

## 📦 Requisitos del Sistema

### Sistema Operativo
- **Ubuntu 20.04+** (recomendado)
- **Debian 10+**
- **Windows** (con WSL2)
- **macOS** (soporte limitado)

### Python
- **Python 3.8 - 3.11**
- **pip 20.3+**

## 🔧 Instalación

### 1. Instalación Básica (x86_64)

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar Olympe desde PyPI
pip install parrot-olympe

# O instalar versión específica
pip install parrot-olympe==7.7.5
```

### 2. Instalación en Raspberry Pi (ARM)

Para Raspberry Pi y otras arquitecturas ARM, necesitas compilar desde el código fuente:

```bash
# Dependencias del sistema
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    libgl1 \
    python3-dev

# Clonar repositorio Olympe
git clone https://github.com/Parrot-Developers/olympe.git
cd olympe

# Compilar e instalar
./build.sh -p python-clang-11 -t build -j
```

### 3. Instalación con Docker

```dockerfile
FROM ubuntu:20.04

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libgl1

# Instalar Olympe
RUN pip3 install parrot-olympe
```

## 🚀 Verificación de Instalación

```python
# test_olympe.py
import olympe
from olympe.messages.ardrone3.Piloting import TakeOff

print("✅ Olympe instalado correctamente")
print(f"📌 Versión: {olympe.__version__}")
```

Ejecutar:
```bash
python test_olympe.py
```

## 🔌 Conexión al Drone

### WiFi Directo (Modo por defecto)
1. Encender el drone ANAFI
2. Conectar tu computadora a la red WiFi del drone:
   - SSID: `ANAFI_XXXXXX`
   - Contraseña: Ver etiqueta del drone
3. IP por defecto: `10.202.0.1`

### Usando SkyController
1. Conectar SkyController al drone
2. Conectar computadora al SkyController via USB o WiFi
3. IP: `192.168.53.1`

## 📝 Ejemplo Básico

```python
#!/usr/bin/env python3
import olympe
from olympe.messages.ardrone3.Piloting import TakeOff, Landing
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged

# Crear instancia del drone
drone = olympe.Drone("10.202.0.1")

# Conectar
drone.connect()

# Despegar
assert drone(
    TakeOff()
    >> FlyingStateChanged(state="hovering", _timeout=5)
).wait()

print("✅ Drone despegado")

# Aterrizar
assert drone(Landing()).wait()

# Desconectar
drone.disconnect()
```

## 🐛 Solución de Problemas

### Error: "No module named 'olympe'"
```bash
# Verificar instalación
pip list | grep olympe

# Reinstalar
pip uninstall parrot-olympe
pip install parrot-olympe
```

### Error: "libGL.so.1: cannot open shared object file"
```bash
# Instalar libgl1
sudo apt-get install libgl1
```

### Error de conexión al drone
1. Verificar conexión WiFi al drone
2. Verificar IP correcta (ping 10.202.0.1)
3. Verificar firewall/antivirus

## 📚 Recursos Adicionales

- **Documentación Oficial**: https://developer.parrot.com/docs/olympe/
- **Foro de Desarrolladores**: https://forum.developer.parrot.com/
- **GitHub**: https://github.com/Parrot-Developers/olympe
- **Ejemplos**: https://github.com/Parrot-Developers/olympe/tree/master/src/olympe/doc/examples

## 🔒 Consideraciones de Seguridad

1. **Volar en áreas seguras**: Siempre probar en espacios abiertos y seguros
2. **Permisos**: Verificar regulaciones locales para vuelo de drones
3. **Modo simulación**: Usar simulación (Sphinx) para desarrollo inicial
4. **Límites de altura**: Configurar límites apropiados en el código

## 📄 Licencia

Olympe está licenciado bajo BSD-3-Clause. Ver [LICENSE](https://github.com/Parrot-Developers/olympe/blob/master/LICENSE.md) para más detalles.