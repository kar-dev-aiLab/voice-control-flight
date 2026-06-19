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