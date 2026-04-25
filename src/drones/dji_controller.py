#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJI drone controller -- STUB / NOT IMPLEMENTED.

This file declares the BaseDrone interface for DJI hardware but DOES NOT
integrate with any real DJI SDK. All methods are mocks that log and return
success values without controlling actual hardware.

Real integration requires:
- DJI Mobile SDK (Android/iOS only -- no native Python binding)
- DJI Onboard SDK (drones with payload computer support -- Matrice 300, M30)
- DJI Cloud API (for fleet management)

Until integration is complete, instantiating this controller for non-test
purposes raises NotImplementedError. See ADR-003.
"""

import logging
import os
import tempfile
import time
from typing import Any

from src.drones.base_drone import BaseDrone

logger = logging.getLogger(__name__)


class DJIDroneController(BaseDrone):
    """DJI drone controller -- simulation-only stub (no real SDK integration).

    Instantiation requires ``simulation_mode=True`` explicitly. Calling with
    the default ``simulation_mode=False`` raises ``NotImplementedError`` to
    prevent accidental use in production paths. See ADR-003 for rationale
    and integration roadmap.
    """

    def __init__(self, simulation_mode: bool = False) -> None:
        """Initialise the DJI drone controller.

        Args:
            simulation_mode: Must be ``True`` until real DJI SDK integration
                ships. Defaults to ``False`` so accidental instantiation
                fails loudly.

        Raises:
            NotImplementedError: When ``simulation_mode`` is ``False``. The
                DJI SDK is not integrated; only simulated runs are valid.
        """
        if not simulation_mode:
            raise NotImplementedError(
                "DJIDroneController requires real DJI SDK integration which is "
                "not implemented. For testing/simulation, instantiate with "
                "simulation_mode=True. See ADR-003."
            )

        self.simulation_mode = simulation_mode
        self.aircraft = None
        self.flight_controller = None
        self.camera = None
        self.connected = False
        # Default coordinates (New York); can be updated dynamically via update_position.
        self.current_position = {
            "latitude": 40.7128,
            "longitude": -74.0060,
        }
        logger.warning(
            "DJIDroneController instantiated in SIMULATION MODE -- "
            "does not control real hardware"
        )

    def _ensure_simulation(self) -> None:
        """Guard against real-mode invocation post-init flag toggling."""
        if not self.simulation_mode:
            raise NotImplementedError("DJI SDK integration not implemented")

    def connect(self) -> bool:
        """Establish connection with the DJI drone (simulated)."""
        self._ensure_simulation()
        try:
            self.connected = True
            logger.info("DJI drone connection established (SIMULATION)")
            return True
        except Exception:
            logger.exception("Error connecting to DJI drone")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the DJI drone (simulated)."""
        self._ensure_simulation()
        try:
            self.connected = False
            logger.info("DJI drone disconnected (SIMULATION)")
            return True
        except Exception:
            logger.exception("Error disconnecting from DJI drone")
            return False

    def take_off(self, altitude: float) -> bool:
        """Take off to the specified altitude (simulated)."""
        self._ensure_simulation()
        try:
            if not self.connected:
                raise ConnectionError("Drone not connected")
            logger.info("DJI drone took off to %.2f meters (SIMULATION)", altitude)
            return True
        except Exception:
            logger.exception("Error during take-off")
            return False

    def land(self) -> bool:
        """Land the drone (simulated)."""
        self._ensure_simulation()
        try:
            if not self.connected:
                raise ConnectionError("Drone not connected")
            logger.info("DJI drone initiating landing (SIMULATION)")
            return True
        except Exception:
            logger.exception("Error during landing")
            return False

    def move_to(self, latitude: float, longitude: float, altitude: float) -> bool:
        """Move the drone to the specified coordinates (simulated)."""
        self._ensure_simulation()
        try:
            if not self.connected:
                raise ConnectionError("Drone not connected")
            logger.info(
                "DJI drone moving to: %.6f, %.6f, alt=%.2f (SIMULATION)",
                latitude,
                longitude,
                altitude,
            )
            return True
        except Exception:
            logger.exception("Error moving the drone")
            return False

    def capture_image(self) -> str:
        """Capture an image and return the file path (simulated)."""
        self._ensure_simulation()
        try:
            if not self.connected:
                raise ConnectionError("Drone not connected")

            # Create temp directory for images if it does not exist.
            temp_dir = os.path.join(tempfile.gettempdir(), "drone_images")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(temp_dir, f"dji_image_{timestamp}.jpg")

            # Simulation: write a placeholder file.
            with open(image_path, "w") as f:
                f.write("Simulated image payload")

            logger.info("Image captured: %s (SIMULATION)", image_path)
            return image_path
        except Exception:
            logger.exception("Error capturing image")
            return ""

    def start_video_stream(self) -> str:
        """Start the video stream and return the stream URL (simulated)."""
        self._ensure_simulation()
        try:
            if not self.connected:
                raise ConnectionError("Drone not connected")
            stream_url = "rtmp://localhost:1935/live/drone"
            logger.info("Video stream started: %s (SIMULATION)", stream_url)
            return stream_url
        except Exception:
            logger.exception("Error starting video stream")
            return ""

    def stop_video_stream(self) -> bool:
        """Stop the video stream (simulated)."""
        self._ensure_simulation()
        try:
            if not self.connected:
                raise ConnectionError("Drone not connected")
            logger.info("Video stream stopped (SIMULATION)")
            return True
        except Exception:
            logger.exception("Error stopping video stream")
            return False

    def update_position(self, latitude: float, longitude: float) -> None:
        """Update the cached drone position. Stub mode only.

        Raises:
            NotImplementedError: if ``simulation_mode`` flag was disabled
                post-init. Defense in depth -- ``__init__`` already rejects
                real mode, but a caller mutating the attribute afterwards
                must still hit the guard. Mirrors the pattern used by
                ``connect``, ``take_off``, ``move_to`` etc.
        """
        self._ensure_simulation()
        self.current_position["latitude"] = latitude
        self.current_position["longitude"] = longitude
        logger.info(
            "DJI drone repositioned to: %.6f, %.6f (SIMULATION)",
            latitude,
            longitude,
        )

    def get_telemetry(self) -> dict[str, Any]:
        """Return simulated telemetry data."""
        self._ensure_simulation()
        try:
            if not self.connected:
                raise ConnectionError("Drone not connected")
            return self._build_telemetry_data()
        except Exception:
            logger.exception("Error retrieving telemetry")
            return {}

    def _build_telemetry_data(self) -> dict[str, Any]:
        """Build the telemetry payload."""
        return {
            "battery": self._get_battery_status(),
            "gps": self._get_gps_data(),
            "altitude": 50.5,
            "speed": self._get_speed_data(),
            "orientation": self._get_orientation_data(),
            "signal_strength": 85,
            "timestamp": time.time(),
        }

    def _get_battery_status(self) -> int:
        """Return battery level (percentage)."""
        return 75

    def _get_gps_data(self) -> dict[str, Any]:
        """Return GPS data."""
        return {
            "latitude": self.current_position["latitude"],
            "longitude": self.current_position["longitude"],
            "satellites": 8,
            "signal_quality": 4,
        }

    def _get_speed_data(self) -> dict[str, float]:
        """Return speed data."""
        return {
            "horizontal": 5.2,
            "vertical": 0.0,
        }

    def _get_orientation_data(self) -> dict[str, float]:
        """Return orientation data."""
        return {
            "pitch": 0.0,
            "roll": 0.0,
            "yaw": 90.0,
        }

    def execute_mission(self, mission_data: dict[str, Any]) -> bool:
        """Execute a pre-programmed mission (simulated)."""
        self._ensure_simulation()
        try:
            if not self.connected:
                raise ConnectionError("Drone not connected")

            waypoints = mission_data.get("waypoints", [])
            if not waypoints:
                logger.error("No waypoints defined in mission")
                return False

            logger.info("Starting mission with %d waypoints", len(waypoints))
            return self._execute_waypoints(waypoints)
        except Exception:
            logger.exception("Error executing mission")
            return False

    def _execute_waypoints(self, waypoints: list[dict[str, Any]]) -> bool:
        """Execute every waypoint in the mission."""
        for i, waypoint in enumerate(waypoints):
            logger.info("Navigating to waypoint %d/%d", i + 1, len(waypoints))

            self.move_to(
                waypoint["latitude"],
                waypoint["longitude"],
                waypoint["altitude"],
            )

            self._execute_waypoint_actions(waypoint)

        logger.info("Mission completed successfully")
        return True

    def _execute_waypoint_actions(self, waypoint: dict[str, Any]) -> None:
        """Execute the actions associated with a waypoint."""
        actions = waypoint.get("actions", [])
        for action in actions:
            self._execute_single_action(action)

    def _execute_single_action(self, action: dict[str, Any]) -> None:
        """Dispatch a single waypoint action."""
        action_type = action["type"]

        if action_type == "capture_image":
            self.capture_image()
        elif action_type == "start_video":
            self.start_video_stream()
        elif action_type == "stop_video":
            self.stop_video_stream()
        elif action_type == "wait":
            time.sleep(action["duration"])
