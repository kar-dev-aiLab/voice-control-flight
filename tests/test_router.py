# test_router.py
from unittest.mock import MagicMock, patch
from voice.command_router import CommandRouter

# Mock executor — we just want to confirm the right method gets called
ex = MagicMock()
router = CommandRouter(ex)

def make_intent(action, **params):
    i = MagicMock()
    i.action = action
    i.params = params
    return i

router.route(make_intent("ARM"))
router.route(make_intent("DISARM"))
router.route(make_intent("SET_MODE", mode="GUIDED"))
router.route(make_intent("TAKEOFF", altitude=5.0))
router.route(make_intent("LAND"))
router.route(make_intent("MOVE", direction="FORWARD"))
router.route(make_intent("ROTATE", direction="LEFT"))
router.route(make_intent("RTL"))

expected_calls = [
    ("arm",      []),
    ("disarm",   []),
    ("set_mode", ["GUIDED"]),
    ("takeoff",  [5.0]),
    ("land",     []),
    ("move",     ["FORWARD"]),
    ("rotate",   ["LEFT"]),
    ("rtl",      []),
]

passed = 0
for method_name, args in expected_calls:
    method = getattr(ex, method_name)
    if method.called:
        call_args = list(method.call_args[0])
        match = call_args == args
        print(f"{'✅' if match else '❌'} {method_name}({args}) → called with {call_args}")
        if match:
            passed += 1
    else:
        print(f"❌ {method_name} — never called")

print(f"\n{passed}/{len(expected_calls)} passed")