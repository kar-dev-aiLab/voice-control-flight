# safety_rules.py

from utils.config import (AIRBORNE_THRESHOLD, DISARM_SAFE_ALTITUDE)


class SafetyRules:

    # ─────────────────────────────────────────────────────────────────────────────
    # ARM
    # ─────────────────────────────────────────────────────────────────────────────
    def can_arm(self, state):
        if state.system_status is None:
            return False, "NO_HEARTBEAT"
        
        if state.armed:
            return False, "ALREADY_ARMED"
        return True, "OK"

    # ─────────────────────────────────────────────────────────────────────────────
    # DISARM
    # ─────────────────────────────────────────────────────────────────────────────
    def can_disarm(self, state):
        if state.altitude is not None and state.altitude > DISARM_SAFE_ALTITUDE:
            return False, "STILL_AIRBORNE"
        return True, "OK"

    # ─────────────────────────────────────────────────────────────────────────────
    # SET MODE
    # ─────────────────────────────────────────────────────────────────────────────
    def can_set_mode(self, state, mode):
        
        allowed = {"STABILIZE", "GUIDED", "LOITER", "LAND", "RTL"}
        
        if mode not in allowed:
            return False, "INVALID_MODE"
        
        # Block STABILIZE while airborne; cuts throttle and disarms in SITL
        if mode == "STABILIZE" and state.altitude is not None and state.altitude > AIRBORNE_THRESHOLD:
            return False, "STABILIZE_BLOCKED_AIRBORNE"
        
        return True, "OK"

    # ─────────────────────────────────────────────────────────────────────────────
    # TAKEOFF
    # ─────────────────────────────────────────────────────────────────────────────
    def can_takeoff(self, state):
        if not state.armed:
            return False, "NOT_ARMED"
        if state.altitude is not None and state.altitude > AIRBORNE_THRESHOLD:
            return False, "ALREADY_AIRBORNE"
        return True, "OK"

    # ─────────────────────────────────────────────────────────────────────────────
    # MOVE / ROTATE  (shared airborne guard)
    # ─────────────────────────────────────────────────────────────────────────────
    def can_move(self, state):
        if not state.armed:
            return False, "NOT_ARMED"
        if state.altitude is None or state.altitude < AIRBORNE_THRESHOLD:
            return False, "NOT_AIRBORNE"
        return True, "OK"