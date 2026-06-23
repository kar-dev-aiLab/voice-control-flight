# command_router.py

from utils.config import DEFAULT_TAKEOFF_ALTITUDE


class CommandRouter:

    def __init__(self, executor):
        self.executor = executor

    def route(self, intent):

        if intent.action == "ARM":
            return self.executor.arm()

        if intent.action == "DISARM":
            return self.executor.disarm()

        if intent.action == "SET_MODE":
            return self.executor.set_mode(intent.params["mode"])

        if intent.action == "TAKEOFF":
            altitude = intent.params.get("altitude", DEFAULT_TAKEOFF_ALTITUDE)
            return self.executor.takeoff(altitude)

        if intent.action == "LAND":
            return self.executor.land()

        if intent.action == "MOVE":
            return self.executor.move(intent.params["direction"])

        if intent.action == "ROTATE":
            return self.executor.rotate(intent.params["direction"])

        if intent.action == "RTL":
            return self.executor.rtl()

        return None