#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script ejecutor para tests del módulo /models del proyecto Drone Geo Analysis.

Uso:
    python run_models_tests.py                      # Ejecutar todos los tests
    python run_models_tests.py mission_models       # Solo tests de MissionModels
    python run_models_tests.py mission_utils        # Solo tests de MissionUtils
    python run_models_tests.py mission_parser       # Solo tests de MissionParser
    python run_models_tests.py mission_validator    # Solo tests de MissionValidator
    python run_models_tests.py geo_manager          # Solo tests de GeolocationManager
"""

import sys
import os
import unittest
import argparse

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importar módulos de tests
from test_mission_models import TestMissionModels
from test_mission_utils import TestMissionUtils
from test_mission_parser import TestMissionParser
from test_mission_validator import TestMissionValidator
from test_geo_manager import TestGeolocationManager


class ModelsTestRunner:
    """Ejecutor de tests para el módulo /models."""
    
    def __init__(self):
        """Inicializar el ejecutor de tests."""
        self.test_modules = {
            'mission_models': TestMissionModels,
            'mission_utils': TestMissionUtils,
            'mission_parser': TestMissionParser,
            'mission_validator': TestMissionValidator,
            'geo_manager': TestGeolocationManager
        }
        self.results = {}
    
    def run_single_module(self, module_name: str):
        """Ejecuta tests de un módulo específico."""
        if module_name not in self.test_modules:
            raise ValueError(f"Módulo '{module_name}' no encontrado")
        
        print(f"\n🧪 EJECUTANDO TESTS DE {module_name.upper()}")
        print("=" * 60)
        
        # Crear suite de tests
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(self.test_modules[module_name])
        
        # Ejecutar tests
        runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        # Procesar resultados
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        passed = total_tests - failures - errors
        success_rate = (passed / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"✓ {module_name}: {passed}/{total_tests} tests exitosos ({success_rate:.1f}%)")
        
        self.results[module_name] = {
            'passed': passed,
            'total': total_tests,
            'success_rate': success_rate,
            'failures': result.failures,
            'errors': result.errors
        }
        
        return result
    
    def run_all_modules(self):
        """Ejecuta tests de todos los módulos."""
        print("🤖 SISTEMA DE TESTING DE MODELS")
        print("=" * 60)
        
        # Ejecutar cada módulo
        for module_name in self.test_modules.keys():
            try:
                self.run_single_module(module_name)
            except Exception as e:
                print(f"❌ {module_name}: ERROR - {str(e)}")
                self.results[module_name] = {
                    'passed': 0,
                    'total': 0,
                    'success_rate': 0,
                    'failures': [],
                    'errors': [('Module Error', str(e))]
                }
        
        self.print_summary()
    
    def print_summary(self):
        """Imprime resumen de resultados."""
        if not self.results:
            print("❌ No hay resultados para mostrar")
            return
        
        print(f"\n📈 ESTADÍSTICAS:")
        total_modules = len(self.results)
        successful_modules = sum(1 for r in self.results.values() if r['success_rate'] == 100)
        total_tests = sum(r['total'] for r in self.results.values())
        total_passed = sum(r['passed'] for r in self.results.values())
        
        print(f"   Total de archivos: {total_modules}")
        print(f"   Exitosos: {successful_modules} ({(successful_modules/total_modules)*100:.1f}%)")
        print(f"   Fallidos: {total_modules - successful_modules}")
        print(f"   Tasa de éxito: {(successful_modules/total_modules)*100:.1f}%")
        print(f"")
        print(f"🔍 TESTS INDIVIDUALES:")
        print(f"   Total ejecutados: {total_tests}")
        print(f"   Exitosos: {total_passed}")
        print(f"   Tasa de éxito: {(total_passed/total_tests)*100:.1f}%")
        
        # Mostrar detalles por módulo
        print(f"\n📋 DETALLES POR MÓDULO:")
        for module_name, result in self.results.items():
            status_emoji = "✅" if result['success_rate'] == 100 else "❌"
            print(f"   {status_emoji} {module_name}: {result['passed']}/{result['total']} tests ({result['success_rate']:.1f}%)")
        
        # Mostrar fallos específicos
        has_failures = any(r['success_rate'] < 100 for r in self.results.values())
        
        if has_failures:
            print(f"\n❌ FALLOS DETECTADOS:")
            for module_name, result in self.results.items():
                if result['success_rate'] < 100:
                    print(f"\n   📁 {module_name}:")
                    
                    for failure in result['failures']:
                        test_name = str(failure[0])
                        print(f"      💥 {test_name}")
                    
                    for error in result['errors']:
                        test_name = str(error[0])
                        print(f"      🔥 {test_name}")
        else:
            print(f"\n🎉 ¡TODOS LOS TESTS DE MODELS PASAN! 🎉")


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description="Ejecutor de tests para el módulo /models")
    parser.add_argument('module', nargs='?', 
                       choices=['mission_models', 'mission_utils', 'mission_parser', 
                               'mission_validator', 'geo_manager'],
                       help='Módulo específico a testear')
    
    args = parser.parse_args()
    
    # Crear ejecutor
    runner = ModelsTestRunner()
    
    try:
        if args.module:
            # Ejecutar módulo específico
            runner.run_single_module(args.module)
        else:
            # Ejecutar todos los módulos
            runner.run_all_modules()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrumpidos por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error ejecutando tests: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main() 