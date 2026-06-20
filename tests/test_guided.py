# test_guided.py

from drone.controller import DroneController

controller = DroneController(
    "udpin:0.0.0.0:14560"
)

print("Before:", controller.get_mode())

controller.set_mode("GUIDED")

print("After:", controller.get_mode())