# config.py
# All adjustable settings — one place to tune everything.

# ─────────────────────────────────────────────────────────────────────────────
# MAVLink Connection
# ─────────────────────────────────────────────────────────────────────────────
CONNECTION_STRING        =  "udpin:0.0.0.0:14560"
HEARTBEAT_TIMEOUT        =  30

# ─────────────────────────────────────────────────────────────────────────────
# Flight
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_TAKEOFF_ALTITUDE =  10          # metres
MOVE_SPEED               =  8.0         # Velocity magnitude for move commands (m/s)
MOVE_DURATION            =  1.5         # Duration to send velocity setpoints (seconds)
YAW_ANGLE                =  30.0        # Degrees to rotate per single ROTATE command
YAW_RATE                 =  30.0        # Rotation speed in deg/s
AIRBORNE_THRESHOLD       =  0.5         # Minimum relative altitude (m) required 
                                        # before move/rotate commands are allowed.
DISARM_SAFE_ALTITUDE     =  0.5         # metres; must be on (or near) ground to disarm

# ─────────────────────────────────────────────────────────────────────────────
# STT: Model
# ─────────────────────────────────────────────────────────────────────────────
STT_MODEL                = "base"        # tiny | base | small | medium
STT_COMPUTE_TYPE         = "int8"
STT_LANGUAGE             = "en"

# ─────────────────────────────────────────────────────────────────────────────
# STT: Whisper prompt bias
# Updated to reflect actual operator phrases after diagnostic tuning.
# 'slide left' replaces 'move left' — more phonetically distinct for Whisper.
# 'come home' replaces 'return home' — avoids go-down echo confusion.
# ─────────────────────────────────────────────────────────────────────────────
STT_INITIAL_PROMPT       = (
    "Drone flight commands: drone arm, drone disarm, drone takeoff, "
    "drone land, move forward, move backward, slide left, move right, "
    "ascend, descend, move up, move down, turn left, turn right, "
    "guided mode, stabilize mode, loiter mode, come home"
)

# ─────────────────────────────────────────────────────────────────────────────
# STT: Voice Activity Detection (VAD)
# ─────────────────────────────────────────────────────────────────────────────
STT_WEBRTC_SENSITIVITY   = 2
STT_SILERO_SENSITIVITY   = 0.5
STT_SILERO_DEACTIVITY    = True

# ─────────────────────────────────────────────────────────────────────────────
# STT: Recording timing
# ─────────────────────────────────────────────────────────────────────────────
STT_POST_SPEECH_SILENCE  = 0.6
STT_MIN_RECORDING_LENGTH = 0.5
STT_MIN_GAP_RECORDINGS   = 0.5       # prevents buffer bleed between utterances

# ─────────────────────────────────────────────────────────────────────────────
# STT: Fuzzy matching
# ─────────────────────────────────────────────────────────────────────────────
STT_FUZZY_THRESHOLD      = 70

# ─────────────────────────────────────────────────────────────────────────────
# STT: Hallucination filter
# ─────────────────────────────────────────────────────────────────────────────
STT_HALLUCINATION_PHRASES = {
    ".", "..", "...", "thank you", "thanks",
    "thank you.", "thanks.", "you", "the",  "a", "",
    "bye", "bye.", "goodbye", "okay", "ok",
    "i don't know", "i don't know.", "hmm", "um", "uh",
    # VAD echo patterns — Whisper repeating the same phrase
    "lean down",           # mic echo after landing
    "we go down range",    # background noise hallucination
    "go down",
    "down",
    "up", 
    "go",
    "come on lets go yeah in take",  # pure noise
    "and the drone",
    "and drone",
}

# ─────────────────────────────────────────────────────────────────────────────
# SHUTDOWN TRIGGER PHRASES
# Words that immediately stop the voice loop.
# Add variants here if STT mishears "disconnect".
# ─────────────────────────────────────────────────────────────────────────────
_DISCONNECT_PHRASES = {
    "disconnect",
    "this connect",
    "this connected",
    "dis connect",
    "disco nect",
    "disconnect the drone",
    "drone disconnect",
    "disconadge",
    "shutdown",
    "shut down",
    "exit",
    "quit",
}

# ─────────────────────────────────────────────────────────────────────────────
# Actions that bypass the command lock, always executable
# ─────────────────────────────────────────────────────────────────────────────
_EMERGENCY_ACTIONS = {"LAND", "RTL", "DISARM"}
