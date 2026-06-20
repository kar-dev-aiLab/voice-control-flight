# safety_manager.py

from .safety_rules import SafetyRules
from .safety_result import SafetyResult


class SafetyManager:

    def __init__(self):
        self.rules = SafetyRules()

    def check_arm(self, state):

        ok, reason = self.rules.can_arm(state)

        return SafetyResult(
            allowed=ok,
            reason=reason,
            risk_level="LOW" if ok else "HIGH"
        )

    def check_disarm(self, state):

        ok, reason = self.rules.can_disarm(state)

        return SafetyResult(
            allowed=ok,
            reason=reason,
            risk_level="LOW"
        )

    def check_mode(self, state, mode):

        ok, reason = self.rules.can_set_mode(state, mode)

        return SafetyResult(
            allowed=ok,
            reason=reason,
            risk_level="LOW" if ok else "MEDIUM"
        )