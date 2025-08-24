#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script ejecutor principal para todos los tests del módulo /processors.

Este script permite ejecutar todos los tests o tests específicos del módulo processors,
proporcionando estadísticas detalladas y identificación exacta de errores.

Uso:
    python run_processors_tests.py                    # Ejecuta todos los tests
    python run_processors_tests.py change_detector    # Solo tests de ChangeDetector
    python run_processors_tests.py video_processor    # Solo tests de VideoProcessor
"""

import sys
import os
import unittest
import time
from typing import Dict, Any

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importar los módulos de test
from test_change_detector import TestChangeDetector
from test_video_processor import TestVideoProcessor


class ProcessorTestRunner:
    """Ejecutor de tests para el módulo processors."""
    
    def __init__(self):
        """Inicializar el ejecutor de tests."""
        self.test_modules = {
            'change_detector': TestChangeDetector,
            'video_processor': TestVideoProcessor
        }
        
        self.results = {}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecuta todos los tests del módulo processors.
        
        Returns:
            Diccionario con los resultados de todos los tests
        """
        print("🎬 SISTEMA DE TESTING DE PROCESSORS")
        print("=" * 60)
        
        total_stats = {
            'total_tests': 0,
            'total_passed': 0,
            'total_failures': 0,
            'total_errors': 0,
            'execution_time': 0
        }
        
        start_time = time.time()
        
        # Ejecutar tests para cada módulo
        for module_name, test_class in self.test_modules.items():
            print(f"\n🔧 Ejecutando tests de {module_name}...")
            
            module_result = self._run_module_tests(test_class)
            self.results[module_name] = module_result
            
            # Acumular estadísticas
            total_stats['total_tests'] += module_result['tests_run']
            total_stats['total_passed'] += module_result['passed']
            total_stats['total_failures'] += module_result['failures']
            total_stats['total_errors'] += module_result['errors']
        
        total_stats['execution_time'] = time.time() - start_time
        
        # Mostrar resumen final
        self._show_final_summary(total_stats)
        
        return {
            'modules': self.results,
            'total_stats': total_stats
        }
    
    def run_specific_test(self, module_name: str) -> Dict[str, Any]:
        """
        Ejecuta tests de un módulo específico.
        
        Args:
            module_name: Nombre del módulo a testear
            
        Returns:
            Diccionario con los resultados del módulo
        """
        if module_name not in self.test_modules:
            available = ', '.join(self.test_modules.keys())
            print(f"❌ Módulo '{module_name}' no encontrado.")
            print(f"📋 Módulos disponibles: {available}")
            return {}
        
        print(f"🎬 EJECUTANDO TESTS DE {module_name.upper()}")
        print("=" * 60)
        
        start_time = time.time()
        test_class = self.test_modules[module_name]
        result = self._run_module_tests(test_class)
        result['execution_time'] = time.time() - start_time
        
        # Mostrar resumen del módulo
        self._show_module_summary(module_name, result)
        
        return result
    
    def _run_module_tests(self, test_class) -> Dict[str, Any]:
        """Ejecuta los tests de un módulo específico."""
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
    
    def _show_module_summary(self, module_name: str, result: Dict[str, Any]) -> None:
        """Muestra el resumen de un módulo específico."""
        success_rate = result['success_rate']
        
        if success_rate == 100.0:
            status_emoji = "✓"
            status_color = "verde"
        elif success_rate >= 80.0:
            status_emoji = "⚠"
            status_color = "amarillo"
        else:
            status_emoji = "❌"
            status_color = "rojo"
        
        print(f"{status_emoji} {module_name}: {result['passed']}/{result['tests_run']} tests exitosos ({success_rate:.1f}%)")
        
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
        print(f"   Total archivos: {len(self.test_modules)}")
        print(f"   Total tests: {total_tests}")
        print(f"   Exitosos: {total_passed}")
        print(f"   Fallidos: {total_failures}")
        print(f"   Errores: {total_errors}")
        print(f"   Tasa de éxito: {success_rate:.1f}%")
        print(f"   Tiempo total: {stats['execution_time']:.2f}s")
        
        # Determinar estado final
        if success_rate == 100.0:
            print(f"\n🎉 ¡TODOS LOS TESTS DE PROCESSORS PASAN! 🎉")
        elif success_rate >= 80.0:
            print(f"\n⚠️  TESTS MAYORMENTE EXITOSOS - REVISAR FALLOS")
        else:
            print(f"\n❌ MÚLTIPLES FALLOS DETECTADOS - REQUIERE ATENCIÓN")
        
        # Mostrar resumen por módulo
        print(f"\n📊 RESUMEN POR MÓDULO:")
        for module_name, result in self.results.items():
            self._show_module_summary(module_name, result)


def main():
    """Función principal del script."""
    runner = ProcessorTestRunner()
    
    # Determinar modo de ejecución
    if len(sys.argv) > 1:
        module_name = sys.argv[1].lower()
        runner.run_specific_test(module_name)
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
        sys.exit(1) 