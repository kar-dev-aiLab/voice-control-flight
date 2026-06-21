# voice_controller.py
# Top-level voice loop: STT → IntentParser → CommandRouter.

from voice.stt_engine import STTEngine
from voice.intent_parser import IntentParser
from voice.command_router import CommandRouter


class _ShutdownRequested(Exception):
    """Raised internally when the operator says 'disconnect'."""
    pass


class VoiceController:

    def __init__(self, executor):
        self.stt    = STTEngine()
        self.parser = IntentParser()
        self.router = CommandRouter(executor)

    # ----------------------------------------------------------
    # SHUTDOWN TRIGGER PHRASES
    # Words that immediately stop the voice loop.
    # Add variants here if STT mishears "disconnect".
    # ----------------------------------------------------------
    _DISCONNECT_PHRASES = {
        "disconnect",
        "drone disconnect",
        "disconadge",
        "shutdown",
        "shut down",
        "exit",
        "quit",
    }

    def _is_disconnect(self, text: str) -> bool:
        return text.strip().lower() in self._DISCONNECT_PHRASES

    def run(self):

        print("\n  Voice system started. Listening...")
        print("  Say 'disconnect' to exit.\n")

        try:
            while True:

                print("\nListening...")
                text = self.stt.listen()

                if not text:
                    continue

                print(f"Heard:  {text!r}")

                # -- Shutdown gate (checked before intent parsing)
                if self._is_disconnect(text):
                    print("\n[SHUTDOWN] Disconnect command received.")
                    raise _ShutdownRequested

                intent = self.parser.parse(text)

                print(f"Intent: {intent}")

                if intent.action == "UNKNOWN":
                    print("(No matching command — ignoring)")
                    continue

                result = self.router.route(intent)

                print(f"Result: {result}")

        except _ShutdownRequested:
            pass   # clean exit — falls through to finally

        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Ctrl+C received.")

        finally:
            print("\n[SHUTDOWN] Stopping STT engine...")
            self.stt.stop()
            print("[SHUTDOWN] STT engine stopped.")
            print("[SHUTDOWN] Vox-Flight disconnected. Goodbye.\n")