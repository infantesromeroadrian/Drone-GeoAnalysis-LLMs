"""Background mission execution engine with progress tracking and position interpolation."""

import json
import logging
import os
import threading
import time
from typing import Dict, Any, Optional

from src.models.mission_utils import calculate_distance

logger = logging.getLogger(__name__)

SIMULATED_SPEED_MPS = 15.0
INTERPOLATION_INTERVAL = 0.3


class MissionExecutor:

    def __init__(self, drone_controller, missions_dir: str):
        self._drone = drone_controller
        self._missions_dir = missions_dir
        self._thread: Optional[threading.Thread] = None
        self._abort_flag = False
        self._status = "idle"
        self._mission_id: Optional[str] = None
        self._current_waypoint = 0
        self._total_waypoints = 0
        self._position = {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0}
        self._started_at: Optional[float] = None
        self._eta_seconds = 0.0
        self._lock = threading.Lock()
        logger.info("MissionExecutor initialized")

    def start(self, mission_id: str) -> Dict[str, Any]:
        if self._status == "flying":
            return {"success": False, "error": "A mission is already in progress"}

        mission_data = self._load_mission(mission_id)
        if not mission_data:
            return {"success": False, "error": f"Mission {mission_id} not found"}

        waypoints = mission_data.get("waypoints", [])
        if not waypoints:
            return {"success": False, "error": "Mission has no waypoints"}

        self._abort_flag = False
        self._status = "flying"
        self._mission_id = mission_id
        self._current_waypoint = 0
        self._total_waypoints = len(waypoints)
        self._started_at = time.time()

        pos = self._drone.current_position
        self._position = {"latitude": pos["latitude"], "longitude": pos["longitude"],
                          "altitude": pos.get("altitude", 0.0)}

        self._thread = threading.Thread(target=self._execute, args=(mission_data,), daemon=True)
        self._thread.start()

        logger.info("Mission execution started: %s (%d waypoints)", mission_id, len(waypoints))
        return {"success": True, "mission_id": mission_id, "waypoints": len(waypoints)}

    def abort(self) -> Dict[str, Any]:
        if self._status != "flying":
            return {"success": False, "error": "No mission in progress"}
        self._abort_flag = True
        logger.info("Mission abort requested")
        return {"success": True, "message": "Abort signal sent"}

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            progress = 0.0
            if self._total_waypoints > 0:
                progress = (self._current_waypoint / self._total_waypoints) * 100

            return {
                "status": self._status,
                "mission_id": self._mission_id,
                "current_waypoint": self._current_waypoint,
                "total_waypoints": self._total_waypoints,
                "progress_pct": round(progress, 1),
                "position": dict(self._position),
                "eta_seconds": round(self._eta_seconds, 1),
                "started_at": self._started_at,
                "elapsed_seconds": round(time.time() - self._started_at, 1) if self._started_at else 0,
            }

    def _execute(self, mission_data: Dict[str, Any]) -> None:
        waypoints = mission_data.get("waypoints", [])
        try:
            for i, wp in enumerate(waypoints):
                if self._abort_flag:
                    self._status = "aborted"
                    logger.info("Mission aborted at waypoint %d/%d", i + 1, len(waypoints))
                    return

                target = (wp["latitude"], wp["longitude"])
                current = (self._position["latitude"], self._position["longitude"])
                dist = calculate_distance(current, target)
                travel_time = max(dist / SIMULATED_SPEED_MPS, 1.0)

                self._eta_seconds = self._calculate_remaining_eta(waypoints, i)

                steps = max(int(travel_time / INTERPOLATION_INTERVAL), 5)
                start_lat, start_lng = current
                end_lat, end_lng = target
                start_alt = self._position["altitude"]
                end_alt = wp["altitude"]

                for step in range(steps):
                    if self._abort_flag:
                        self._status = "aborted"
                        logger.info("Mission aborted during transit to waypoint %d", i + 1)
                        return

                    t = (step + 1) / steps
                    with self._lock:
                        self._position = {
                            "latitude": start_lat + (end_lat - start_lat) * t,
                            "longitude": start_lng + (end_lng - start_lng) * t,
                            "altitude": start_alt + (end_alt - start_alt) * t,
                        }
                    time.sleep(INTERPOLATION_INTERVAL)

                # Arrived at waypoint
                self._drone.move_to(wp["latitude"], wp["longitude"], wp["altitude"])
                with self._lock:
                    self._current_waypoint = i + 1

                logger.info("Waypoint %d/%d reached: %s", i + 1, len(waypoints), wp.get("action", "navigate"))

                # Execute waypoint action duration
                action_time = wp.get("duration", 2)
                if action_time > 0:
                    time.sleep(min(action_time, 5))

            self._status = "completed"
            self._eta_seconds = 0
            logger.info("Mission %s completed successfully", self._mission_id)

        except Exception as e:
            self._status = "error"
            logger.error("Mission execution error: %s", e)

    def _calculate_remaining_eta(self, waypoints: list, current_idx: int) -> float:
        total_dist = 0.0
        pos = (self._position["latitude"], self._position["longitude"])
        for wp in waypoints[current_idx:]:
            target = (wp["latitude"], wp["longitude"])
            total_dist += calculate_distance(pos, target)
            pos = target
        return total_dist / SIMULATED_SPEED_MPS

    def _load_mission(self, mission_id: str) -> Optional[Dict]:
        path = os.path.join(self._missions_dir, f"mission_{mission_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
