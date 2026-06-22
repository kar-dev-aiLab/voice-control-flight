# test_intent_parser.py
# Tests IntentParser exact-match AND fuzzy-match stages.
# No SITL, no mic, no hardware required.
# Run: python -m pytest tests/test_intent_parser.py -v

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from voice.intent_parser import IntentParser, Intent

p = IntentParser()


# ─────────────────────────────────────────────────────────────
# EXACT MATCH CASES
# ─────────────────────────────────────────────────────────────

class TestExactMatch:

    def test_arm_single_word(self):
        assert p.parse('arm').action == 'ARM'

    def test_arm_with_context(self):
        assert p.parse('arm the drone').action == 'ARM'

    def test_arm_with_prefix(self):
        assert p.parse('please arm now').action == 'ARM'

    def test_disarm_single(self):
        assert p.parse('disarm').action == 'DISARM'

    def test_disarm_with_context(self):
        assert p.parse('disarm the drone').action == 'DISARM'

    def test_land(self):
        assert p.parse('land').action == 'LAND'

    def test_touchdown(self):
        assert p.parse('touchdown').action == 'LAND'

    def test_guided_single(self):
        i = p.parse('guided')
        assert i.action == 'SET_MODE'
        assert i.params['mode'] == 'GUIDED'

    def test_guided_with_prefix(self):
        i = p.parse('set guided mode')
        assert i.action == 'SET_MODE'
        assert i.params['mode'] == 'GUIDED'

    def test_stabilize_american(self):
        i = p.parse('stabilize')
        assert i.action == 'SET_MODE'
        assert i.params['mode'] == 'STABILIZE'

    def test_stabilize_british(self):
        i = p.parse('stabilise')
        assert i.action == 'SET_MODE'
        assert i.params['mode'] == 'STABILIZE'

    def test_loiter(self):
        i = p.parse('loiter')
        assert i.action == 'SET_MODE'
        assert i.params['mode'] == 'LOITER'

    def test_hover_maps_to_loiter(self):
        i = p.parse('hover')
        assert i.action == 'SET_MODE'
        assert i.params['mode'] == 'LOITER'

    def test_disarm_takes_priority_over_arm(self):
        # 'disarm' contains 'arm' — DISARM must be checked first
        assert p.parse('disarm').action == 'DISARM'


# ─────────────────────────────────────────────────────────────
# FALSE TRIGGER GUARDS — these must NOT match ARM
# ─────────────────────────────────────────────────────────────

class TestFalseTriggerGuards:

    def test_warm_is_unknown(self):
        assert p.parse('warm').action == 'UNKNOWN'

    def test_farm_is_unknown(self):
        assert p.parse('farm').action == 'UNKNOWN'

    def test_alarm_is_unknown(self):
        assert p.parse('alarm').action == 'UNKNOWN'

    def test_charm_is_unknown(self):
        assert p.parse('charm').action == 'UNKNOWN'

    def test_armed_forces_is_unknown(self):
        # 'armed' contains 'arm' — word boundary must prevent false match
        assert p.parse('armed forces').action == 'UNKNOWN'


# ─────────────────────────────────────────────────────────────
# EMPTY / NOISE / HALLUCINATION
# ─────────────────────────────────────────────────────────────

class TestNoise:

    def test_empty_string(self):
        assert p.parse('').action == 'UNKNOWN'

    def test_whitespace_only(self):
        assert p.parse('   ').action == 'UNKNOWN'

    def test_thank_you(self):
        assert p.parse('thank you').action == 'UNKNOWN'

    def test_random_words(self):
        assert p.parse('the quick brown fox').action == 'UNKNOWN'


# ─────────────────────────────────────────────────────────────
# FUZZY MATCH CASES (requires rapidfuzz installed)
# ─────────────────────────────────────────────────────────────

class TestFuzzyMatch:

    def test_arm_mishear_our(self):
        # Whisper sometimes hears 'arm' as 'our'
        # fuzzy should still catch 'arm the drone' → ARM
        i = p.parse('arm the drone')
        assert i.action == 'ARM'

    def test_guided_mishear(self):
        # 'guide it' should still fuzzy-match to GUIDED
        i = p.parse('guide it')
        assert i.action == 'SET_MODE'
        assert i.params['mode'] == 'GUIDED'

    def test_loiter_phrase(self):
        i = p.parse('hold position')
        assert i.action == 'SET_MODE'
        assert i.params['mode'] == 'LOITER'

    def test_stabilize_phrase(self):
        i = p.parse('stabilize mode')
        assert i.action == 'SET_MODE'
        assert i.params['mode'] == 'STABILIZE'
