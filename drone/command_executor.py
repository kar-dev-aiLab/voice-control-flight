# command_executor.py
# High-level command orchestration layer.

import time
import logging
import threading
from pymavlink import mavutil

from .command_result import CommandResult
from safety.safety_manager import SafetyManager
from utils.config import (
    MOVE_SPEED, 
    MOVE_DURATION,
    YAW_ANGLE, 
    YAW_RATE)


logger = logging.getLogger("CommandExecutor")

class CommandExecutor:

    def __init__(self, controller):
        """
        controller = DroneController instance
        """
        self.ctrl         = controller
        self.conn         = controller.conn
        self.state        = controller.state
        self.wait_for     = controller.wait_for
        self.wait_for_ack = controller.wait_for_ack
        self.safety       = SafetyManager()

        # Emergency interrupt — set by LAND/RTL/DISARM to break move() loop
        self._move_interrupt = threading.Event()

    # =========================================================
    # CORE EXECUTION ENGINE
    # =========================================================
    def execute_command(self, name, send_fn, ack_cmd, state_check, timeout=5.0):

        start_time = time.time()

        # 1 --> Send command
        send_fn()

        # 2 --> Wait for ACK
        ack = self.wait_for_ack(ack_cmd)

        if ack is None:
            return self._build_result(name, False, "ACK_TIMEOUT", False, start_time, ack_code=None)

        if ack != mavutil.mavlink.MAV_RESULT_ACCEPTED:
            return self._build_result(name, False, f"ACK_REJECTED:{ack}", False, start_time, ack_code=ack)

        # 3 --> Wait for STATE
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

        start_time = time.time()

        decision = self.safety.check_arm(self.state)

        if not decision.allowed:
            return self._build_result("ARM", False, decision.reason, False, start_time)

        # Auto-switch to GUIDED before arming — required by ArduCopter for takeoff
        if self.state.mode != "GUIDED":
            logger.info("[ARM] Auto-switching to GUIDED mode before arming...")
            mode_result = self._set_mode_raw("GUIDED", start_time)
            if not mode_result.success:
                return self._build_result("ARM", False, "GUIDED_MODE_FAILED", False, start_time)

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
        
        start_time = time.time()

        # Interrupt any active move() loop before disarming
        self._move_interrupt.set()

        # Already disarmed (RTL auto-lands and disarms) — treat as success
        if not self.state.armed:
            return self._build_result("DISARM", True, "ALREADY_DISARMED", True, start_time)

        decision = self.safety.check_disarm(self.state)

        if not decision.allowed:
            return self._build_result(
                "DISARM", False, decision.reason, False, start_time)

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

    def _set_mode_raw(self, mode_name: str, start_time: float, timeout: float = 5.0):
        """
        Send a mode change via MAV_CMD_DO_SET_MODE (ACK-producing) and
        wait for both the MAVLink acknowledgement and the state update.
        """
        mode_map = self.conn.mode_mapping()

        if mode_name not in mode_map:
            return self._build_result("SET_MODE", False, "INVALID_MODE", False, start_time)

        mode_id = mode_map[mode_name]

        self.conn.mav.command_long_send(
            self.conn.target_system,
            self.conn.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE,
            0, 
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id,
            0, 0, 0, 0, 0 
        )
        
        # Wait for MAVLink ACK first
        ack = self.wait_for_ack(mavutil.mavlink.MAV_CMD_DO_SET_MODE, timeout=2.0)
        if ack is None:
            return self._build_result("SET_MODE", False, "ACK_TIMEOUT", False, start_time)

        if ack != mavutil.mavlink.MAV_RESULT_ACCEPTED:
            return self._build_result("SET_MODE", False, f"ACK_REJECTED:{ack}", False, start_time)
        
        # Then wait for state to confirm
        ok = self.wait_for(lambda: self.state.mode == mode_name, timeout)
        if ok:
            return self._build_result("SET_MODE", True, "SUCCESS", True, start_time)

        return self._build_result("SET_MODE", False, "STATE_TIMEOUT", False, start_time)


    def set_mode(self, mode_name: str, timeout: float = 5.0):

        start_time = time.time()

        decision = self.safety.check_mode(self.state, mode_name)

        if not decision.allowed:
            return self._build_result("SET_MODE", False, decision.reason, False, start_time)

        return self._set_mode_raw(mode_name, start_time, timeout)
    
    # =========================================================
    # TAKEOFF
    # =========================================================
    def takeoff(self, altitude: float = 10.0):
        """
        Climb to `altitude` metres above home.
        Drone must be armed and in GUIDED mode before calling.
        State check: relative altitude reaches >= 90 % of target.
        """
        start_time = time.time()

        decision = self.safety.check_takeoff(self.state)

        if not decision.allowed:
            return self._build_result("TAKEOFF", False, decision.reason, False, start_time)

        return self.execute_command(
            "TAKEOFF",
            send_fn=lambda: self.conn.mav.command_long_send(
                self.conn.target_system,
                self.conn.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,          # confirmation
                0,          # param1 — minimum pitch (ignored by copter)
                0, 0, 0,    # param2-4 unused
                0, 0,       # param5-6 lat/lon (use current)
                altitude    # param7 — target altitude (m)
            ),
            ack_cmd=mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            state_check=lambda: (
                self.state.altitude is not None
                and self.state.altitude >= altitude * 0.90
            ),
            timeout=30.0    # climbing takes longer than mode changes
        )

    # =========================================================
    # LAND
    # =========================================================
    def land(self):
        """
        Switch to LAND mode and wait until the drone disarms (touchdown).
        """
        start_time = time.time()

        # Interrupt any active move() loop before sending LAND
        self._move_interrupt.set()

        decision = self.safety.check_mode(self.state, "LAND")

        if not decision.allowed:
            return self._build_result("LAND", False, decision.reason, False, start_time)

        # Switch mode first
        mode_result = self._set_mode_raw("LAND", start_time)

        if not mode_result.success:
            return mode_result

        # Wait for touchdown — ArduCopter disarms automatically on landing
        ok = self.wait_for(lambda: not self.state.armed, timeout=30.0)

        if ok:
            return self._build_result("LAND", True, "LANDED", True, start_time)

        # Mode switched but didn't see disarm within 30 s
        return self._build_result("LAND", False, "DESCENDING", False, start_time)

    # =========================================================
    # MOVE
    # =========================================================
    def move(self, direction: str):
        """
        Send a 1-second velocity burst in `direction`.
        direction: FORWARD | BACKWARD | LEFT | RIGHT | UP | DOWN

        Uses MAV_FRAME_BODY_OFFSET_NED:
            vx = forward/back  (+forward)
            vy = left/right    (+right)
            vz = up/down       (+down, so UP = negative)
        """
        start_time = time.time()

        decision = self.safety.check_move(self.state)

        if not decision.allowed:
            return self._build_result("MOVE", False, decision.reason, False, start_time)

        direction = direction.upper()

        velocity_map = {
            "FORWARD":  ( MOVE_SPEED,  0.0,        0.0),
            "BACKWARD": (-MOVE_SPEED,  0.0,        0.0),
            "LEFT":     ( 0.0,        -MOVE_SPEED,  0.0),
            "RIGHT":    ( 0.0,         MOVE_SPEED,  0.0),
            "UP":       ( 0.0,         0.0,        -MOVE_SPEED),
            "DOWN":     ( 0.0,         0.0,         MOVE_SPEED),
        }

        if direction not in velocity_map:
            return self._build_result("MOVE", False, "INVALID_DIRECTION", False, start_time)

        vx, vy, vz = velocity_map[direction]

        # Clear any previous interrupt before starting
        self._move_interrupt.clear()

        # Velocity commands don't produce COMMAND_ACK
        # send for MOVE_DURATION seconds
        deadline = time.time() + MOVE_DURATION
        interrupted = False

        while time.time() < deadline:

            # Check for emergency interrupt every iteration
            if self._move_interrupt.is_set():
                interrupted = True
                logger.warning(f"[MOVE] Interrupted by emergency command.")
                break

            self.conn.mav.set_position_target_local_ned_send(
                0,                                              # time_boot_ms (ignored)
                self.conn.target_system,
                self.conn.target_component,
                mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
                0b0000_1111_1100_0111,                          # type_mask: use vx,vy,vz only
                0, 0, 0,                                        # position (ignored)
                vx, vy, vz,                                     # velocity (m/s)
                0, 0, 0,                                        # acceleration (ignored)
                0, 0                                            # yaw, yaw_rate (ignored)
            )
            time.sleep(0.05)   # 20 Hz
        
        # Only send stop command if interrupted by emergency — not on normal completion
        if interrupted:
            self.conn.mav.set_position_target_local_ned_send(
                0,
                self.conn.target_system,
                self.conn.target_component,
                mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
                0b0000_1111_1100_0111,
                0, 0, 0,
                0.0, 0.0, 0.0,
                0, 0, 0,
                0, 0
            )
            logger.info("[MOVE] Zero velocity sent — drone stopped.")
        status = f"MOVE_{direction}_INTERRUPTED" if interrupted else f"MOVE_{direction}"
        return self._build_result("MOVE", True, status, True, start_time)

    # =========================================================
    # ROTATE
    # =========================================================
    def rotate(self, direction: str):
        """
        Yaw left or right by one increment (YAW_RATE deg/s for 1 second).
        direction: LEFT | RIGHT
        """
        start_time = time.time()

        decision = self.safety.check_move(self.state)   # same airborne guard

        if not decision.allowed:
            return self._build_result("ROTATE", False, decision.reason, False, start_time)

        direction = direction.upper()

        if direction not in ("LEFT", "RIGHT"):
            return self._build_result("ROTATE", False, "INVALID_DIRECTION", False, start_time)

        # positive yaw_rate = clockwise (right), negative = counter-clockwise (left)
        yaw_rate = YAW_RATE if direction == "RIGHT" else -YAW_RATE

        return self.execute_command(
            "ROTATE",
            send_fn=lambda yr=yaw_rate: self.conn.mav.command_long_send(
                self.conn.target_system,
                self.conn.target_component,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,
                YAW_ANGLE,                          # param1 — target angle (deg) to rotate
                YAW_RATE,                           # param2 — yaw speed (deg/s)
                1 if direction == "RIGHT" else -1,  # param3 — direction: 1=CW, -1=CCW
                1,                                  # param4 — 1 = relative, 0 = absolute
                0, 0, 0
            ),
            ack_cmd=mavutil.mavlink.MAV_CMD_CONDITION_YAW,
            state_check=lambda: True,   # no readable yaw delta state — ACK is sufficient
            timeout=5.0
        )

    # =========================================================
    # RTL  (Return to Launch)
    # =========================================================
    def rtl(self):
        """
        Switch to RTL mode. Drone will fly home and land automatically.
        """
        start_time = time.time()

        # Interrupt any active move() loop before sending RTL
        self._move_interrupt.set()

        decision = self.safety.check_mode(self.state, "RTL")

        if not decision.allowed:
            return self._build_result("RTL", False, decision.reason, False, start_time)

        return self._set_mode_raw("RTL", start_time)
