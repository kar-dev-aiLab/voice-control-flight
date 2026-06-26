# test_controller.py

import time
from drone.controller import DroneController
from drone.command_executor import CommandExecutor

drone = DroneController("udpin:0.0.0.0:14560")
executor = CommandExecutor(drone)

print("\n===== INITIAL STATE =====")
print("Mode:", drone.get_mode())
print("Armed:", drone.is_armed())

time.sleep(1)

print("\n----- Testing ARM -----")
executor.arm()

assert drone.wait_for(lambda: drone.is_armed(), 5), "ARM state not reached"
print("ARM OK")

time.sleep(1)

print("\n----- Testing MODE -----")
executor.set_mode("GUIDED")  # or "STABILIZE" depending on SITL config

assert drone.wait_for(lambda: drone.get_mode() == "GUIDED", 5), "MODE not reached"
print("MODE OK")

time.sleep(1)

print("\n----- Testing DISARM -----")
executor.disarm()

assert drone.wait_for(lambda: not drone.is_armed(), 5), "DISARM state not reached"
print("DISARM OK")

print("\nALL TESTS COMPLETED for 'test_controller.py")