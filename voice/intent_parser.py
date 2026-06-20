# intent_parser.py
# Maps raw transcribed text → structured Intent.
#
# Two-stage matching pipeline:
#
#   Stage 1 — EXACT:  word-boundary regex on every keyword.
#                     Handles single words and phrases precisely.
#                     Zero false positives — 'warm' never matches 'arm'.
#
#   Stage 2 — FUZZY:  rapidfuzz token_set_ratio against MULTI-WORD
#                     phrase variants ONLY.
#                     Single-word targets are excluded from fuzzy because
#                     short strings score too similarly to unrelated words
#                     (e.g. 'warm' scores 86 against 'arm').
#                     Multi-word targets are safe — 'arm the drone' scores
#                     only 43 against 'warm', which is below threshold.
#
# If neither stage matches, returns UNKNOWN.

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
# COMMAND VOCABULARY
#
# Each entry: (action, params, phrase_variants)
#
# Rules:
#   - Single-word variants ("arm", "guided") are used for EXACT match only.
#   - Multi-word variants ("arm the drone", "guide it") are used for FUZZY
#     match. They are the safety net when Whisper adds filler words.
#   - Never put a single word in the fuzzy pool — it will match false positives.
#
# Whisper mishears this system handles:
#   arm       → "our", "are"         → caught by 'arm the drone' fuzzy
#   disarm    → "this arm"           → caught by 'disarm the drone' fuzzy
#   guided    → "guide it"           → caught by 'guide it' fuzzy
#   stabilize → "stay below"         → caught by 'stabilize mode' fuzzy
#   loiter    → "hold position"      → caught by 'hold position' fuzzy
# ─────────────────────────────────────────────────────────────────────────────

COMMAND_VOCAB = [
    # (action,     params,               [single_word_variants], [multi_word_variants])
    ("ARM",        {},
        ["arm"],
        ["arm the drone", "arm motors", "arm it"]),

    ("DISARM",     {},
        ["disarm"],
        ["disarm the drone", "disarm motors", "disarm it"]),

    ("DISARM",     {},
        ["land"],
        ["land the drone", "land now", "land it"]),

    ("SET_MODE",   {"mode": "GUIDED"},
        ["guided"],
        ["guided mode", "set guided", "guide it", "set guided mode"]),

    ("SET_MODE",   {"mode": "STABILIZE"},
        ["stabilize", "stabilise"],
        ["stabilize mode", "stabilise mode", "set stabilize"]),

    ("SET_MODE",   {"mode": "LOITER"},
        ["loiter", "hover"],
        ["loiter mode", "hold position", "hold hover", "stay in place"]),
]

# Build exact-match keyword list: (pattern, action, params)
# IMPORTANT: check DISARM before ARM — 'disarm' contains 'arm'
_EXACT_CHECKS = [
    (r"\bdisarm\b",        "DISARM",   {}),
    (r"\bland\b",          "DISARM",   {}),
    (r"\barm\b",           "ARM",      {}),
    (r"\bguided?\b",       "SET_MODE", {"mode": "GUIDED"}),
    (r"\bstabili[sz]e?\b", "SET_MODE", {"mode": "STABILIZE"}),
    (r"\bloiter\b",        "SET_MODE", {"mode": "LOITER"}),
    (r"\bhov(?:er)?\b",    "SET_MODE", {"mode": "LOITER"}),
]

# Build fuzzy pool: MULTI-WORD phrases only
_FUZZY_MAP: dict[str, tuple[str, dict]] = {}
for _action, _params, _single, _multi in COMMAND_VOCAB:
    for _phrase in _multi:                    # ← multi-word only
        _FUZZY_MAP[_phrase] = (_action, _params)

_FUZZY_PHRASES = list(_FUZZY_MAP.keys())


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — EXACT MATCH
# ─────────────────────────────────────────────────────────────────────────────

def _exact_match(text: str) -> "Intent | None":
    for pattern, action, params in _EXACT_CHECKS:
        if re.search(pattern, text):
            logger.debug(f"Exact match: {pattern!r} → {action}")
            return Intent(action, params)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — FUZZY MATCH (multi-word targets only)
# ─────────────────────────────────────────────────────────────────────────────

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
        f"Fuzzy match: {text!r} → {best_phrase!r} "
        f"(score={score:.0f}) → {action}"
    )
    return Intent(action, params)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PARSER
# ─────────────────────────────────────────────────────────────────────────────

class IntentParser:

    def parse(self, text: str) -> Intent:
        """
        Stage 1 exact → Stage 2 fuzzy → UNKNOWN.
        Always returns an Intent, never raises.
        """
        text = text.lower().strip()

        if not text:
            return Intent("UNKNOWN")

        intent = _exact_match(text)
        if intent:
            return intent

        intent = _fuzzy_match(text)
        if intent:
            return intent

        logger.debug(f"No match for: {text!r}")
        return Intent("UNKNOWN")
