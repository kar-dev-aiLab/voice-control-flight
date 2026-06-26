# test_stt_diagnostic.py
# Diagnostic — shows exactly what Whisper hears for each command phrase.
# Run: python tests/test_stt_diagnostic.py
# No SITL needed. Just your mic.

import sys, os, signal
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from voice.stt_engine import STTEngine
from voice.intent_parser import IntentParser, Intent

# Phrase-style commands;
# not bare single words
COMMANDS_TO_TEST = [
    # phrase to say,          expected action,   expected params)
    ("drone arm",             "ARM",             {}),
    ("drone disarm",          "DISARM",          {}),
    ("drone takeoff",         "TAKEOFF",         {}),
    ("drone land",            "LAND",            {}),
    ("move forward",          "MOVE",            {"direction": "forward"}),
    ("move backward",         "MOVE",            {"direction": "backward"}),
    ("slide left",            "MOVE",            {"direction": "left"}),
    ("move right",            "MOVE",            {"direction": "right"}),
    ("go up",                 "MOVE",            {"direction": "up"}),
    ("go down",               "MOVE",            {"direction": "down"}),
    ("turn left",             "ROTATE",          {"direction": "left"}),
    ("turn right",            "ROTATE",          {"direction": "right"}),
    ("guided mode",           "SET_MODE",        {"mode": "GUIDED"}),
    ("stabilize mode",        "SET_MODE",        {"mode": "STABILIZE"}),
    ("loiter mode",           "SET_MODE",        {"mode": "LOITER"}),
    ("come home",             "RTL",             {}),
]

SEPARATOR = "-" * 60

def main():
    print("\n" + "=" * 60)
    print("STT DIAGNOSTIC v2 — PHRASE-STYLE COMMANDS")
    print("=" * 60)
    print("Say each PHRASE (not single words) when prompted.")
    print("Wait for 'Listening...' before speaking.\n")

    stt    = STTEngine()
    parser = IntentParser()
    results = []

    for i, (command, exp_action, exp_params) in enumerate(COMMANDS_TO_TEST):
        print(SEPARATOR)
        print(f"[{i+1}/{len(COMMANDS_TO_TEST)}]  Say:  '{command}'")
        print("Listening...")

        heard = stt.listen()

        if not heard:
            heard_display = "(nothing / filtered)"
            intent = Intent("UNKNOWN")
        else:
            heard_display = heard
            intent = parser.parse(heard)

        overall_pass = intent.action == exp_action
        status = "PASS ✓" if overall_pass else "FAIL ✗"

        print(f"  Heard:    {heard_display!r}")
        print(f"  Intent:   {intent.action}  params={intent.params}")
        print(f"  Expected: {exp_action}  params={exp_params}")
        print(f"  Result:   {status}")

        results.append({
            "command": command, "heard": heard_display,
            "got_action": intent.action, "got_params": intent.params,
            "exp_action": exp_action, "exp_params": exp_params,
            "pass": overall_pass,
        })

        input("\n  Press Enter when ready for next command...")

    stt.stop()

    passed = sum(1 for r in results if r["pass"])
    failed = len(results) - passed

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed / {failed} failed / {len(results)} total")
    print("=" * 60)

    failures = [r for r in results if not r["pass"]]
    if failures:
        print("\nFAILED COMMANDS:")
        for r in failures:
            print(f"  Said {r['command']!r:20s} → heard {r['heard']!r:35s} → got {r['got_action']}")

    out_path = os.path.join(os.path.dirname(__file__), "stt_diagnostic_results.txt")
    with open(out_path, "w") as f:
        f.write("STT DIAGNOSTIC v2 RESULTS\n")
        f.write("=" * 60 + "\n\n")
        for r in results:
            status = "PASS" if r["pass"] else "FAIL"
            f.write(f"[{status}] Said: {r['command']!r}\n")
            f.write(f"       Whisper heard: {r['heard']!r}\n")
            f.write(f"       Intent got:    {r['got_action']}  {r['got_params']}\n")
            f.write(f"       Expected:      {r['exp_action']}  {r['exp_params']}\n\n")

    print(f"\nSaved to: {out_path}")
    
    stt.stop()
    #import ctypes
    #ctypes.windll.kernel32.TerminateProcess(
    #    ctypes.windll.kernel32.GetCurrentProcess(), 
    #    0)
    
if __name__ == "__main__":
    main()