"""Tests para parrot_anafi_controller.py"""

import pytest
from unittest.mock import MagicMock, patch
from src.drones.parrot_anafi_controller import ParrotAnafiController

class TestParrotAnafiController:
    @pytest.fixture
    def controller(self):
        return ParrotAnafiController()
    
    def test_init(self, controller):
        """Test de inicialización del controlador Parrot ANAFI."""
        assert controller is not None
        assert controller.connected is False
        assert controller.ip_address == "10.202.0.1"
        assert controller.battery_level == 100
        assert controller.gps_satellites == 0
        assert controller.is_flying is False
    
    def test_connect_success(self, controller):
        """Test de conexión exitosa con simulación."""
        # Como no tenemos Olympe instalado, debería usar simulación
        result = controller.connect()
        assert result is True
        assert controller.connected is True
    
    def test_disconnect(self, controller):
        """Test de desconexión."""
        controller.connected = True
        result = controller.disconnect()
        assert result is True
        assert controller.connected is False
    
    def test_take_off_not_connected(self, controller):
        """Test de despegue sin conexión."""
        result = controller.take_off(10.0)
        assert result is False
    
    def test_take_off_connected(self, controller):
        """Test de despegue con conexión."""
        controller.connected = True
        result = controller.take_off(10.0)
        assert result is True
        assert controller.is_flying is True
        assert controller.current_position["altitude"] == 10.0
    
    def test_land(self, controller):
        """Test de aterrizaje."""
        controller.connected = True
        controller.is_flying = True
        result = controller.land()
        assert result is True
        assert controller.is_flying is False
        assert controller.current_position["altitude"] == 0
    
    def test_move_to(self, controller):
        """Test de movimiento a coordenadas."""
        controller.connected = True
        controller.set_home(40.7128, -74.0060)
        result = controller.move_to(40.7140, -74.0050, 50.0)
        assert result is True
        assert controller.current_position["latitude"] == 40.7140
        assert controller.current_position["longitude"] == -74.0050
        assert controller.current_position["altitude"] == 50.0

    def test_move_to_rejected_without_home(self, controller):
        """Sin home registrada ningún comando de movimiento se acepta (fail-closed)."""
        controller.connected = True
        assert controller.move_to(40.7140, -74.0050, 50.0) is False

    def test_move_to_rejected_outside_envelope(self, controller):
        controller.connected = True
        controller.set_home(40.7128, -74.0060)
        assert controller.move_to(40.7140, -74.0050, 500.0) is False   # altitude
        assert controller.move_to(40.7589, -73.9851, 50.0) is False    # ~4.7 km from home
    
    def test_capture_image(self, controller):
        """Test de captura de imagen."""
        controller.connected = True
        image_path = controller.capture_image()
        assert image_path != ""
        assert "anafi_image" in image_path
    
    def test_start_video_stream(self, controller):
        """Test de inicio de stream de video."""
        controller.connected = True
        stream_url = controller.start_video_stream()
        assert stream_url != ""
        assert controller.is_streaming is True
    
    def test_stop_video_stream(self, controller):
        """Test de detención de stream de video."""
        controller.connected = True
        controller.is_streaming = True
        result = controller.stop_video_stream()
        assert result is True
        assert controller.is_streaming is False
    
    def test_get_telemetry(self, controller):
        """Test de obtención de telemetría."""
        controller.connected = True
        telemetry = controller.get_telemetry()
        
        assert "position" in telemetry
        assert "attitude" in telemetry
        assert "speed" in telemetry
        assert "battery" in telemetry
        assert "gps" in telemetry
        assert "status" in telemetry
        
        assert telemetry["status"]["connected"] is True
    
    def test_execute_mission(self, controller):
        """Test de ejecución de misión."""
        controller.connected = True
        
        mission_data = {
            "waypoints": [
                {
                    "latitude": 40.7135,
                    "longitude": -74.0055,
                    "altitude": 50.0,
                    "actions": [
                        {"type": "capture_image"},
                        {"type": "hover", "duration": 2}
                    ]
                },
                {
                    "latitude": 40.7140,
                    "longitude": -74.0050,
                    "altitude": 60.0,
                    "actions": [
                        {"type": "start_video"}
                    ]
                }
            ]
        }
        
        from src.safety.approval import MissionGate
        gate = MissionGate()
        home = (40.7128, -74.0060)
        review = gate.review("m1", mission_data, home)
        assert review.ok, review.violations
        token = gate.approve("m1", mission_data, home, review.mission_hash, "t")
        approved = gate.redeem(token, "m1", mission_data, home)
        result = controller.execute_mission(approved)
        assert result is True

    def test_execute_mission_refuses_plain_dict(self, controller):
        from src.safety.approval import ApprovalError
        controller.connected = True
        with pytest.raises(ApprovalError):
            controller.execute_mission({"waypoints": [{"latitude": 40.7135, "longitude": -74.0055, "altitude": 50.0}]})
