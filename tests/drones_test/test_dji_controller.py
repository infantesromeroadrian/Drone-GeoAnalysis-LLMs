#!/usr/bin/env python3
"""Tests para dji_controller.py"""
import sys, os, pytest
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.drones.dji_controller import DJIDroneController

class TestDJIDroneController:
    @pytest.fixture
    def drone(self):
        return DJIDroneController()
    
    def test_initialization(self, drone):
        assert drone.connected is False
        assert drone.current_position["latitude"] == 40.7128
    
    def test_connect_success(self, drone):
        result = drone.connect()
        assert result is True
        assert drone.connected is True
    
    def test_disconnect_success(self, drone):
        drone.connect()
        result = drone.disconnect()
        assert result is True
        assert drone.connected is False
    
    def test_takeoff_connected(self, drone):
        drone.connect()
        result = drone.take_off(50.0)
        assert result is True
    
    def test_get_telemetry_connected(self, drone):
        drone.connect()
        result = drone.get_telemetry()
        assert "battery" in result
        assert "gps" in result
