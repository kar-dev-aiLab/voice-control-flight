"""
Phase 2 Release Validation Suite

Validates:
- Connection
- ARM
- MODE change
- DISARM
- Invalid mode handling
- State consistency

Run:

python -m tests.test_phase2_final
"""

import time

from drone.controller import DroneController
from drone.command_executor import CommandExecutor


def check(condition, description):
    if condition:
        print(f"[PASS] {description}")
    else:
        raise AssertionError(f"[FAIL] {description}")


def main():

    print("=" * 60)
    print("PHASE 2 RELEASE VALIDATION")
    print("=" * 60)

    drone = DroneController("udpin:0.0.0.0:14560")
    executor = CommandExecutor(drone)

    result = executor.set_mode("STABILIZE")

    time.sleep(2)

    # =====================================================
    # TEST 1: TELEMETRY AVAILABLE
    # =====================================================

    print("\nTEST 1 - TELEMETRY")

    check(
        drone.state.last_heartbeat is not None,
        "Heartbeat received"
    )

    print("Mode:", drone.get_mode())
    print("Armed:", drone.is_armed())

    # =====================================================
    # TEST 2: ARM
    # =====================================================

    print("\nTEST 2 - ARM")

    result = executor.arm()

    print(result)

    check(
        result.success,
        "ARM command succeeded"
    )

    check(
        drone.is_armed(),
        "Vehicle reports armed state"
    )

    # =====================================================
    # TEST 3: MODE CHANGE
    # =====================================================

    print("\nTEST 3 - MODE CHANGE")

    result = executor.set_mode("GUIDED")

    print(result)

    check(
        result.success,
        "GUIDED mode command succeeded"
    )

    check(
        drone.get_mode() == "GUIDED",
        "Vehicle entered GUIDED mode"
    )

    # =====================================================
    # TEST 4: DISARM
    # =====================================================

    print("\nTEST 4 - DISARM")

    result = executor.disarm()

    print(result)

    check(
        result.success,
        "DISARM command succeeded"
    )

    check(
        not drone.is_armed(),
        "Vehicle reports disarmed state"
    )

    # =====================================================
    # TEST 5: INVALID MODE
    # =====================================================

    print("\nTEST 5 - INVALID MODE")

    result = executor.set_mode("THIS_MODE_DOES_NOT_EXIST")

    print(result)

    check(
        not result.success,
        "Invalid mode rejected"
    )

    check(
        result.status == "INVALID_MODE",
        "Correct invalid mode status returned"
    )

    # =====================================================
    # TEST 6: RAPID COMMAND SEQUENCE
    # =====================================================

    print("\nTEST 6 - RAPID SEQUENCE")

    result1 = executor.arm()
    result2 = executor.disarm()

    check(result1.success, "Rapid ARM succeeded")
    check(result2.success, "Rapid DISARM succeeded")

    # =====================================================
    # COMPLETE
    # =====================================================

    print("\n" + "=" * 60)
    print("PHASE 2 VALIDATION PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()