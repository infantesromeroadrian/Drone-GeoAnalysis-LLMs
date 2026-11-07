#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clase base abstracta para todos los controladores de drones.
"""

from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, List, Tuple, Optional

from src.safety.approval import ApprovedMission
from src.safety.envelope import SafetyEnvelope, check_point

logger = logging.getLogger(__name__)

class BaseDrone(ABC):
    """
    Abstract Factory pattern for drone controllers.
    
    This class implements the Abstract Factory design pattern to provide
    a uniform interface for controlling different drone manufacturers' hardware.
    
    Pattern Components:
    - BaseDrone: Abstract Factory interface defining common operations
    - Concrete Implementations: ParrotAnafiController, DJIDroneController, etc.
    - Products: Consistent drone control operations across hardware
    
    Design Rationale:
    - Enables easy integration of new drone manufacturers
    - Provides consistent API regardless of underlying hardware
    - Facilitates testing with mock implementations
    - Supports hot-swapping of drone types in missions
    
    Usage:
        drone = ParrotAnafiController()  # Concrete factory
        drone.connect()
        drone.take_off(50)
        drone.capture_image()
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """Establece conexión con el dron."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Desconecta del dron."""
        pass
    
    # Envelope enforced on every motion command, independently of any mission. Override per
    # instance/class (tests) or via SAFETY_ENVELOPE_FILE. ``home_position`` is set when a mission
    # is authorised or on take-off; without it no motion command is accepted (fail-closed).
    safety_envelope: Optional[SafetyEnvelope] = None
    home_position: Optional[Tuple[float, float]] = None

    def _envelope(self) -> SafetyEnvelope:
        if self.safety_envelope is None:
            BaseDrone.safety_envelope = SafetyEnvelope.from_env()
        return self.safety_envelope  # type: ignore[return-value]

    def set_home(self, latitude: float, longitude: float) -> None:
        """Record the launch point that anchors the geofence."""
        self.home_position = (float(latitude), float(longitude))

    def _command_violations(self, latitude: float, longitude: float, altitude: float,
                            ground_ok: bool = False):
        if self.home_position is None:
            from src.safety.envelope import Violation
            return [Violation(code="no_home", message="home position not set")]
        return check_point(latitude, longitude, altitude, self.home_position, self._envelope(), ground_ok)

    def take_off(self, altitude: float) -> bool:
        """Envelope-checked take-off. The current position becomes home if none is set."""
        pos = getattr(self, "current_position", None)
        if self.home_position is None and pos:
            self.set_home(pos["latitude"], pos["longitude"])
        if pos:
            bad = self._command_violations(pos["latitude"], pos["longitude"], altitude)
            if bad:
                logger.error("take_off rejected by safety envelope: %s", [v.message for v in bad])
                return False
        return self._do_take_off(altitude)

    def move_to(self, latitude: float, longitude: float, altitude: float, *, ground: bool = False) -> bool:
        """Envelope-checked motion command: the last line of defence before the controller.

        ``ground=True`` (land/takeoff waypoints only) waives the minimum-altitude rule.
        """
        bad = self._command_violations(latitude, longitude, altitude, ground_ok=ground)
        if bad:
            logger.error("move_to rejected by safety envelope: %s", [v.message for v in bad])
            return False
        return self._do_move_to(latitude, longitude, altitude)

    def execute_mission(self, mission: ApprovedMission) -> bool:
        """Execute an ``ApprovedMission`` (anything else is refused)."""
        approved = ApprovedMission.require(mission)
        self.set_home(*approved.home)
        return self._execute_approved(approved.waypoints)

    @abstractmethod
    def _do_take_off(self, altitude: float) -> bool:
        """Controller-specific take-off (called only after the envelope check)."""
        pass

    @abstractmethod
    def _do_move_to(self, latitude: float, longitude: float, altitude: float) -> bool:
        """Controller-specific motion (called only after the envelope check)."""
        pass

    @abstractmethod
    def _execute_approved(self, waypoints: List[Dict[str, Any]]) -> bool:
        """Controller-specific mission loop over already-approved waypoints."""
        pass

    @abstractmethod
    def land(self) -> bool:
        """Aterriza el dron."""
        pass
    
    @abstractmethod
    def capture_image(self) -> str:
        """Captura una imagen y devuelve la ruta al archivo."""
        pass
    
    @abstractmethod
    def start_video_stream(self) -> str:
        """Inicia la transmisión de video y devuelve el URL del stream."""
        pass
    
    @abstractmethod
    def stop_video_stream(self) -> bool:
        """Detiene la transmisión de video."""
        pass
    
    @abstractmethod
    def get_telemetry(self) -> Dict[str, Any]:
        """Obtiene datos telemétricos del dron."""
        pass
