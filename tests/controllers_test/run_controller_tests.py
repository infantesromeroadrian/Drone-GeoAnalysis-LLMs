#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar todos los tests de controladores.
Proporciona un informe detallado de qué funciones pasan o fallan.
"""

import sys
import os
import pytest
import subprocess
from pathlib import Path

def run_controller_tests():
    """Ejecuta todos los tests de controladores y muestra resultados detallados"""
    
    # Obtener la ruta del directorio actual
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    
    print("🔥 SISTEMA DE TESTING DE CONTROLADORES")
    print("=" * 50)
    print(f"📁 Directorio de tests: {current_dir}")
    print(f"📁 Raíz del proyecto: {project_root}")
    print()
    
    # Lista de archivos de test a ejecutar
    test_files = [
        "test_analysis_controller.py",
        "test_drone_controller.py",
        "test_geo_controller.py",
        "test_mission_controller.py"
    ]
    
    # Verificar qué archivos de test existen
    existing_tests = []
    missing_tests = []
    
    for test_file in test_files:
        test_path = current_dir / test_file
        if test_path.exists():
            existing_tests.append(test_file)
        else:
            missing_tests.append(test_file)
    
    print("📋 ESTADO DE ARCHIVOS DE TEST:")
    print("-" * 30)
    for test_file in existing_tests:
        print(f"✅ {test_file}")
    
    for test_file in missing_tests:
        print(f"❌ {test_file} (FALTANTE)")
    
    print()
    
    if not existing_tests:
        print("❌ No se encontraron archivos de test para ejecutar")
        return
    
    # Ejecutar cada archivo de test individualmente
    results = {}
    
    for test_file in existing_tests:
        print(f"🧪 EJECUTANDO: {test_file}")
        print("-" * 40)
        
        test_path = str(current_dir / test_file)
        
        try:
            # Ejecutar pytest con verbosidad alta
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_path, 
                "-v",  # verboso
                "--tb=short",  # traceback corto
                "--no-header",  # sin header
                "-q"  # quiet
            ], 
            capture_output=True, 
            text=True, 
            cwd=str(project_root)
            )
            
            results[test_file] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if result.returncode == 0:
                print(f"✅ {test_file}: TODOS LOS TESTS PASARON")
                # Contar tests exitosos
                lines = result.stdout.split('\n')
                passed_count = 0
                for line in lines:
                    if ' PASSED' in line or '::test_' in line:
                        passed_count += 1
                        print(f"   ✓ {line.strip()}")
            else:
                print(f"❌ {test_file}: ALGUNOS TESTS FALLARON")
                print("STDOUT:")
                print(result.stdout)
                print("STDERR:")
                print(result.stderr)
            
        except Exception as e:
            print(f"💥 ERROR ejecutando {test_file}: {str(e)}")
            results[test_file] = {
                'returncode': -1,
                'error': str(e)
            }
        
        print()
    
    # Resumen final
    print("📊 RESUMEN FINAL")
    print("=" * 50)
    
    total_files = len(existing_tests)
    passed_files = 0
    failed_files = 0
    
    for test_file, result in results.items():
        if result['returncode'] == 0:
            print(f"✅ {test_file}: ÉXITO")
            passed_files += 1
        else:
            print(f"❌ {test_file}: FALLOS")
            failed_files += 1
    
    print()
    print(f"📈 ESTADÍSTICAS:")
    print(f"   Total de archivos: {total_files}")
    print(f"   Exitosos: {passed_files}")
    print(f"   Fallidos: {failed_files}")
    print(f"   Faltantes: {len(missing_tests)}")
    
    success_rate = (passed_files / total_files * 100) if total_files > 0 else 0
    print(f"   Tasa de éxito: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 ¡TODOS LOS TESTS DE CONTROLADORES PASAN! 🎉")
    elif success_rate >= 80:
        print("\n⚠️  La mayoría de tests pasan, pero algunos necesitan atención")
    else:
        print("\n🚨 Se necesita trabajo significativo en los tests")
    
    return results

def run_specific_controller_test(controller_name):
    """Ejecuta tests para un controlador específico"""
    
    test_file = f"test_{controller_name}_controller.py"
    current_dir = Path(__file__).parent
    test_path = current_dir / test_file
    
    if not test_path.exists():
        print(f"❌ Archivo de test no encontrado: {test_file}")
        return False
    
    print(f"🎯 EJECUTANDO TESTS ESPECÍFICOS: {controller_name.upper()}")
    print("=" * 50)
    
    project_root = current_dir.parent.parent
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            str(test_path), 
            "-v",
            "--tb=long",  # traceback completo para debugging
            "--no-header"
        ], 
        cwd=str(project_root),
        text=True
        )
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"💥 ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        # Ejecutar test específico
        controller_name = sys.argv[1].lower()
        run_specific_controller_test(controller_name)
    else:
        # Ejecutar todos los tests
        run_controller_tests() 