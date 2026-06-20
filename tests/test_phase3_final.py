# test_phase3_final.py
# Phase 3 validation — SafetyManager integration.

import time
from drone.controller import DroneController
from drone.command_executor import CommandExecutor


def check(condition, msg):
    if condition:
        print(f"[PASS] {msg}")
    else:
        raise AssertionError(f"[FAIL] {msg}")


def main():

    print("\n" + "=" * 60)
    print("PHASE 3 FINAL VALIDATION (SAFETY LAYER)")
    print("=" * 60)

    # -------------------------------------------------
    # INIT SYSTEM
    # CommandExecutor creates its own SafetyManager internally.
    # Do NOT inject a second one — that was Bug 1.
    # -------------------------------------------------
    drone    = DroneController("udpin:0.0.0.0:14560")
    executor = CommandExecutor(drone)

    time.sleep(2)

    # =================================================
    # TEST 1 - BLOCK UNSAFE STATE (NO HEARTBEAT)
    # =================================================
    print("\nTEST 1 - UNSAFE STATE BLOCK")

    drone.state.system_status = None

    result = executor.arm()
    print(result)

    check(result.success is False, "ARM blocked when system not ready")

    # =================================================
    # TEST 2 - ALLOW SAFE STATE
    # =================================================
    print("\nTEST 2 - SAFE STATE ARM")

    drone.state.system_status = 1
    drone.state.last_heartbeat = "ok"

    result = executor.arm()
    print(result)

    check(result.success is True,       "ARM allowed in safe state")
    check(drone.is_armed() is True,     "Drone reports armed state")

    # =================================================
    # TEST 3 - INVALID MODE BLOCK
    # =================================================
    print("\nTEST 3 - INVALID MODE")

    result = executor.set_mode("FAKE_MODE")
    print(result)

    check(result.success is False, "Invalid mode blocked")

    # =================================================
    # TEST 4 - VALID MODE TRANSITION
    # =================================================
    print("\nTEST 4 - VALID MODE")

    result = executor.set_mode("GUIDED")
    print(result)

    check(result.success is True,           "Valid mode accepted")
    check(drone.get_mode() == "GUIDED",     "Drone entered GUIDED mode")

    # =================================================
    # TEST 5 - DISARM ALWAYS ALLOWED
    # =================================================
    print("\nTEST 5 - DISARM")

    result = executor.disarm()
    print(result)

    check(result.success is True,       "Disarm always allowed")
    check(drone.is_armed() is False,    "Drone is disarmed")

    # =================================================
    # FINAL
    # =================================================
    print("\n" + "=" * 60)
    print("PHASE 3 COMPLETE — SAFETY LAYER STABLE")
    print("=" * 60)


if __name__ == "__main__":
    main()
