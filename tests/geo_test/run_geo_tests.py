#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script ejecutor para tests del módulo /geo del proyecto Drone Geo Analysis.

Uso:
    python run_geo_tests.py                    # Ejecutar todos los tests
    python run_geo_tests.py geo_correlator     # Solo tests de GeoCorrelator
    python run_geo_tests.py geo_triangulation  # Solo tests de GeoTriangulation
"""

import sys
import os
import unittest
import argparse

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importar módulos de tests
from test_geo_correlator import TestGeoCorrelator
from test_geo_triangulation import TestGeoTriangulation


class GeoTestRunner:
    """Ejecutor de tests para el módulo /geo."""
    
    def __init__(self):
        """Inicializar el ejecutor de tests."""
        self.test_modules = {
            'geo_correlator': TestGeoCorrelator,
            'geo_triangulation': TestGeoTriangulation
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
            'success_rate': success_rate
        }
        
        return result
    
    def run_all_modules(self):
        """Ejecuta tests de todos los módulos."""
        print("🚁 SISTEMA DE TESTING DE GEO")
        print("=" * 60)
        
        # Ejecutar cada módulo
        for module_name in self.test_modules.keys():
            try:
                self.run_single_module(module_name)
            except Exception as e:
                print(f"❌ {module_name}: ERROR - {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Imprime resumen de resultados."""
        if not self.results:
            print("❌ No hay resultados para mostrar")
            return
        
        print(f"\n📈 ESTADÍSTICAS:")
        total_modules = len(self.results)
        successful_modules = sum(1 for r in self.results.values() if r['success_rate'] == 100)
        
        print(f"   Total de archivos: {total_modules}")
        print(f"   Exitosos: {successful_modules} ({(successful_modules/total_modules)*100:.1f}%)")
        print(f"   Fallidos: {total_modules - successful_modules}")
        print(f"   Tasa de éxito: {(successful_modules/total_modules)*100:.1f}%")
        
        if successful_modules == total_modules:
            print(f"\n🎉 ¡TODOS LOS TESTS DE GEO PASAN! 🎉")
        else:
            print(f"\n❌ {total_modules - successful_modules}/{total_modules} MÓDULOS CON FALLOS")


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description="Ejecutor de tests para el módulo /geo")
    parser.add_argument('module', nargs='?', 
                       choices=['geo_correlator', 'geo_triangulation'],
                       help='Módulo específico a testear')
    
    args = parser.parse_args()
    
    # Crear ejecutor
    runner = GeoTestRunner()
    
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