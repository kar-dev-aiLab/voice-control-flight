# test_guided.py

from drone.controller import DroneController
from drone.command_executor import CommandExecutor

controller = DroneController(
    "udpin:0.0.0.0:14560"
)
executor   = CommandExecutor(controller)

print("Before:", controller.get_mode())

executor.set_mode("GUIDED")

print("After:", controller.get_mode())