# safety_rules.py

class SafetyRules:

    def can_arm(self, state):
        if state.system_status is None:
            return False, "NO_HEARTBEAT"

        return True, "OK"

    def can_disarm(self, state):
        return True, "OK"

    def can_set_mode(self, state, mode):
        if mode not in ["STABILIZE", "GUIDED", "LOITER"]:
            return False, "INVALID_MODE"

        return True, "OK"