#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicación principal refactorizada siguiendo principios de modularidad.
Responsabilidad única: Configurar Flask y orquestar la aplicación.
"""

import os
import sys
import logging
from flask import Flask, render_template
from dotenv import load_dotenv

# Agregar la ruta del proyecto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar módulos internos
from src.models.geo_analyzer import GeoAnalyzer
from src.models.yolo_detector import YoloObjectDetector
from src.models.mission_planner import LLMMissionPlanner
from src.models.geo_manager import GeolocationManager
from src.utils.config import setup_logging
from src.services import DroneService, MissionService, AnalysisService, GeoService
from src.services.chat_service import ChatService
from src.controllers import (
    drone_blueprint, mission_blueprint, 
    analysis_blueprint, geo_blueprint
)
from src.controllers.drone_controller import init_drone_controller
from src.controllers.mission_controller import init_mission_controller
from src.controllers.analysis_controller import init_analysis_controller
from src.controllers.geo_controller import init_geo_controller

logger = logging.getLogger(__name__)

class DroneGeoApp:
    """
    Clase principal de la aplicación que orquesta todos los componentes.
    Sigue el patrón Factory para crear y configurar la aplicación.
    """
    
    def __init__(self):
        """Inicializa la aplicación."""
        self.app = None
        self.services = {}
        self.use_real_modules = False
        
    def create_app(self) -> Flask:
        """
        Crea y configura la aplicación Flask.
        
        Returns:
            Instancia configurada de Flask
        """
        # Cargar variables de entorno
        load_dotenv()
        
        # Configurar logging
        setup_logging()
        logger.info("Iniciando aplicación Drone Geo Analysis")
        
        # Validar configuración crítica
        self._validate_environment()
        
        # Crear aplicación Flask
        self.app = self._create_flask_app()
        
        # Inicializar componentes
        self._initialize_components()
        
        # Registrar rutas
        self._register_routes()
        
        # Registrar blueprints
        self._register_blueprints()
        
        logger.info("Aplicación configurada correctamente")
        return self.app
    
    def _validate_environment(self):
        """Valida que las variables de entorno críticas estén configuradas."""
        if "OPENAI_API_KEY" not in os.environ:
            logger.error("No se encontró OPENAI_API_KEY en las variables de entorno")
            print("Error: Se requiere una API key de OpenAI. Agrégala al archivo .env")
            sys.exit(1)
    
    def _create_flask_app(self) -> Flask:
        """Crea la instancia básica de Flask."""
        app = Flask(__name__, 
                   static_folder='templates/static',
                   template_folder='templates')
        
        # Configuración básica
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
        
        return app
    
    def _initialize_components(self):
        """Inicializa todos los componentes del sistema."""
        logger.info("Inicializando componentes del sistema...")
        
        # Detectar módulos disponibles
        self._detect_available_modules()
        
        # Inicializar modelos principales
        analyzer = GeoAnalyzer()
        yolo_detector = YoloObjectDetector()
        mission_planner = LLMMissionPlanner()
        geo_manager = GeolocationManager()
        
        # Inicializar servicio de chat
        chat_service = ChatService()
        
        # Inicializar controladores de hardware
        hardware_components = self._initialize_hardware_components()
        
        # Crear servicios
        self.services = {
            'drone': DroneService(
                hardware_components['drone_controller'],
                hardware_components['video_processor']
            ),
            'mission': MissionService(
                mission_planner,
                hardware_components['drone_controller']
            ),
            'analysis': AnalysisService(analyzer, yolo_detector),
            'geo': GeoService(
                geo_manager,
                hardware_components['geo_triangulation'],
                hardware_components['geo_correlator']
            ),
            'chat': chat_service
        }
        
        logger.info(f"Servicios inicializados: {list(self.services.keys())}")
    
    def _detect_available_modules(self):
        """Detecta qué módulos están disponibles (reales vs fallback)."""
        try:
            # Intentar importar módulos reales
            from src.drones.parrot_anafi_controller import ParrotAnafiController
            from src.processors.video_processor import VideoProcessor
            from src.processors.change_detector import ChangeDetector
            from src.geo.geo_triangulation import GeoTriangulation
            from src.geo.geo_correlator import GeoCorrelator
            
            self.use_real_modules = True
            logger.info("✅ Módulos reales detectados y disponibles")
            
        except ImportError as e:
            self.use_real_modules = False
            logger.error(f"❌ Módulos reales no disponibles: {e}")
            logger.error("💥 Sistema requiere módulos reales para funcionar correctamente")
            print("❌ Error: Módulos de hardware no encontrados")
            print("🔧 Asegúrate de que todos los drivers y dependencias estén instalados")
            sys.exit(1)
    
    def _initialize_hardware_components(self) -> dict:
        """Inicializa componentes de hardware reales."""
        return self._initialize_real_components()
    
    def _initialize_real_components(self) -> dict:
        """Inicializa componentes reales."""
        from src.drones.parrot_anafi_controller import ParrotAnafiController
        from src.processors.video_processor import VideoProcessor
        from src.processors.change_detector import ChangeDetector
        from src.geo.geo_triangulation import GeoTriangulation
        from src.geo.geo_correlator import GeoCorrelator
        
        analyzer = GeoAnalyzer()  # Necesario para VideoProcessor
        
        components = {
            'drone_controller': ParrotAnafiController(),
            'video_processor': VideoProcessor(analyzer),
            'change_detector': ChangeDetector(),
            'geo_triangulation': GeoTriangulation(),
            'geo_correlator': GeoCorrelator()
        }
        
        logger.info("✅ Componentes reales inicializados correctamente")
        return components
    
    def _register_routes(self):
        """Registra rutas básicas de la aplicación."""
        assert self.app is not None, "Flask app must be initialized first"
        
        @self.app.route('/')
        def index():
            """Ruta principal que muestra la interfaz moderna."""
            return render_template('index.html')
        
        @self.app.route('/drone_control.html')
        def drone_control():
            """Panel de control completo de drones."""
            return render_template('drone_control.html')
        
        @self.app.route('/web_index.html')
        def web_index():
            """Análisis rápido de imágenes."""
            return render_template('web_index.html')
        
        @self.app.route('/mission_instructions.html')
        def mission_instructions():
            """Instrucciones de misiones LLM."""
            return render_template('mission_instructions.html')
        
        logger.info("✅ Rutas básicas registradas")
    
    def _register_blueprints(self):
        """Registra todos los blueprints de controladores."""
        assert self.app is not None, "Flask app must be initialized first"
        
        # Inicializar controladores con sus servicios
        init_drone_controller(self.services['drone'])
        init_mission_controller(self.services['mission'])
        init_analysis_controller(self.services['analysis'], self.services['chat'])
        init_geo_controller(self.services['geo'])
        
        # Registrar blueprints
        self.app.register_blueprint(drone_blueprint)
        self.app.register_blueprint(mission_blueprint)
        self.app.register_blueprint(analysis_blueprint)
        self.app.register_blueprint(geo_blueprint)
        
        logger.info("✅ Blueprints registrados correctamente")

def main():
    """Función principal que inicia el servidor web."""
    # Crear aplicación
    app_factory = DroneGeoApp()
    app = app_factory.create_app()
    
    # Configuración del servidor
    host = '0.0.0.0'
    port = 5000
    
    logger.info(f"🚀 Servidor iniciado en {host}:{port}")
    print(f"🚀 Servidor iniciado en http://{host}:{port} (puerto interno del contenedor)")
    print(f"🌐 Accede desde tu navegador en: http://localhost:4001")
    print(f"🎮 Panel de Control: http://localhost:4001/drone_control.html")
    print(f"⚡ Análisis Rápido: http://localhost:4001/web_index.html")
    print(f"📱 Mapeo de puertos: localhost:4001 → contenedor:5000")
    
    # Usar waitress para producción
    try:
        from waitress import serve
        serve(app, host=host, port=port)
    except ImportError:
        logger.warning("Waitress no disponible, usando servidor de desarrollo de Flask")
        app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    main() 