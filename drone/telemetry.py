# telemetry.py

from pymavlink import mavutil

def get_heartbeat(conn):
    """
    Wait for a HEARTBEAT message
    and return it.
    """

    msg = conn.recv_match(
        type="HEARTBEAT",
        blocking=True
    )

    return msg

def is_armed(conn):
    """
    Return True if vehicle is armed.
    """

    heartbeat = get_heartbeat(conn)

    return bool(
        heartbeat.base_mode
        & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
    )

def get_flight_mode(conn):
    """
    Return current ArduCopter mode.
    """

    heartbeat = get_heartbeat(conn)

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