#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para MissionValidator del proyecto Drone Geo Analysis.

Estos tests verifican la funcionalidad del validador de seguridad:
- validate_mission_safety: Validación completa de seguridad de misión
- validate_mission_duration: Validación de duración de misión
- Validaciones de altitud, distancia y coordenadas
"""

import sys
import os
import unittest

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.mission_validator import validate_mission_safety, validate_mission_duration


class TestMissionValidator(unittest.TestCase):
    """Tests para el validador de misiones."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        self.valid_mission = {
            "mission_name": "Test Mission",
            "waypoints": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "altitude": 50,
                    "duration": 30
                },
                {
                    "latitude": 40.7129,
                    "longitude": -74.0061,
                    "altitude": 60,
                    "duration": 45
                }
            ],
            "estimated_duration": 2  # minutos
        }
        
        self.invalid_altitude_mission = {
            "mission_name": "High Altitude Mission",
            "waypoints": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "altitude": 150,  # Excede límite legal
                    "duration": 30
                }
            ]
        }
        
        self.invalid_coordinates_mission = {
            "mission_name": "Invalid Coords Mission",
            "waypoints": [
                {
                    "latitude": 95.0,  # Latitud inválida
                    "longitude": -200.0,  # Longitud inválida
                    "altitude": 50,
                    "duration": 30
                }
            ]
        }
    
    def test_validate_mission_safety_valid_mission(self):
        """Test: Validación de misión completamente válida."""
        warnings = validate_mission_safety(self.valid_mission)
        
        self.assertIsInstance(warnings, list)
        # Una misión válida puede tener pocas o ninguna advertencia
        print(f"✓ test_validate_mission_safety_valid_mission: EXITOSO ({len(warnings)} advertencias)")
    
    def test_validate_mission_safety_no_waypoints(self):
        """Test: Misión sin waypoints."""
        empty_mission = {"mission_name": "Empty Mission", "waypoints": []}
        
        warnings = validate_mission_safety(empty_mission)
        
        self.assertIn("Misión sin waypoints definidos", warnings)
        print("✓ test_validate_mission_safety_no_waypoints: EXITOSO")
    
    def test_validate_mission_safety_missing_waypoints(self):
        """Test: Misión sin campo waypoints."""
        mission_no_waypoints = {"mission_name": "No Waypoints Mission"}
        
        warnings = validate_mission_safety(mission_no_waypoints)
        
        self.assertIn("Misión sin waypoints definidos", warnings)
        print("✓ test_validate_mission_safety_missing_waypoints: EXITOSO")
    
    def test_validate_mission_safety_high_altitude(self):
        """Test: Waypoint con altitud excesiva."""
        warnings = validate_mission_safety(self.invalid_altitude_mission)
        
        # Debe contener advertencia sobre altitud
        altitude_warnings = [w for w in warnings if "altitud excede" in w.lower()]
        self.assertGreater(len(altitude_warnings), 0)
        print("✓ test_validate_mission_safety_high_altitude: EXITOSO")
    
    def test_validate_mission_safety_low_altitude(self):
        """Test: Waypoint con altitud muy baja."""
        low_altitude_mission = {
            "mission_name": "Low Altitude Mission",
            "waypoints": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "altitude": 0,  # Altitud muy baja
                    "duration": 30
                }
            ]
        }
        
        warnings = validate_mission_safety(low_altitude_mission)
        
        # Debe contener advertencia sobre altitud baja
        altitude_warnings = [w for w in warnings if "muy baja" in w.lower()]
        self.assertGreater(len(altitude_warnings), 0)
        print("✓ test_validate_mission_safety_low_altitude: EXITOSO")
    
    def test_validate_mission_safety_invalid_coordinates(self):
        """Test: Coordenadas inválidas."""
        warnings = validate_mission_safety(self.invalid_coordinates_mission)
        
        # Debe contener advertencias sobre coordenadas inválidas
        lat_warnings = [w for w in warnings if "latitud inválida" in w.lower()]
        lng_warnings = [w for w in warnings if "longitud inválida" in w.lower()]
        
        self.assertGreater(len(lat_warnings), 0)
        self.assertGreater(len(lng_warnings), 0)
        print("✓ test_validate_mission_safety_invalid_coordinates: EXITOSO")
    
    def test_validate_mission_safety_long_distance(self):
        """Test: Distancia muy larga entre waypoints."""
        long_distance_mission = {
            "mission_name": "Long Distance Mission",
            "waypoints": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "altitude": 50,
                    "duration": 30
                },
                {
                    "latitude": 41.0000,  # ~30km de distancia
                    "longitude": -74.5000,
                    "altitude": 50,
                    "duration": 30
                }
            ]
        }
        
        warnings = validate_mission_safety(long_distance_mission)
        
        # Debe contener advertencia sobre distancia larga
        distance_warnings = [w for w in warnings if "distancia muy larga" in w.lower()]
        self.assertGreater(len(distance_warnings), 0)
        print("✓ test_validate_mission_safety_long_distance: EXITOSO")
    
    def test_validate_mission_duration_normal(self):
        """Test: Validación de duración normal."""
        warnings = validate_mission_duration(self.valid_mission)
        
        self.assertIsInstance(warnings, list)
        # Una duración de 2 minutos es normal, no debería generar advertencias
        duration_warnings = [w for w in warnings if "duración excesiva" in w.lower()]
        self.assertEqual(len(duration_warnings), 0)
        print("✓ test_validate_mission_duration_normal: EXITOSO")
    
    def test_validate_mission_duration_excessive(self):
        """Test: Duración excesiva de misión."""
        long_mission = {
            "mission_name": "Long Mission",
            "estimated_duration": 150,  # 2.5 horas
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 50, "duration": 30}
            ]
        }
        
        warnings = validate_mission_duration(long_mission)
        
        # Debe contener advertencia sobre duración excesiva
        duration_warnings = [w for w in warnings if "duración excesiva" in w.lower()]
        self.assertGreater(len(duration_warnings), 0)
        print("✓ test_validate_mission_duration_excessive: EXITOSO")
    
    def test_validate_mission_duration_discrepancy(self):
        """Test: Discrepancia entre duración estimada y waypoints."""
        discrepant_mission = {
            "mission_name": "Discrepant Mission",
            "estimated_duration": 10,  # 10 minutos
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 50, "duration": 1800}  # 30 min
            ]
        }
        
        warnings = validate_mission_duration(discrepant_mission)
        
        # Debe contener advertencia sobre discrepancia
        discrepancy_warnings = [w for w in warnings if "discrepancia" in w.lower()]
        self.assertGreater(len(discrepancy_warnings), 0)
        print("✓ test_validate_mission_duration_discrepancy: EXITOSO")
    
    def test_validate_mission_duration_missing_duration(self):
        """Test: Misión sin duración estimada."""
        mission_no_duration = {
            "mission_name": "No Duration Mission",
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 50, "duration": 30}
            ]
        }
        
        warnings = validate_mission_duration(mission_no_duration)
        
        # Debería manejar el caso sin duración estimada
        self.assertIsInstance(warnings, list)
        print("✓ test_validate_mission_duration_missing_duration: EXITOSO")
    
    def test_validate_mission_multiple_waypoints(self):
        """Test: Validación de misión con múltiples waypoints."""
        multi_waypoint_mission = {
            "mission_name": "Multi Waypoint Mission",
            "waypoints": [
                {"latitude": 40.7128, "longitude": -74.0060, "altitude": 50, "duration": 30},
                {"latitude": 40.7129, "longitude": -74.0061, "altitude": 60, "duration": 30},
                {"latitude": 40.7130, "longitude": -74.0062, "altitude": 70, "duration": 30},
                {"latitude": 40.7131, "longitude": -74.0063, "altitude": 80, "duration": 30}
            ]
        }
        
        warnings = validate_mission_safety(multi_waypoint_mission)
        
        # Cada waypoint debe ser validado individualmente
        self.assertIsInstance(warnings, list)
        print("✓ test_validate_mission_multiple_waypoints: EXITOSO")


if __name__ == '__main__':
    print("🧪 EJECUTANDO TESTS DE MISSION VALIDATOR")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMissionValidator)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE MISSION VALIDATOR:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE MISSION VALIDATOR PASAN! 🎉") 