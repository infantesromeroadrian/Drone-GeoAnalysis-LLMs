#!/usr/bin/env python3
"""Tests for dji_controller.py (simulation-only stub)."""
import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.drones.dji_controller import DJIDroneController


class TestDJIDroneController:
    @pytest.fixture
    def drone(self):
        return DJIDroneController(simulation_mode=True)

    def test_init_without_simulation_raises(self):
        """Default instantiation must fail loudly — see ADR-003."""
        with pytest.raises(NotImplementedError, match="DJI SDK"):
            DJIDroneController()

    def test_init_explicit_real_mode_raises(self):
        """Explicit simulation_mode=False must also fail."""
        with pytest.raises(NotImplementedError, match="ADR-003"):
            DJIDroneController(simulation_mode=False)

    def test_initialization(self, drone):
        assert drone.connected is False
        assert drone.simulation_mode is True
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

    def test_post_init_flag_toggle_blocked(self, drone):
        """Toggling simulation_mode after init must not unlock real-mode methods."""
        drone.simulation_mode = False
        with pytest.raises(NotImplementedError):
            drone.connect()
