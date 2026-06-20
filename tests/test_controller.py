# test_controller.py

from drone.controller import DroneController
import time

drone = DroneController("udpin:0.0.0.0:14560")

print("\n=== INITIAL STATE ===")
print("Mode:", drone.get_mode())
print("Armed:", drone.is_armed())

time.sleep(1)

print("\n--- Testing ARM ---")
drone.arm()

assert drone.wait_for(lambda: drone.is_armed(), 5), "ARM state not reached"
print("ARM OK")

time.sleep(1)

print("\n--- Testing MODE ---")
drone.set_mode("GUIDED")  # or "STABILIZE" depending on SITL config

assert drone.wait_for(lambda: drone.get_mode() == "GUIDED", 5), "MODE not reached"
print("MODE OK")

time.sleep(1)

print("\n--- Testing DISARM ---")
drone.disarm()

assert drone.wait_for(lambda: not drone.is_armed(), 5), "DISARM state not reached"
print("DISARM OK")

print("\nALL TESTS COMPLETED for 'test_controller.py")