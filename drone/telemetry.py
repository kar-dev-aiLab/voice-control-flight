# telemetry.py
# MAVLink telemetry helpers.

from pymavlink import mavutil
from typing import Optional, Any


def get_heartbeat(conn: Any, timeout: Optional[float] = None) -> Any:
    """
    Wait for a HEARTBEAT message
    and return it.
    """
    msg = conn.recv_match(
        type="HEARTBEAT",
        blocking=True,
        timeout=timeout,
    )

    return msg


def is_armed(conn: Any) -> bool:
    """
    Return True if vehicle is armed in its next heartbeat.
    """
    heartbeat = get_heartbeat(conn)

    if heartbeat is None:
        return False

    return bool(
        heartbeat.base_mode
        & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
    )


def get_flight_mode(conn: Any) -> str:
    """
    Return current ArduCopter flight mode.
    """
    heartbeat = get_heartbeat(conn)

    if heartbeat is None:
        return "UNKNOWN"
    
    mode_mapping = conn.mode_mapping()

    if not mode_mapping:
        return "UNKNOWN"

    reverse_mapping = {
        value: key
        for key, value in mode_mapping.items()
    }

    return reverse_mapping.get(
        heartbeat.custom_mode,
        "UNKNOWN"
    )