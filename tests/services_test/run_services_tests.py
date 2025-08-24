#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script ejecutor principal para todos los tests del módulo /services.

Este script permite ejecutar todos los tests o tests específicos del módulo services,
proporcionando estadísticas detalladas y identificación exacta de errores.

Uso:
    python run_services_tests.py                       # Ejecuta todos los tests
    python run_services_tests.py analysis_service      # Solo tests de AnalysisService
    python run_services_tests.py drone_service         # Solo tests de DroneService
    python run_services_tests.py geo_service           # Solo tests de GeoService
    python run_services_tests.py mission_service       # Solo tests de MissionService
"""

import sys
import os
import unittest
import time
from typing import Dict, Any

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importar los módulos de test
from test_analysis_service import TestAnalysisService
from test_drone_service import TestDroneService
from test_geo_service import TestGeoService
from test_mission_service import TestMissionService


class ServicesTestRunner:
    """Ejecutor de tests para el módulo services."""
    
    def __init__(self):
        """Inicializar el ejecutor de tests."""
        self.test_modules = {
            'analysis_service': TestAnalysisService,
            'drone_service': TestDroneService,
            'geo_service': TestGeoService,
            'mission_service': TestMissionService
        }
        
        self.results = {}
        
        # Emojis para cada servicio
        self.service_emojis = {
            'analysis_service': '🔬',
            'drone_service': '🚁',
            'geo_service': '🌍',
            'mission_service': '🎯'
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los tests del módulo services.
        
        Returns:
            Diccionario con los resultados de todos los tests
        """
        print("🔧 SISTEMA DE TESTING DE SERVICES")
        print("=" * 60)
        
        total_stats = {
            'total_tests': 0,
            'total_passed': 0,
            'total_failures': 0,
            'total_errors': 0,
            'execution_time': 0,
            'services_count': len(self.test_modules)
        }
        
        start_time = time.time()
        
        # Ejecutar tests para cada servicio
        for service_name, test_class in self.test_modules.items():
            emoji = self.service_emojis.get(service_name, '🔧')
            print(f"\n{emoji} Ejecutando tests de {service_name}...")
            
            service_result = self._run_service_tests(test_class)
            self.results[service_name] = service_result
            
            # Acumular estadísticas
            total_stats['total_tests'] += service_result['tests_run']
            total_stats['total_passed'] += service_result['passed']
            total_stats['total_failures'] += service_result['failures']
            total_stats['total_errors'] += service_result['errors']
        
        total_stats['execution_time'] = time.time() - start_time
        
        # Mostrar resumen final
        self._show_final_summary(total_stats)
        
        return {
            'services': self.results,
            'total_stats': total_stats
        }
    
    def run_specific_test(self, service_name: str) -> Dict[str, Any]:
        """
        Ejecuta tests de un servicio específico.
        
        Args:
            service_name: Nombre del servicio a testear
            
        Returns:
            Diccionario con los resultados del servicio
        """
        if service_name not in self.test_modules:
            available = ', '.join(self.test_modules.keys())
            print(f"❌ Servicio '{service_name}' no encontrado.")
            print(f"📋 Servicios disponibles: {available}")
            return {}
        
        emoji = self.service_emojis.get(service_name, '🔧')
        print(f"{emoji} EJECUTANDO TESTS DE {service_name.upper().replace('_', ' ')}")
        print("=" * 60)
        
        start_time = time.time()
        test_class = self.test_modules[service_name]
        result = self._run_service_tests(test_class)
        result['execution_time'] = time.time() - start_time
        
        # Mostrar resumen del servicio
        self._show_service_summary(service_name, result)
        
        return result
    
    def _run_service_tests(self, test_class) -> Dict[str, Any]:
        """Ejecuta los tests de un servicio específico."""
        # Crear suite de tests
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(test_class)
        
        # Ejecutar tests
        runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        # Calcular estadísticas
        tests_run = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        passed = tests_run - failures - errors
        success_rate = (passed / tests_run * 100) if tests_run > 0 else 0
        
        return {
            'tests_run': tests_run,
            'passed': passed,
            'failures': failures,
            'errors': errors,
            'success_rate': success_rate,
            'failure_details': result.failures,
            'error_details': result.errors
        }
    
    def _show_service_summary(self, service_name: str, result: Dict[str, Any]) -> None:
        """Muestra el resumen de un servicio específico."""
        success_rate = result['success_rate']
        emoji = self.service_emojis.get(service_name, '🔧')
        
        if success_rate == 100.0:
            status_emoji = "✓"
            status_color = "verde"
        elif success_rate >= 80.0:
            status_emoji = "⚠"
            status_color = "amarillo"
        else:
            status_emoji = "❌"
            status_color = "rojo"
        
        print(f"{status_emoji} {service_name}: {result['passed']}/{result['tests_run']} tests exitosos ({success_rate:.1f}%)")
        
        if result['failures'] > 0 or result['errors'] > 0:
            print(f"   ❌ Fallos: {result['failures']}, Errores: {result['errors']}")
            
            # Mostrar detalles de fallos
            for failure in result['failure_details']:
                print(f"      • FALLO: {failure[0]}")
            
            for error in result['error_details']:
                print(f"      • ERROR: {error[0]}")
        
        if 'execution_time' in result:
            print(f"   ⏱️  Tiempo: {result['execution_time']:.2f}s")
    
    def _show_final_summary(self, stats: Dict[str, Any]) -> None:
        """Muestra el resumen final de todos los tests."""
        total_tests = stats['total_tests']
        total_passed = stats['total_passed']
        total_failures = stats['total_failures']
        total_errors = stats['total_errors']
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 ESTADÍSTICAS FINALES:")
        print(f"   Total servicios: {stats['services_count']}")
        print(f"   Total tests: {total_tests}")
        print(f"   Exitosos: {total_passed}")
        print(f"   Fallidos: {total_failures}")
        print(f"   Errores: {total_errors}")
        print(f"   Tasa de éxito: {success_rate:.1f}%")
        print(f"   Tiempo total: {stats['execution_time']:.2f}s")
        print(f"   Promedio por servicio: {stats['execution_time']/stats['services_count']:.2f}s")
        
        # Determinar estado final
        if success_rate == 100.0:
            print(f"\n🎉 ¡TODOS LOS TESTS DE SERVICES PASAN! 🎉")
        elif success_rate >= 90.0:
            print(f"\n✅ EXCELENTE RESULTADO - CALIDAD ENTERPRISE")
        elif success_rate >= 80.0:
            print(f"\n⚠️  RESULTADO BUENO - REVISAR FALLOS MENORES")
        else:
            print(f"\n❌ MÚLTIPLES FALLOS DETECTADOS - REQUIERE ATENCIÓN INMEDIATA")
        
        # Mostrar ranking de servicios
        print(f"\n🏆 RANKING DE SERVICIOS:")
        service_rankings = []
        for service_name, result in self.results.items():
            service_rankings.append((service_name, result['success_rate'], result['tests_run']))
        
        # Ordenar por tasa de éxito y luego por número de tests
        service_rankings.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        for i, (service_name, success_rate, tests_count) in enumerate(service_rankings, 1):
            emoji = self.service_emojis.get(service_name, '🔧')
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}️⃣")
            print(f"   {medal} {emoji} {service_name}: {success_rate:.1f}% ({tests_count} tests)")
        
        # Mostrar resumen detallado por servicio
        print(f"\n📊 RESUMEN DETALLADO:")
        for service_name, result in self.results.items():
            self._show_service_summary(service_name, result)
        
        # Mostrar distribución de tests
        print(f"\n📋 DISTRIBUCIÓN DE TESTS:")
        total_services_tests = sum(result['tests_run'] for result in self.results.values())
        for service_name, result in self.results.items():
            percentage = (result['tests_run'] / total_services_tests * 100) if total_services_tests > 0 else 0
            emoji = self.service_emojis.get(service_name, '🔧')
            print(f"   {emoji} {service_name}: {result['tests_run']} tests ({percentage:.1f}%)")
    
    def show_help(self):
        """Muestra ayuda de uso del script."""
        print("🔧 SISTEMA DE TESTING DE SERVICES - AYUDA")
        print("=" * 60)
        print()
        print("USO:")
        print("  python run_services_tests.py                    # Ejecuta todos los tests")
        print("  python run_services_tests.py <servicio>         # Ejecuta tests específicos")
        print()
        print("SERVICIOS DISPONIBLES:")
        for service_name, emoji in self.service_emojis.items():
            print(f"  {emoji} {service_name:<20} # Tests para {service_name.replace('_', ' ').title()}")
        print()
        print("EJEMPLOS:")
        print("  python run_services_tests.py analysis_service  # Solo AnalysisService")
        print("  python run_services_tests.py drone_service     # Solo DroneService")
        print("  python run_services_tests.py geo_service       # Solo GeoService")
        print("  python run_services_tests.py mission_service   # Solo MissionService")
        print()
        print("OPCIONES:")
        print("  --help, -h                                      # Muestra esta ayuda")


def main():
    """Función principal del script."""
    runner = ServicesTestRunner()
    
    # Procesar argumentos de línea de comandos
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        runner.show_help()
        return
    
    # Determinar modo de ejecución
    if len(args) > 0:
        service_name = args[0].lower()
        runner.run_specific_test(service_name)
    else:
        runner.run_all_tests()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Ejecución interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
