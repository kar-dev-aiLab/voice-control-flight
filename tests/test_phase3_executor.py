from drone.controller import DroneController, DroneState
from drone.command_executor import CommandExecutor


def main():

    drone = DroneController("udpin:0.0.0.0:14560")
    executor = CommandExecutor(drone)

    # Inject safety
    from safety.safety_manager import SafetyManager
    executor.safety = SafetyManager()

    # -------------------------------------------------
    # SETUP SAFE STATE (CRITICAL FIX)
    # -------------------------------------------------
    drone.state.system_status = 1
    drone.state.last_heartbeat = "ok"

    print("\n--- TEST ARM ---")

    result = executor.arm()
    print(result)

    assert result.success is True


if __name__ == "__main__":
    main()