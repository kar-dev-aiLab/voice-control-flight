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