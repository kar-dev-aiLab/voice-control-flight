# controller.py
# Responsible for drone commands: arm(), disarm(), etc.

import time
import threading
import logging
from pymavlink import mavutil
from collections import deque
from typing import (Any, Callable, Optional)

from .connection import connect_vehicle
from .telemetry import get_heartbeat
from utils.config import HEARTBEAT_TIMEOUT

logger = logging.getLogger("DroneController")

_TELEMETRY_RECV_TIMEOUT   = 1.0   # seconds per recv_match call
_MAX_MISSED_HEARTBEATS    = 5     # alert after this many consecutive misses


# ─────────────────────────────────────────────────────────────────────────────
# DRONE STATE  (single source of truth for the parts of the system)
# ─────────────────────────────────────────────────────────────────────────────
class DroneState:
    """
    Shared state container updated continuously by the telemetry thread.
    """
    def __init__(self):
        
        self.armed: bool               = False
        self.mode: Optional[str]       = None
        self.last_heartbeat: Any       = None
        self.system_status: Any        = None
        self.altitude: Optional[float] = None
        
# ─────────────────────────────────────────────────────────────────────────────
# DRONE CONTROLLER
# ─────────────────────────────────────────────────────────────────────────────
class DroneController:

    def __init__(self, connection_string: str):
        """
        Connect to the vehicle and start the live telemetry thread.
        """
        self.conn: Any                  = connect_vehicle(connection_string)
        self.state : DroneState         = DroneState()
        self.ack_buffer: deque          = deque(maxlen=50)
        self._ack_lock: threading.Lock  = threading.Lock()

        # Identify this connection as a GCS; required so ArduCopter
        # accepts our COMMAND_LONG messages.
        self.conn.mav.srcSystem = 255
        
        # capture another heartbeat to read armed/mode/system_status
        hb = get_heartbeat(self.conn, timeout=HEARTBEAT_TIMEOUT)

        if hb:
            self.state.system_status  = hb.system_status
            self.state.mode           = mavutil.mode_string_v10(hb)
            self.state.last_heartbeat = hb
            # ONLY the MAV_MODE_FLAG bit is authoritative for armed state
            self.state.armed = bool(
                hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            )
        else:
            logger.warning("[INIT] State-seed heartbeat timed out.")

        self._start_telemetry_thread()

        #print(f"Connected to system {self.conn.target_system}")

    # ====================================================================
    # TELEMETRY LOOP (background thread; runs for the lifetime of the app)
    # ====================================================================

    def _start_telemetry_thread(self):

        thread = threading.Thread(
            target=self._telemetry_loop, 
            daemon=True,
            name="DroneController-telemetry",
            )
        thread.start()


    def _telemetry_loop(self):
        """
        Continuously receive MAVLink messages and update DroneState.
        """
        missed_heartbeats = 0
        
        while True:
            msg = self.conn.recv_match(blocking=True, timeout=_TELEMETRY_RECV_TIMEOUT)

            if msg is None:
                # recv_match timed out; no packet arrived within the window
                missed_heartbeats += 1
                if missed_heartbeats >= _MAX_MISSED_HEARTBEATS:
                    logger.critical(
                        f"[TELEMETRY] No MAVLink packets received for "
                        f"{missed_heartbeats * _TELEMETRY_RECV_TIMEOUT:.0f}s — "
                        f"link may be lost. State is STALE."
                    )
                continue

            # reset on any successful receive
            missed_heartbeats = 0
            
            mtype = msg.get_type()

            if mtype == "HEARTBEAT":

                self.state.last_heartbeat = msg

                self.state.armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)

                self.state.mode  = mavutil.mode_string_v10(msg)

                self.state.system_status = msg.system_status

                logger.debug(
                    f"Heartbeat received: armed={self.state.armed}, mode={self.state.mode}")
            
            elif mtype == "COMMAND_ACK":
                with self._ack_lock:
                    self.ack_buffer.append(msg)
            
            elif mtype == "GLOBAL_POSITION_INT":
                # relative_alt is in mm; convert to metres
                self.state.altitude = msg.relative_alt / 1000.0

    # =========================================================
    # STATE QUERY API (used by CommandExecutor and tests)
    # =========================================================

    def set_home_position(self):
        """
        Set home to current vehicle position. Waits for MAVLink ACK.
        Call once immediately after connection, before arming.
        Logs a CRITICAL warning if rejected (e.g. no GPS fix)
        """
        self.conn.mav.command_long_send(
            self.conn.target_system,
            self.conn.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_HOME,
            0,
            1,              # param1=1 means use current position
            0, 0, 0,        # param2-4 unused
            0, 0, 0         # lat, lon, alt (ignored when param1=1)
        )

        ack = self.wait_for_ack(mavutil.mavlink.MAV_CMD_DO_SET_HOME, timeout=5.0)

        if ack is None:
            logger.critical(
                "[HOME] Set home ACK timed out; RTL destination is undefined. "
                "Do not use RTL until home is confirmed."
            )
        elif ack != mavutil.mavlink.MAV_RESULT_ACCEPTED:
            logger.critical(
                f"[HOME] Set home REJECTED (result={ack}); possibly no GPS fix. "
                f"RTL destination is undefined."
            )
        else:
            logger.info("[HOME] Home position confirmed by vehicle.")

    def is_armed(self) -> bool:
        return self.state.armed


    def get_mode(self) -> Optional[str]:
        return self.state.mode

    # =========================================================
    # GENERIC STATE WAITER (CORE ENGINE)
    # =========================================================

    def wait_for(self, condition: Callable[[], bool], timeout: float = 5.0) -> bool:
        
        start = time.time()

        while time.time() - start < timeout:

            if condition():
                return True
            time.sleep(0.05)

        return False
    
    def wait_for_ack(self, command: int, timeout: float = 2.0) -> Optional[int]:

        start = time.time()

        while time.time() - start < timeout:

            with self._ack_lock:

                for msg in list(self.ack_buffer):
                    if msg.command == command:
                        self.ack_buffer.remove(msg)
                        return msg.result

            time.sleep(0.05)

        return None
