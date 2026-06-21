# safety_rules.py

# Minimum relative altitude (m) required before move/rotate commands are allowed.
AIRBORNE_THRESHOLD = 0.5


class SafetyRules:

    # ----------------------------------------------------------
    # ARM
    # ----------------------------------------------------------
    def can_arm(self, state):
        if state.system_status is None:
            return False, "NO_HEARTBEAT"
        return True, "OK"

    # ----------------------------------------------------------
    # DISARM
    # ----------------------------------------------------------
    def can_disarm(self, state):
        return True, "OK"

    # ----------------------------------------------------------
    # SET MODE
    # ----------------------------------------------------------
    def can_set_mode(self, state, mode):
        allowed = {"STABILIZE", "GUIDED", "LOITER", "LAND", "RTL"}
        if mode not in allowed:
            return False, "INVALID_MODE"
        return True, "OK"

    # ----------------------------------------------------------
    # TAKEOFF
    # ----------------------------------------------------------
    def can_takeoff(self, state):
        if not state.armed:
            return False, "NOT_ARMED"
        if state.altitude is not None and state.altitude > AIRBORNE_THRESHOLD:
            return False, "ALREADY_AIRBORNE"
        return True, "OK"

    # ----------------------------------------------------------
    # MOVE / ROTATE  (shared airborne guard)
    # ----------------------------------------------------------
    def can_move(self, state):
        if not state.armed:
            return False, "NOT_ARMED"
        if state.altitude is None or state.altitude < AIRBORNE_THRESHOLD:
            return False, "NOT_AIRBORNE"
        return True, "OK"