# voice_controller.py
# Top-level voice loop: STT → IntentParser → CommandRouter.
#
# Command lock: only one non-emergency command executes at a time.
# Emergency actions (LAND, RTL, DISARM) always bypass the lock.

import threading
from voice.stt_engine import STTEngine
from voice.intent_parser import IntentParser
from voice.command_router import CommandRouter
from utils.config import (_EMERGENCY_ACTIONS, _DISCONNECT_PHRASES)


class _ShutdownRequested(Exception):
    """
    Raised internally when the operator says 'disconnect'.
    """
    pass


class VoiceController:

    def __init__(self, executor):
        self.stt    = STTEngine()
        self.parser = IntentParser()
        self.router = CommandRouter(executor)

        # Non-reentrant lock: prevents new commands while one is executing.
        # Emergency actions are never blocked by it.
        self._command_lock = threading.Lock()

    def _is_disconnect(self, text: str) -> bool:
        return text.strip().lower() in _DISCONNECT_PHRASES

    def _is_emergency(self, action: str) -> bool:
        return action in _EMERGENCY_ACTIONS

    def run(self):

        print("\n  Voice system started. Listening...")
        print("  Say 'disconnect' to exit.\n")

        try:
            while True:

                print("\nListening...")
                text = self.stt.listen()
                #print(f"[STT] returned: {text!r}")

                if not text:
                    continue

                print(f"Heard:  {text!r}")

                # Shutdown gate (checked before intent parsing)
                if self._is_disconnect(text):
                    print("\n[SHUTDOWN] Disconnect command received.")
                    raise _ShutdownRequested

                intent = self.parser.parse(text)
                print(f"Intent: {intent}")

                if intent.action == "UNKNOWN":
                    print("(No matching command — ignoring)")
                    continue

                # Emergency commands always execute immediately
                if self._is_emergency(intent.action):
                    print(f"[EMERGENCY] {intent.action} — executing immediately.")
                    result = self.router.route(intent)
                    print(f"Result: {result}")
                    continue

                # Normal commands: skip if another command is running
                acquired = self._command_lock.acquire(blocking=False)
                if not acquired:
                    print(f"[BUSY] '{intent.action}' ignored — command already executing.")
                    continue

                try:
                    result = self.router.route(intent)
                    print(f"Result: {result}")
                finally:
                    self._command_lock.release()

        except _ShutdownRequested:
            pass

        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Ctrl+C received.")

        finally:
            print("\n[SHUTDOWN] Disconnect command received. Shutting down...")
            print("[SHUTDOWN] Stopping STT engine...")
            self.stt.stop()
            print("[SHUTDOWN] Vox-Flight disconnected successfully.\n")