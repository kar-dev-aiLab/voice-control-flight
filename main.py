# main.py

import os
import logging

# Suppress noisy third-party output
# ctranslate2 C++ warning: "compute type converted from float16 to float32"
os.environ["CT2_VERBOSE"] = "0"

# faster_whisper logs
logging.getLogger("faster_whisper").setLevel(logging.WARNING)

# RealtimeSTT logs through the root logger
logging.getLogger("root").setLevel(logging.WARNING)

from drone.controller import DroneController
from drone.command_executor import CommandExecutor
from voice.voice_controller import VoiceController
from utils.config import CONNECTION_STRING


def main():

    print(f"Connecting to drone at {CONNECTION_STRING} ...")

    drone    = DroneController(CONNECTION_STRING)

    # Set home position immediately after connection
    drone.set_home_position()

    executor = CommandExecutor(drone)

    voice = VoiceController(executor)

    voice.run() 


if __name__ == "__main__":
    main()
    os._exit(0)