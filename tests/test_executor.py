# test_executor.py
import time
import sys
from drone.controller import DroneController
from drone.command_executor import CommandExecutor

print("[TEST] Connecting...")
ctrl = DroneController("udpin:0.0.0.0:14560")
time.sleep(2)   # let telemetry stabilize

ex = CommandExecutor(ctrl)

def check(label, result):
    symbol = "✅" if result and result.success else "❌"
    reason = result.status if result else "NO_RESULT"
    print(f"{symbol} {label} → {reason}")
    if not result or not result.success:
        print("     Aborting test sequence.")
        sys.exit(1)

# -- Mode first (arm requires GUIDED for takeoff)
check("SET_MODE GUIDED",  ex.set_mode("GUIDED"))
time.sleep(1)

check("ARM",              ex.arm())
time.sleep(2)

check("TAKEOFF 5m",       ex.takeoff(5.0))
time.sleep(3)   # let it stabilize at altitude

check("MOVE FORWARD",     ex.move("FORWARD"))
time.sleep(1)

check("MOVE RIGHT",       ex.move("RIGHT"))
time.sleep(1)

check("MOVE UP",          ex.move("UP"))
time.sleep(1)

check("ROTATE RIGHT",     ex.rotate("RIGHT"))
time.sleep(1)

check("ROTATE LEFT",      ex.rotate("LEFT"))
time.sleep(1)

check("RTL",              ex.rtl())
time.sleep(5)   # wait for it to return and land

# Wait for drone to land and auto-disarm 
# (RTL lands and disarms automatically)
print("Waiting for RTL to complete and auto-disarm...")
import time
deadline = time.time() + 60.0
while time.time() < deadline:
    if not ctrl.state.armed:
        print("✅ Auto-disarmed after RTL landing.")
        break
    time.sleep(1.0)
else:
    print("⚠️  RTL timeout — attempting manual disarm")
    check("DISARM", ex.disarm())
    
print("\n✅ Full sequence complete.")