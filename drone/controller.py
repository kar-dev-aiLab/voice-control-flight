# controller.py
# Responsible for drone commands: arm(), disarm(), etc.

from pymavlink import mavutil
from typing import Any

class DroneController:
    def __init__(self, connection_string):
        
        self.conn: Any = mavutil.mavlink_connection(connection_string)

        print("Waiting for heartbeat...")
        self.conn.wait_heartbeat()

        print(
            f"Connected to system "
            f"{self.conn.target_system}"
        )

    def set_mode(self, mode_name):
        
        mode_map = self.conn.mode_mapping()

        if mode_name not in mode_map:
            raise ValueError(
                f"Unknown mode: {mode_name}"
            )

        mode_id = mode_map[mode_name]

        self.conn.mav.set_mode_send(
            self.conn.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )

        print(f"Mode change requested: {mode_name}")
    

    def get_mode(self):
        
        msg = self.conn.recv_match(
            type="HEARTBEAT",
            blocking=True
        )

        return mavutil.mode_string_v10(msg)