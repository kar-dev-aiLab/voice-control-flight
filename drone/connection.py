# connection.py
# Responsible for establishing the MAVLINK connection

from pymavlink import mavutil
from utils.config import HEARTBEAT_TIMEOUT
from typing import Any


def connect_vehicle(CONNECTION_STRING: str) -> Any:
    """
    Connect to a MAVLINK vehicle and wait for heartbeat packet.
    Return a MAVLINK connection object if successful.
    """

    print(f"Connecting to {CONNECTION_STRING} ...")

    conn: Any = mavutil.mavlink_connection(CONNECTION_STRING)

    print("Waiting for heartbeat ...")

    hb = conn.wait_heartbeat(timeout=HEARTBEAT_TIMEOUT)

    if hb is None or conn.target_system == 0:
        raise ConnectionError(
            f"[TIMEOUT] No MAVLink heartbeat received within {HEARTBEAT_TIMEOUT}s "
            f"on {CONNECTION_STRING}. Check that SITL or Mission Planner "
            f"is running and the connection string is correct."
        )

    print(
        f"Connected to system {conn.target_system},"
        f"component {conn.target_component}"
    )

    return conn