# controller.py
# Responsible for drone commands: arm(), disarm(), etc.

from pymavlink import mavutil
from typing import Any, Callable, Optional
import time
import threading


class DroneState:
    """
    Central state container (single source of truth).
    """
    def __init__(self):
        
        # declare attributes with types to satisfy static type checkers
        self.armed: bool = False
        self.mode: Optional[str] = None
        self.last_heartbeat: Any = None
        self.system_status: Any = None


class DroneController:

    def __init__(self, connection_string: str):

        self.conn: Any = mavutil.mavlink_connection(connection_string)
        self.state = DroneState()
        self.ack_buffer = []

        print("Waiting for heartbeat...")
        self.conn.wait_heartbeat()

        self._start_telemetry_thread()

        print(f"Connected to system {self.conn.target_system}")

    # =========================================================
    # TELEMETRY LOOP (STATE MACHINE INPUT FEED)
    # =========================================================
    def _start_telemetry_thread(self):
        thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        thread.start()


    def _telemetry_loop(self):
        while True:
            msg = self.conn.recv_match(blocking=True)

            if not msg:
                continue
            
            mtype = msg.get_type()

            if mtype == "HEARTBEAT":

                self.state.last_heartbeat = msg

                self.state.armed = bool(
                    msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                )

                self.state.mode = mavutil.mode_string_v10(msg)

                self.state.system_status = msg.system_status
            
            elif mtype == "COMMAND_ACK":
                self.ack_buffer.append(msg)
    

    # =========================================================
    # STATE QUERY API
    # =========================================================
    def is_armed(self) -> bool:
        return self.state.armed


    def get_mode(self) -> Optional[str]:
        return self.state.mode

    # =========================================================
    # GENERIC STATE WAITER (CORE ENGINE)
    # =========================================================
    def wait_for(self, condition: Callable[[], bool], timeout: float = 5.0):
        
        start = time.time()
        last_true_time = None

        while time.time() - start < timeout:
            if condition():
                if last_true_time is None:
                    last_true_time = time.time()
                elif time.time() - last_true_time > 0.1:
                    return True
            else:
                last_true_time = None

            time.sleep(0.05)

        return False
    
    def _wait_for_ack(self, command, timeout=2.0):
        
        start = time.time()

        while time.time() - start < timeout:

            for i, msg in enumerate(self.ack_buffer):
                if msg.command == command:

                    return self.ack_buffer.pop(i).result

            time.sleep(0.05)

        return None

    # =========================================================
    # COMMAND: ARM
    # =========================================================
    def arm(self, timeout: float = 5.0) -> bool:
        
        print("Sending ARM command...")

        self.conn.mav.command_long_send(
            self.conn.target_system,
            self.conn.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1, 0, 0, 0, 0, 0, 0
        )
        
        ack = self._wait_for_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)

        if ack is None:
            raise TimeoutError("No ACK received for ARM command")

        if ack != mavutil.mavlink.MAV_RESULT_ACCEPTED:
            raise RuntimeError(f"ARM rejected by autopilot. ACK={ack}")

        # Wait until the vehicle reports it is armed
        success = self.wait_for(
            lambda: self.state.armed,
            timeout=timeout
        )

        if success:
            print("Drone is ARMED.")
            return True

        raise TimeoutError("ARM failed: state not reached")

    # =========================================================
    # COMMAND: DISARM
    # =========================================================
    def disarm(self, timeout: float = 5.0) -> bool:

        print("Sending DISARM command...")

        self.conn.mav.command_long_send(
            self.conn.target_system,
            self.conn.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            0, 0, 0, 0, 0, 0, 0
        )
        
        ack = self._wait_for_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)

        if ack is None:
            raise TimeoutError("No ACK received for DISARM command")

        if ack != mavutil.mavlink.MAV_RESULT_ACCEPTED:
            raise RuntimeError(f"DISARM rejected by autopilot. ACK={ack}")

        success = self.wait_for(
            lambda: not self.state.armed,
            timeout=timeout
        )
 
        if success:
            print("Drone is DISARMED.")
            return True

        raise TimeoutError("DISARM failed: state not reached")

    # =========================================================
    # COMMAND: SET MODE
    # =========================================================
    def set_mode(self, mode_name: str, timeout: float = 5.0):

        mode_map = self.conn.mode_mapping()

        if mode_name not in mode_map:
            raise ValueError(f"Unknown mode: {mode_name}")

        mode_id = mode_map[mode_name]

        print(f"Requesting mode change --> {mode_name}")

        self.conn.mav.set_mode_send(
            self.conn.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )

        success = self.wait_for(
            lambda: self.state.mode == mode_name,
            timeout=timeout
        )

        if success:
            print(f"Mode set --> {mode_name}")
            return True

        raise TimeoutError(f"Mode change failed: {mode_name}")
    
    