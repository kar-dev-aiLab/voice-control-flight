# config.py
# All adjustable settings live here — one place to tune everything.

# ── MAVLink ──────────────────────────────────────────────────────────────────
CONNECTION_STRING        = "udpin:0.0.0.0:14560"
HEARTBEAT_TIMEOUT        = 30

# ── Flight ───────────────────────────────────────────────────────────────────
DEFAULT_TAKEOFF_ALTITUDE = 5          # metres

# ── STT: Model ───────────────────────────────────────────────────────────────
STT_MODEL                = "base"     # tiny | base | small | medium
                                      # "tiny"  → fastest, least accurate
                                      # "base"  → good balance for drone commands
                                      # "small" → best accuracy, slower on CPU
STT_LANGUAGE             = "en"       # lock to English — avoids mis-detection

# ── STT: Whisper transcription quality ───────────────────────────────────────
#STT_BEAM_SIZE            = 5          # higher = more accurate, slightly slower
#STT_BEST_OF              = 5          # candidates Whisper considers internally

# Whisper sees this text before your speech — biases it toward drone vocabulary.
# Do NOT put a period at the end (causes Whisper to treat it as sentence end).
STT_INITIAL_PROMPT       = (
    "Drone flight commands: arm, disarm, takeoff, land, "
    "guided, stabilize, loiter, return to home"
)

# ── STT: Voice Activity Detection (VAD) ──────────────────────────────────────
# WebRTC: first gate — fast, CPU-only
# 0 = least aggressive (picks up quiet voices)
# 3 = most aggressive (ignores soft sounds, good for noisy rooms)
STT_WEBRTC_SENSITIVITY   = 3

# Silero: second gate — neural network, more accurate than WebRTC alone
# 0.0 = picks up everything  |  1.0 = only very confident speech
STT_SILERO_SENSITIVITY   = 0.6

# Use Silero also for END-of-speech detection (not just start).
# More robust in noisy environments at the cost of slight extra latency.
STT_SILERO_DEACTIVITY    = True

# ── STT: Recording timing ────────────────────────────────────────────────────
# How long silence must last after speech before recording stops.
# Lower = faster response. 0.5s is safe for crisp single-word commands.
STT_POST_SPEECH_SILENCE  = 0.5       # seconds (default is 0.6)

# Minimum recording length — reject anything shorter (filters mic pops).
STT_MIN_RECORDING_LENGTH = 0.3       # seconds

# Minimum gap between two consecutive recordings.
STT_MIN_GAP_RECORDINGS   = 0.2       # seconds

# ── STT: Fuzzy matching ───────────────────────────────────────────────────────
# Minimum rapidfuzz similarity score (0–100) to accept a keyword match.
# Below this threshold the utterance is treated as UNKNOWN.
STT_FUZZY_THRESHOLD      = 70        # tune down if too many misses

# ── STT: Hallucination filter ─────────────────────────────────────────────────
# Whisper sometimes outputs these when it hears silence/noise.
# Any transcription that exactly matches one of these is discarded.
STT_HALLUCINATION_PHRASES = {
    ".", "..", "...", "thank you", "thanks",
    "thank you.", "thanks.", "you", "the", "",
    "bye", "bye.", "goodbye", "okay", "ok",
}
