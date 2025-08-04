#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests básicos para MissionUtils del proyecto Drone Geo Analysis.

Estos tests verifican las funciones de utilidades matemáticas y geográficas:
- calculate_distance: Cálculo de distancia entre puntos GPS
- calculate_area_center: Cálculo del centro de un área
- calculate_total_mission_distance: Distancia total de misión
- estimate_flight_time: Estimación de tiempo de vuelo
- is_point_in_boundaries: Verificación de punto dentro de límites
"""

import sys
import os
import unittest
import math

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.mission_utils import (
    calculate_distance,
    calculate_area_center,
    calculate_total_mission_distance,
    estimate_flight_time,
    is_point_in_boundaries
)
from src.models.mission_models import MissionArea


class TestMissionUtils(unittest.TestCase):
    """Tests para las utilidades de misiones."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        # Coordenadas de Nueva York
        self.ny_coords = (40.7128, -74.0060)
        self.ny_coords_2 = (40.7129, -74.0061)
        
        # Waypoints de prueba
        self.sample_waypoints = [
            {"latitude": 40.7128, "longitude": -74.0060},
            {"latitude": 40.7129, "longitude": -74.0061},
            {"latitude": 40.7130, "longitude": -74.0062}
        ]
        
        # Área de prueba
        self.test_boundaries = [
            (40.7120, -74.0070),
            (40.7130, -74.0070),
            (40.7130, -74.0050),
            (40.7120, -74.0050)
        ]
    
    def test_calculate_distance_same_point(self):
        """Test: Distancia entre el mismo punto debe ser 0."""
        distance = calculate_distance(self.ny_coords, self.ny_coords)
        
        self.assertEqual(distance, 0.0)
        print("✓ test_calculate_distance_same_point: EXITOSO")
    
    def test_calculate_distance_different_points(self):
        """Test: Distancia entre puntos diferentes."""
        distance = calculate_distance(self.ny_coords, self.ny_coords_2)
        
        # La distancia debe ser positiva y razonable (aproximadamente 100-200m)
        self.assertGreater(distance, 0)
        self.assertLess(distance, 1000)  # Menos de 1km para puntos tan cercanos
        print("✓ test_calculate_distance_different_points: EXITOSO")
    
    def test_calculate_distance_known_values(self):
        """Test: Distancia entre coordenadas conocidas."""
        # Distancia aproximada entre Times Square y Central Park (NY)
        times_square = (40.7580, -73.9855)
        central_park = (40.7829, -73.9654)
        
        distance = calculate_distance(times_square, central_park)
        
        # Distancia aproximada conocida: ~3.2km
        self.assertGreater(distance, 2500)  # Al menos 2.5km
        self.assertLess(distance, 4000)     # Menos de 4km
        print("✓ test_calculate_distance_known_values: EXITOSO")
    
    def test_calculate_area_center_with_boundaries(self):
        """Test: Cálculo del centro de área con boundaries."""
        area = MissionArea(
            name="Test Area",
            boundaries=self.test_boundaries
        )
        
        center = calculate_area_center(area)
        
        self.assertIsNotNone(center)
        self.assertEqual(len(center), 2)  # (lat, lng)
        
        # El centro debe estar aproximadamente en el medio
        expected_lat = sum(coord[0] for coord in self.test_boundaries) / len(self.test_boundaries)
        expected_lng = sum(coord[1] for coord in self.test_boundaries) / len(self.test_boundaries)
        
        self.assertAlmostEqual(center[0], expected_lat, places=5)
        self.assertAlmostEqual(center[1], expected_lng, places=5)
        print("✓ test_calculate_area_center_with_boundaries: EXITOSO")
    
    def test_calculate_area_center_no_boundaries_with_pois(self):
        """Test: Cálculo del centro sin boundaries pero con POIs."""
        area = MissionArea(
            name="Test Area",
            boundaries=[],
            points_of_interest=[
                {"name": "POI1", "coordinates": (40.7128, -74.0060)}
            ]
        )
        
        center = calculate_area_center(area)
        
        self.assertEqual(center, (40.7128, -74.0060))
        print("✓ test_calculate_area_center_no_boundaries_with_pois: EXITOSO")
    
    def test_calculate_area_center_empty_area(self):
        """Test: Cálculo del centro de área vacía."""
        area = MissionArea(
            name="Empty Area",
            boundaries=[],
            points_of_interest=[]
        )
        
        center = calculate_area_center(area)
        
        self.assertIsNone(center)
        print("✓ test_calculate_area_center_empty_area: EXITOSO")
    
    def test_calculate_total_mission_distance_normal(self):
        """Test: Cálculo de distancia total de misión normal."""
        total_distance = calculate_total_mission_distance(self.sample_waypoints)
        
        self.assertGreater(total_distance, 0)
        self.assertIsInstance(total_distance, float)
        print("✓ test_calculate_total_mission_distance_normal: EXITOSO")
    
    def test_calculate_total_mission_distance_single_waypoint(self):
        """Test: Distancia total con un solo waypoint."""
        single_waypoint = [{"latitude": 40.7128, "longitude": -74.0060}]
        
        total_distance = calculate_total_mission_distance(single_waypoint)
        
        self.assertEqual(total_distance, 0.0)
        print("✓ test_calculate_total_mission_distance_single_waypoint: EXITOSO")
    
    def test_calculate_total_mission_distance_empty(self):
        """Test: Distancia total con lista vacía."""
        total_distance = calculate_total_mission_distance([])
        
        self.assertEqual(total_distance, 0.0)
        print("✓ test_calculate_total_mission_distance_empty: EXITOSO")
    
    def test_estimate_flight_time_normal(self):
        """Test: Estimación de tiempo de vuelo normal."""
        distance = 1000.0  # 1km
        speed = 10.0  # 10 m/s
        
        flight_time = estimate_flight_time(distance, speed)
        
        self.assertEqual(flight_time, 100.0)  # 1000/10 = 100 segundos
        print("✓ test_estimate_flight_time_normal: EXITOSO")
    
    def test_estimate_flight_time_zero_distance(self):
        """Test: Tiempo de vuelo con distancia cero."""
        flight_time = estimate_flight_time(0.0, 10.0)
        
        self.assertEqual(flight_time, 0.0)
        print("✓ test_estimate_flight_time_zero_distance: EXITOSO")
    
    def test_estimate_flight_time_zero_speed(self):
        """Test: Tiempo de vuelo con velocidad cero."""
        flight_time = estimate_flight_time(1000.0, 0.0)
        
        self.assertEqual(flight_time, 0.0)
        print("✓ test_estimate_flight_time_zero_speed: EXITOSO")
    
    def test_is_point_in_boundaries_inside(self):
        """Test: Punto dentro de los límites."""
        # Punto en el centro del área de prueba
        center_point = (40.7125, -74.0060)
        
        result = is_point_in_boundaries(center_point, self.test_boundaries)
        
        self.assertTrue(result)
        print("✓ test_is_point_in_boundaries_inside: EXITOSO")
    
    def test_is_point_in_boundaries_outside(self):
        """Test: Punto fuera de los límites."""
        # Punto claramente fuera del área
        outside_point = (40.8000, -74.0060)
        
        result = is_point_in_boundaries(outside_point, self.test_boundaries)
        
        self.assertFalse(result)
        print("✓ test_is_point_in_boundaries_outside: EXITOSO")
    
    def test_is_point_in_boundaries_insufficient_boundaries(self):
        """Test: Verificación con boundaries insuficientes."""
        # Menos de 3 puntos no forman un polígono
        insufficient_boundaries = [(40.7120, -74.0070), (40.7130, -74.0070)]
        
        result = is_point_in_boundaries((40.7125, -74.0060), insufficient_boundaries)
        
        self.assertFalse(result)
        print("✓ test_is_point_in_boundaries_insufficient_boundaries: EXITOSO")


if __name__ == '__main__':
    print("🧪 EJECUTANDO TESTS DE MISSION UTILS")
    print("=" * 60)
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMissionUtils)
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Mostrar resumen
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📈 ESTADÍSTICAS DE MISSION UTILS:")
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
        print(f"\n🎉 ¡TODOS LOS TESTS DE MISSION UTILS PASAN! 🎉") 