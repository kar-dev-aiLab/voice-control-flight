# main.py

import os
from drone.controller import DroneController
from drone.command_executor import CommandExecutor
from voice.voice_controller import VoiceController
from utils.config import CONNECTION_STRING


def main():

    print(f"Connecting to drone at {CONNECTION_STRING} ...")

    drone    = DroneController(CONNECTION_STRING)
    executor = CommandExecutor(drone)

    voice = VoiceController(executor)

    voice.run()
    os._exit(0)



if __name__ == "__main__":
    main()