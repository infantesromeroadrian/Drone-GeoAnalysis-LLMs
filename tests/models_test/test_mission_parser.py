#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para MissionParser del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad del parser de respuestas JSON:
- extract_json_from_response: Extracción robusta de JSON desde respuestas LLM
- Manejo de diferentes formatos de respuesta
- Casos de error y recuperación
"""

import sys
import os
import unittest
import json

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.mission_parser import extract_json_from_response


class TestMissionParser(unittest.TestCase):
    """Tests para el parser de misiones."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        self.valid_json = {
            "mission_name": "Test Mission",
            "description": "A test mission",
            "waypoints": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "altitude": 100
                }
            ]
        }
        
    def test_extract_json_direct_parse(self):
        """Test: Parseo directo de JSON válido."""
        json_string = json.dumps(self.valid_json)
        
        result = extract_json_from_response(json_string)
        
        self.assertEqual(result, self.valid_json)
        print("✓ test_extract_json_direct_parse: EXITOSO")
    
    def test_extract_json_markdown_format(self):
        """Test: Extracción de JSON desde bloque markdown."""
        markdown_response = f"""
        Aquí está la misión generada:
        
        ```json
        {json.dumps(self.valid_json, indent=2)}
        ```
        
        Esta misión cumple con los requisitos.
        """
        
        result = extract_json_from_response(markdown_response)
        
        self.assertEqual(result, self.valid_json)
        print("✓ test_extract_json_markdown_format: EXITOSO")
    
    def test_extract_json_with_extra_text(self):
        """Test: Extracción de JSON con texto adicional."""
        response_with_text = f"""
        He analizado tu solicitud y he generado la siguiente misión:
        
        {json.dumps(self.valid_json)}
        
        Espero que esta misión sea de tu agrado.
        """
        
        result = extract_json_from_response(response_with_text)
        
        self.assertEqual(result, self.valid_json)
        print("✓ test_extract_json_with_extra_text: EXITOSO")
    
    def test_extract_json_regex_extraction(self):
        """Test: Extracción usando regex cuando no hay markdown."""
        response = f"""
        La misión solicitada es la siguiente:
        {json.dumps(self.valid_json)}
        Fin de la respuesta.
        """
        
        result = extract_json_from_response(response)
        
        self.assertEqual(result, self.valid_json)
        print("✓ test_extract_json_regex_extraction: EXITOSO")
    
    def test_extract_json_with_whitespace(self):
        """Test: Manejo de espacios en blanco."""
        json_with_whitespace = f"""
        
        
        {json.dumps(self.valid_json)}
        
        
        """
        
        result = extract_json_from_response(json_with_whitespace)
        
        self.assertEqual(result, self.valid_json)
        print("✓ test_extract_json_with_whitespace: EXITOSO")
    
    def test_extract_json_case_insensitive_markdown(self):
        """Test: Markdown case insensitive."""
        markdown_response = f"""
        ```JSON
        {json.dumps(self.valid_json)}
        ```
        """
        
        result = extract_json_from_response(markdown_response)
        
        self.assertEqual(result, self.valid_json)
        print("✓ test_extract_json_case_insensitive_markdown: EXITOSO")
    
    def test_extract_json_nested_braces(self):
        """Test: JSON con llaves anidadas complejas."""
        complex_json = {
            "mission": {
                "details": {
                    "name": "Complex Mission",
                    "config": {"param1": "value1", "param2": {"nested": True}}
                }
            }
        }
        
        response = f"Misión: {json.dumps(complex_json)} - Completada"
        
        result = extract_json_from_response(response)
        
        self.assertEqual(result, complex_json)
        print("✓ test_extract_json_nested_braces: EXITOSO")
    
    def test_extract_json_invalid_json_raises_error(self):
        """Test: JSON inválido debe lanzar ValueError."""
        invalid_json_response = "Esta es una respuesta sin JSON válido"
        
        with self.assertRaises(ValueError) as context:
            extract_json_from_response(invalid_json_response)
        
        self.assertIn("No se pudo extraer JSON válido", str(context.exception))
        print("✓ test_extract_json_invalid_json_raises_error: EXITOSO")
    
    def test_extract_json_malformed_json_raises_error(self):
        """Test: JSON malformado debe lanzar ValueError."""
        malformed_json = """
        {
            "mission_name": "Test",
            "description": "Missing closing brace"
        """
        
        with self.assertRaises(ValueError):
            extract_json_from_response(malformed_json)
        
        print("✓ test_extract_json_malformed_json_raises_error: EXITOSO")
    
    def test_extract_json_empty_string(self):
        """Test: String vacío debe lanzar ValueError."""
        with self.assertRaises(ValueError):
            extract_json_from_response("")
        
        print("✓ test_extract_json_empty_string: EXITOSO")
    
    def test_extract_json_only_braces(self):
        """Test: Solo llaves sin contenido válido."""
        with self.assertRaises(ValueError):
            extract_json_from_response("{}")
        
        # Nota: {} es técnicamente JSON válido, pero podría no ser útil
        # Dependiendo de la implementación, esto podría pasar o fallar
        print("✓ test_extract_json_only_braces: EXITOSO")
    
    def test_extract_json_multiple_json_blocks(self):
        """Test: Múltiples bloques JSON - debe tomar el primero."""
        multiple_json_response = f"""
        Primer JSON:
        ```json
        {json.dumps(self.valid_json)}
        ```
        
        Segundo JSON (que debería ser ignorado):
        ```json
        {json.dumps({"otro": "json"})}
        ```
        """
        
        result = extract_json_from_response(multiple_json_response)
        
        self.assertEqual(result, self.valid_json)
        print("✓ test_extract_json_multiple_json_blocks: EXITOSO")


if __name__ == '__main__':
    print("🧪 EJECUTANDO TESTS DE MISSION PARSER")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMissionParser)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE MISSION PARSER:")
    print(f"   Tests ejecutados: {total_tests}")
    print(f"   Exitosos: {passed}")
    print(f"   Fallidos: {failures}")
    print(f"   Errores: {errors}")
    print(f"   Tasa de éxito: {(passed/total_tests)*100:.1f}%")
    
    if failures > 0 or errors > 0:
        print(f"\n❌ FALLOS DETECTADOS:")
        for failure in result.failures:
            print(f"   • {failure[0]}")
        for error in result.errors:
            print(f"   • {error[0]}")
    else:
        print(f"\n🎉 ¡TODOS LOS TESTS DE MISSION PARSER PASAN! 🎉") 