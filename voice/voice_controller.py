# voice_controller.py
# Top-level voice loop: STT → IntentParser → CommandRouter.

from voice.stt_engine import STTEngine
from voice.intent_parser import IntentParser
from voice.command_router import CommandRouter


class VoiceController:

    def __init__(self, executor):
        self.stt    = STTEngine()
        self.parser = IntentParser()
        self.router = CommandRouter(executor)

    def run(self):

        print("\n🎙  Voice system started. Listening...")

        try:
            while True:

                print("\nListening...")
                text = self.stt.listen()

                if not text:
                    # Heard nothing (silence / noise below VAD threshold)
                    continue

                print(f"Heard:  {text!r}")

                intent = self.parser.parse(text)

                print(f"Intent: {intent}")

                # Skip routing for unrecognised speech — avoids None result spam
                if intent.action == "UNKNOWN":
                    print("(no matching command — ignoring)")
                    continue

                result = self.router.route(intent)

                print(f"Result: {result}")

        except KeyboardInterrupt:
            print("\n\n Shutting down voice system...")

        finally:
            # Close RealtimeSTT multiprocessing pipe → prevents ghost terminal output
            self.stt.stop()
            print("STT engine stopped.")
