#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para MissionModels del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad de los modelos de datos:
- Waypoint: Modelo para waypoints de misión
- MissionArea: Modelo para áreas geográficas de misión  
- MissionMetadata: Metadatos para misiones
"""

import sys
import os
import unittest

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.mission_models import Waypoint, MissionArea, MissionMetadata


class TestMissionModels(unittest.TestCase):
    """Tests para los modelos de datos de misiones."""
    
    def test_waypoint_creation_basic(self):
        """Test: Creación básica de waypoint."""
        waypoint = Waypoint(
            latitude=40.7128,
            longitude=-74.0060,
            altitude=100.0
        )
        
        self.assertEqual(waypoint.latitude, 40.7128)
        self.assertEqual(waypoint.longitude, -74.0060)
        self.assertEqual(waypoint.altitude, 100.0)
        self.assertEqual(waypoint.action, "navigate")  # Default
        self.assertEqual(waypoint.duration, 0.0)  # Default
        self.assertEqual(waypoint.description, "")  # Default
        print("✓ test_waypoint_creation_basic: EXITOSO")
    
    def test_waypoint_creation_complete(self):
        """Test: Creación completa de waypoint con todos los parámetros."""
        waypoint = Waypoint(
            latitude=40.7128,
            longitude=-74.0060,
            altitude=100.0,
            action="scan",
            duration=30.0,
            description="Punto de escaneo principal"
        )
        
        self.assertEqual(waypoint.latitude, 40.7128)
        self.assertEqual(waypoint.longitude, -74.0060)
        self.assertEqual(waypoint.altitude, 100.0)
        self.assertEqual(waypoint.action, "scan")
        self.assertEqual(waypoint.duration, 30.0)
        self.assertEqual(waypoint.description, "Punto de escaneo principal")
        print("✓ test_waypoint_creation_complete: EXITOSO")
    
    def test_mission_area_creation_basic(self):
        """Test: Creación básica de área de misión."""
        boundaries = [(40.7128, -74.0060), (40.7129, -74.0061), (40.7127, -74.0059)]
        
        area = MissionArea(
            name="Test Area",
            boundaries=boundaries
        )
        
        self.assertEqual(area.name, "Test Area")
        self.assertEqual(area.boundaries, boundaries)
        self.assertEqual(area.restrictions, [])  # Default
        self.assertEqual(area.points_of_interest, [])  # Default
        print("✓ test_mission_area_creation_basic: EXITOSO")
    
    def test_mission_area_creation_complete(self):
        """Test: Creación completa de área de misión."""
        boundaries = [(40.7128, -74.0060), (40.7129, -74.0061), (40.7127, -74.0059)]
        restrictions = ["no_fly_zone", "altitude_limit_50m"]
        pois = [{"name": "Building A", "coordinates": (40.7128, -74.0060)}]
        
        area = MissionArea(
            name="Manhattan Area",
            boundaries=boundaries,
            restrictions=restrictions,
            points_of_interest=pois
        )
        
        self.assertEqual(area.name, "Manhattan Area")
        self.assertEqual(area.boundaries, boundaries)
        self.assertEqual(area.restrictions, restrictions)
        self.assertEqual(area.points_of_interest, pois)
        print("✓ test_mission_area_creation_complete: EXITOSO")
    
    def test_mission_metadata_creation(self):
        """Test: Creación de metadatos de misión."""
        metadata = MissionMetadata(
            mission_id="mission_123",
            created_at="2024-01-01T10:00:00",
            status="planned",
            area_name="Test Area",
            original_command="patrol the perimeter",
            llm_provider="openai",
            llm_model="gpt-4"
        )
        
        self.assertEqual(metadata.mission_id, "mission_123")
        self.assertEqual(metadata.created_at, "2024-01-01T10:00:00")
        self.assertEqual(metadata.status, "planned")
        self.assertEqual(metadata.area_name, "Test Area")
        self.assertEqual(metadata.original_command, "patrol the perimeter")
        self.assertEqual(metadata.llm_provider, "openai")
        self.assertEqual(metadata.llm_model, "gpt-4")
        print("✓ test_mission_metadata_creation: EXITOSO")
    
    def test_waypoint_dataclass_fields(self):
        """Test: Verificar que Waypoint es dataclass correctamente."""
        waypoint = Waypoint(40.0, -74.0, 100.0)
        
        # Verificar que tiene los atributos de dataclass
        self.assertTrue(hasattr(waypoint, '__dataclass_fields__'))
        
        # Verificar campos específicos
        fields = waypoint.__dataclass_fields__
        self.assertIn('latitude', fields)
        self.assertIn('longitude', fields)
        self.assertIn('altitude', fields)
        self.assertIn('action', fields)
        self.assertIn('duration', fields)
        self.assertIn('description', fields)
        print("✓ test_waypoint_dataclass_fields: EXITOSO")
    
    def test_mission_area_dataclass_fields(self):
        """Test: Verificar que MissionArea es dataclass correctamente."""
        area = MissionArea("Test", [])
        
        # Verificar que tiene los atributos de dataclass
        self.assertTrue(hasattr(area, '__dataclass_fields__'))
        
        # Verificar campos específicos
        fields = area.__dataclass_fields__
        self.assertIn('name', fields)
        self.assertIn('boundaries', fields)
        self.assertIn('restrictions', fields)
        self.assertIn('points_of_interest', fields)
        print("✓ test_mission_area_dataclass_fields: EXITOSO")


if __name__ == '__main__':
    print("🧪 EJECUTANDO TESTS DE MISSION MODELS")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMissionModels)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE MISSION MODELS:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE MISSION MODELS PASAN! 🎉") 