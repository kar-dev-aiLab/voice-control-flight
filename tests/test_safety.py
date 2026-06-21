# test_safety.py
from unittest.mock import MagicMock
from safety.safety_manager import SafetyManager

sm = SafetyManager()

def make_state(armed=False, altitude=0.0, mode="STABILIZE", system_status=1):
    s = MagicMock()
    s.armed = armed
    s.altitude = altitude
    s.mode = mode
    s.system_status = system_status
    return s

tests = [
    # (description,                      method,        state_args,                          expect_allowed)
    ("ARM — no heartbeat",               sm.check_arm,   dict(system_status=None),            False),
    ("ARM — OK",                         sm.check_arm,   dict(),                              True),
    ("TAKEOFF — not armed",              sm.check_takeoff, dict(armed=False),                 False),
    ("TAKEOFF — already airborne",       sm.check_takeoff, dict(armed=True, altitude=2.0),    False),
    ("TAKEOFF — OK",                     sm.check_takeoff, dict(armed=True, altitude=0.0),    True),
    ("MOVE — not armed",                 sm.check_move,  dict(armed=False, altitude=5.0),     False),
    ("MOVE — on ground",                 sm.check_move,  dict(armed=True,  altitude=0.1),     False),
    ("MOVE — OK",                        sm.check_move,  dict(armed=True,  altitude=5.0),     True),
    ("MODE LAND — allowed",              sm.check_mode,  dict(),                              True),
    ("MODE RTL — allowed",               sm.check_mode,  dict(),                              True),
    ("MODE INVALID — blocked",           sm.check_mode,  dict(),                              False),
    ("DISARM — still airborne",          sm.check_disarm, dict(altitude=2.0),                 False),
    ("DISARM — on ground",               sm.check_disarm, dict(altitude=0.3),                 True),
    ("DISARM — already disarmed",        sm.check_disarm, dict(altitude=0.0),                 True),
]

# Special handling for check_mode which needs a mode argument
mode_map = {
    "MODE LAND — allowed":   "LAND",
    "MODE RTL — allowed":    "RTL",
    "MODE INVALID — blocked": "AUTOPILOT",
}

passed = 0
for desc, method, state_args, expect in tests:
    state = make_state(**state_args)
    if desc in mode_map:
        result = method(state, mode_map[desc])
    else:
        result = method(state)
    
    ok = result.allowed == expect
    symbol = "✅" if ok else "❌"
    print(f"{symbol} {desc} → allowed={result.allowed}, reason={result.reason}")
    if ok:
        passed += 1

print(f"\n{passed}/{len(tests)} passed")