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

        return None