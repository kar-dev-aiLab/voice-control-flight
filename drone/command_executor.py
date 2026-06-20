# command_executor.py
# High-level command orchestration layer.

import time
import logging
from pymavlink import mavutil
from .command_result import CommandResult
from safety.safety_manager import SafetyManager


logger = logging.getLogger("CommandExecutor")


class CommandExecutor:

    def __init__(self, controller):
        """
        controller = DroneController instance
        """
        self.ctrl        = controller
        self.conn        = controller.conn
        self.state       = controller.state
        self.wait_for    = controller.wait_for
        self.wait_for_ack = controller.wait_for_ack
        # Single SafetyManager instance — do NOT reassign from outside
        self.safety      = SafetyManager()

    # =========================================================
    # CORE EXECUTION ENGINE
    # =========================================================
    def execute_command(self, name, send_fn, ack_cmd, state_check, timeout=5.0):

        start_time = time.time()

        # 1 >> Send command
        send_fn()

        # 2 >> Wait for ACK
        ack = self.wait_for_ack(ack_cmd)

        if ack is None:
            return self._build_result(name, False, "ACK_TIMEOUT", False, start_time, ack_code=None)

        if ack != mavutil.mavlink.MAV_RESULT_ACCEPTED:
            return self._build_result(name, False, f"ACK_REJECTED:{ack}", False, start_time, ack_code=ack)

        # 3 >> Wait for STATE
        ok = self.wait_for(state_check, timeout)

        if not ok:
            return self._build_result(name, True, "STATE_TIMEOUT", False, start_time)

        return self._build_result(name, True, "SUCCESS", True, start_time)

    # =========================================================
    # RESULT FORMATTER
    # =========================================================
    def _build_result(self, command, success, status, state_reached, start_time, ack_code=None):

        latency = int((time.time() - start_time) * 1000)

        result = CommandResult(
            command=command,
            success=success,
            status=status,
            state_reached=state_reached,
            latency_ms=latency,
            ack_code=ack_code
        )

        if success:
            logger.info(f"[{command}] SUCCESS | {status} | {latency}ms")
        else:
            logger.error(f"[{command}] FAILED | {status} | state={state_reached} | {latency}ms")

        return result

    # =========================================================
    # ARM
    # =========================================================
    def arm(self):

        decision = self.safety.check_arm(self.state)

        if not decision.allowed:
            return self._build_result(
                "ARM", False, decision.reason, False, time.time()
            )

        return self.execute_command(
            "ARM",
            send_fn=lambda: self.conn.mav.command_long_send(
                self.conn.target_system,
                self.conn.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1, 0, 0, 0, 0, 0, 0
            ),
            ack_cmd=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            state_check=lambda: self.state.armed
        )

    # =========================================================
    # DISARM
    # =========================================================
    def disarm(self):

        decision = self.safety.check_disarm(self.state)

        if not decision.allowed:
            return self._build_result(
                "DISARM", False, decision.reason, False, time.time()
            )

        return self.execute_command(
            "DISARM",
            send_fn=lambda: self.conn.mav.command_long_send(
                self.conn.target_system,
                self.conn.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                0, 0, 0, 0, 0, 0, 0
            ),
            ack_cmd=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            state_check=lambda: not self.state.armed
        )

    # =========================================================
    # SET MODE
    # =========================================================
    def set_mode(self, mode_name: str, timeout: float = 5.0):

        # Capture start time HERE — before any work — so latency is accurate
        start_time = time.time()

        decision = self.safety.check_mode(self.state, mode_name)

        if not decision.allowed:
            return self._build_result(
                "SET_MODE", False, decision.reason, False, start_time
            )

        mode_map = self.conn.mode_mapping()

        if mode_name not in mode_map:
            return self._build_result(
                "SET_MODE", False, "INVALID_MODE", False, start_time
            )

        mode_id = mode_map[mode_name]

        self.conn.mav.set_mode_send(
            self.conn.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )

        ok = self.wait_for(
            lambda: self.state.mode == mode_name,
            timeout
        )

        if ok:
            return self._build_result("SET_MODE", True, "SUCCESS", True, start_time)

        return self._build_result("SET_MODE", False, "STATE_TIMEOUT", False, start_time)
