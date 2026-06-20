from safety.safety_manager import SafetyManager
from drone.controller import DroneState


def run_tests():

    print("\n=== PHASE 3 SAFETY UNIT TEST ===")

    safety = SafetyManager()

    # =====================================================
    # TEST 1 - UNSAFE STATE (no heartbeat)
    # =====================================================
    print("\nTEST 1 - NO HEARTBEAT (should block ARM)")

    state = DroneState()

    result = safety.check_arm(state)
    print(result)

    assert result.allowed is False
    assert result.reason == "NO_HEARTBEAT"

    # =====================================================
    # TEST 2 - SAFE STATE
    # =====================================================
    print("\nTEST 2 - VALID STATE (should allow ARM)")

    state.system_status = 1  # simulate healthy system
    state.last_heartbeat = "dummy"

    result = safety.check_arm(state)
    print(result)

    assert result.allowed is True

    # =====================================================
    # TEST 3 - INVALID MODE
    # =====================================================
    print("\nTEST 3 - INVALID MODE")

    result = safety.check_mode(state, "FAKE_MODE")
    print(result)

    assert result.allowed is False
    assert result.reason == "INVALID_MODE"

    print("\nALL SAFETY TESTS PASSED ✅")


if __name__ == "__main__":
    run_tests()