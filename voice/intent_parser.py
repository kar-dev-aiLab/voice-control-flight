# intent_parser.py
# Maps transcribed text → structured Intent.
#
# Two-stage pipeline:
#   Stage 1 — EXACT:  word-boundary regex. Fast, zero false positives.
#   Stage 2 — FUZZY:  rapidfuzz against multi-word phrases ONLY.
#
# Operator phrase vocabulary (tuned from diagnostic results):
#   "drone arm"     "drone disarm"    "drone takeoff"   "drone land"
#   "move forward"  "move backward"   "slide left"      "move right"
#   "go up"         "go down"         "turn left"       "turn right"
#   "guided mode"   "stabilize mode"  "loiter mode"     "come home"

import re
import logging
from rapidfuzz import process, fuzz

from utils.config import STT_FUZZY_THRESHOLD

logger = logging.getLogger("IntentParser")


# ─────────────────────────────────────────────────────────────────────────────
# INTENT
# ─────────────────────────────────────────────────────────────────────────────

class Intent:
    def __init__(self, action: str, params: dict | None = None):
        self.action = action
        self.params = params or {}

    def __repr__(self):
        return f"Intent(action={self.action!r}, params={self.params!r})"


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — EXACT MATCH
# Order matters:
#   DISARM before ARM, TURN before bare LEFT/RIGHT, LAND before LOITER
# ─────────────────────────────────────────────────────────────────────────────

_EXACT_CHECKS = [
    # ── ARM / DISARM ─────────────────────────────────────────────────────────
    (r"\bdisarm\b",                     "DISARM",   {}),
    (r"\barm\b",                        "ARM",      {}),

    # ── TAKEOFF / LAND ───────────────────────────────────────────────────────
    (r"\btake\s*off\b",                 "TAKEOFF",  {}),
    (r"\blift\s*off\b",                 "TAKEOFF",  {}),
    (r"\bland\b",                       "LAND",     {}),
    (r"\btouch\s*down\b",               "LAND",     {}),

    # ── ROTATE — must come before bare left/right ─────────────────────────────
    (r"\bturn\s+left\b",                "ROTATE",   {"direction": "left"}),
    (r"\bturn\s+right\b",               "ROTATE",   {"direction": "right"}),
    (r"\byaw\s+left\b",                 "ROTATE",   {"direction": "left"}),
    (r"\byaw\s+right\b",                "ROTATE",   {"direction": "right"}),
    (r"\brotate\s+left\b",              "ROTATE",   {"direction": "left"}),
    (r"\brotate\s+right\b",             "ROTATE",   {"direction": "right"}),

    # ── MOVE: forward / backward ─────────────────────────────────────────────
    (r"\bforward\b",                    "MOVE",     {"direction": "forward"}),
    (r"\bahead\b",                      "MOVE",     {"direction": "forward"}),
    (r"\bback(?:ward)?\b",              "MOVE",     {"direction": "backward"}),
    (r"\breverse\b",                    "MOVE",     {"direction": "backward"}),

    # ── MOVE: left / right ───────────────────────────────────────────────────
    (r"\bslide\s+left\b",               "MOVE",     {"direction": "left"}),
    (r"\bleft\b",                       "MOVE",     {"direction": "left"}),
    (r"\bright\b",                      "MOVE",     {"direction": "right"}),

    # ── MOVE: up / down ──────────────────────────────────────────────────────
    (r"\bascend\b",                     "MOVE",     {"direction": "up"}),
    (r"\bclimb\b",                      "MOVE",     {"direction": "up"}),
    (r"\bgo\s+up\b",                    "MOVE",     {"direction": "up"}),
    (r"\bup\b",                         "MOVE",     {"direction": "up"}),
    (r"\bdescend\b",                    "MOVE",     {"direction": "down"}),
    (r"\bgo\s+down\b",                  "MOVE",     {"direction": "down"}),
    (r"\bdown\b",                       "MOVE",     {"direction": "down"}),

    # ── MODES ────────────────────────────────────────────────────────────────
    (r"\bguided?\b",                    "SET_MODE", {"mode": "GUIDED"}),
    (r"\bstabili[sz]e?\b",              "SET_MODE", {"mode": "STABILIZE"}),
    (r"\bloiter\b",                     "SET_MODE", {"mode": "LOITER"}),
    (r"\bhov(?:er)?\b",                 "SET_MODE", {"mode": "LOITER"}),

    # ── RTL ──────────────────────────────────────────────────────────────────
    (r"\breturn\b",                     "RTL",      {}),
    (r"\brtl\b",                        "RTL",      {}),
    (r"\bgo\s+home\b",                  "RTL",      {}),
    (r"\bcome\s+home\b",                "RTL",      {}),
]


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — FUZZY MATCH VOCAB (multi-word only)
#
# Includes Whisper mishear variants from diagnostic results:
#   'move for life'       → forward  (add 'move for' variant)
#   'love it'             → left     (no fix possible; phrase changed to 'slide left')
#   'and right'           → ROTATE   (add 'and right' as ROTATE variant)
#   'go down go down...'  → filtered by hallucination list in config
# ─────────────────────────────────────────────────────────────────────────────

_FUZZY_VOCAB = [
    # phrase                            action      params

    # ── ARM ──────────────────────────────────────────────────────────────────
    ("drone arm",                       "ARM",      {}),
    ("drone and",                       "ARM",      {}),
    ("arm the drone",                   "ARM",      {}),
    ("arm motors",                      "ARM",      {}),
    ("arm it",                          "ARM",      {}),

    # ── DISARM ───────────────────────────────────────────────────────────────
    ("drone disarm",                    "DISARM",   {}),
    ("disarm the drone",                "DISARM",   {}),
    ("disarm motors",                   "DISARM",   {}),

    # ── TAKEOFF ──────────────────────────────────────────────────────────────
    ("drone takeoff",                   "TAKEOFF",  {}),
    ("take off now",                    "TAKEOFF",  {}),
    ("initiate takeoff",                "TAKEOFF",  {}),
    ("drone take off",                  "TAKEOFF",  {}),

    # ── LAND ─────────────────────────────────────────────────────────────────
    ("drone land",                      "LAND",     {}),
    ("land the drone",                  "LAND",     {}),
    ("land now",                        "LAND",     {}),
    ("touch down",                      "LAND",     {}),

    # ── MOVE FORWARD — includes Whisper mishear 'move for life' ──────────────
    ("move forward",                    "MOVE",     {"direction": "forward"}),
    ("go forward",                      "MOVE",     {"direction": "forward"}),
    ("fly forward",                     "MOVE",     {"direction": "forward"}),
    ("move for",                        "MOVE",     {"direction": "forward"}),  # mishear fix

    # ── MOVE BACKWARD ────────────────────────────────────────────────────────
    ("move backward",                   "MOVE",     {"direction": "backward"}),
    ("go backward",                     "MOVE",     {"direction": "backward"}),
    ("move back",                       "MOVE",     {"direction": "backward"}),

    # ── MOVE LEFT — 'slide left' is primary phrase (more phonetically distinct)
    ("slide left",                      "MOVE",     {"direction": "left"}),
    ("move left",                       "MOVE",     {"direction": "left"}),
    ("go left",                         "MOVE",     {"direction": "left"}),
    ("fly left",                        "MOVE",     {"direction": "left"}),

    # ── MOVE RIGHT ───────────────────────────────────────────────────────────
    ("move right",                      "MOVE",     {"direction": "right"}),
    ("go right",                        "MOVE",     {"direction": "right"}),
    ("fly right",                       "MOVE",     {"direction": "right"}),

    # ── MOVE UP ──────────────────────────────────────────────────────────────
    ("go up",                           "MOVE",     {"direction": "up"}),
    ("move up",                         "MOVE",     {"direction": "up"}),
    ("climb up",                        "MOVE",     {"direction": "up"}),
    ("ascend now",                      "MOVE",     {"direction": "up"}),
    ("increase altitude",               "MOVE",     {"direction": "up"}),

    # ── MOVE DOWN ────────────────────────────────────────────────────────────
    ("go down",                         "MOVE",     {"direction": "down"}),
    ("move down",                       "MOVE",     {"direction": "down"}),
    ("descend now",                     "MOVE",     {"direction": "down"}),
    ("decrease altitude",               "MOVE",     {"direction": "down"}),

    # ── ROTATE — includes Whisper mishear 'and right' ────────────────────────
    ("turn left",                       "ROTATE",   {"direction": "left"}),
    ("ten left",                        "ROTATE",   {"direction": "left"}),   # mishear fix
    ("10 left",                         "ROTATE",   {"direction": "left"}),   # mishear fix
    ("10 loved",                        "ROTATE",   {"direction": "left"}),   # mishear fix
    ("turn the left",                   "ROTATE",   {"direction": "left"}),
    ("rotate left",                     "ROTATE",   {"direction": "left"}),
    ("yaw left",                        "ROTATE",   {"direction": "left"}),
    ("spin left",                       "ROTATE",   {"direction": "left"}),
    ("turn right",                      "ROTATE",   {"direction": "right"}),
    ("ten right",                       "ROTATE",   {"direction": "right"}),  # mishear fix
    ("10 right",                        "ROTATE",   {"direction": "right"}),
    ("rotate right",                    "ROTATE",   {"direction": "right"}),
    ("yaw right",                       "ROTATE",   {"direction": "right"}),
    ("and right",                       "ROTATE",   {"direction": "right"}),  # mishear fix

    # ── MODES ────────────────────────────────────────────────────────────────
    ("guided mode",                     "SET_MODE", {"mode": "GUIDED"}),
    ("set guided",                      "SET_MODE", {"mode": "GUIDED"}),
    ("set guided mode",                 "SET_MODE", {"mode": "GUIDED"}),
    ("guide it",                        "SET_MODE", {"mode": "GUIDED"}),
    ("stabilize mode",                  "SET_MODE", {"mode": "STABILIZE"}),
    ("stabilise mode",                  "SET_MODE", {"mode": "STABILIZE"}),
    ("set stabilize",                   "SET_MODE", {"mode": "STABILIZE"}),
    ("loiter mode",                     "SET_MODE", {"mode": "LOITER"}),
    ("hold position",                   "SET_MODE", {"mode": "LOITER"}),
    ("stay in place",                   "SET_MODE", {"mode": "LOITER"}),

    # ── RTL — 'come home' is primary phrase ──────────────────────────────────
    ("come home",                       "RTL",      {}),
    ("return home",                     "RTL",      {}),
    ("return to home",                  "RTL",      {}),
    ("go home",                         "RTL",      {}),
    ("come back",                       "RTL",      {}),
    ("fly home",                        "RTL",      {}),
    ("and hold",                        "RTL",      {}),   # mishear fix
    ("come on home",                    "RTL",      {}),
    ("on home",                         "RTL",      {}),
]

_FUZZY_MAP: dict[str, tuple[str, dict]] = {
    phrase: (action, params)
    for phrase, action, params in _FUZZY_VOCAB
}
_FUZZY_PHRASES = list(_FUZZY_MAP.keys())


# ─────────────────────────────────────────────────────────────────────────────
# MATCHING FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _exact_match(text: str) -> "Intent | None":
    for pattern, action, params in _EXACT_CHECKS:
        if re.search(pattern, text):
            logger.debug(f"Exact: {pattern!r} → {action} {params}")
            return Intent(action, params)
    return None


def _fuzzy_match(text: str) -> "Intent | None":
    result = process.extractOne(
        text,
        _FUZZY_PHRASES,
        scorer=fuzz.token_set_ratio,
        score_cutoff=STT_FUZZY_THRESHOLD,
    )
    if result is None:
        return None
    best_phrase, score, _ = result
    action, params = _FUZZY_MAP[best_phrase]
    logger.debug(
        f"Fuzzy: {text!r} → {best_phrase!r} "
        f"(score={score:.0f}) → {action} {params}"
    )
    return Intent(action, params)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PARSER
# ─────────────────────────────────────────────────────────────────────────────

class IntentParser:

    def parse(self, text: str) -> Intent:
        text = text.lower().strip()

        if not text:
            return Intent("UNKNOWN")

        intent = _exact_match(text)
        if intent:
            return intent

        intent = _fuzzy_match(text)
        if intent:
            return intent

        logger.debug(f"No match: {text!r}")
        return Intent("UNKNOWN")
