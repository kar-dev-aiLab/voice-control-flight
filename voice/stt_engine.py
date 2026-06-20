# stt_engine.py
# Wraps RealtimeSTT + fuzzy post-processing for drone command recognition.
#
# Pipeline per utterance:
#   mic → WebRTC VAD → Silero VAD → faster-whisper → hallucination filter
#   → text out → IntentParser (exact + fuzzy matching)

from RealtimeSTT import AudioToTextRecorder
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

import logging

from utils.config import (
    STT_MODEL,
    STT_LANGUAGE,
    #STT_BEAM_SIZE,
    #STT_BEST_OF,
    STT_INITIAL_PROMPT,
    STT_WEBRTC_SENSITIVITY,
    STT_SILERO_SENSITIVITY,
    STT_SILERO_DEACTIVITY,
    STT_POST_SPEECH_SILENCE,
    STT_MIN_RECORDING_LENGTH,
    STT_MIN_GAP_RECORDINGS,
    STT_HALLUCINATION_PHRASES,
)

logger = logging.getLogger("STTEngine")


class STTEngine:

    def __init__(self):

        logger.info(
            f"Initializing STT — model={STT_MODEL!r}, "
            f"language={STT_LANGUAGE!r}"
        )

        self.recorder: AudioToTextRecorder = AudioToTextRecorder(

            # ── Model ────────────────────────────────────────
            model=STT_MODEL,
            language=STT_LANGUAGE,

            # ── Whisper accuracy ─────────────────────────────
            #beam_size=STT_BEAM_SIZE,
            #best_of=STT_BEST_OF,
            initial_prompt=STT_INITIAL_PROMPT,

            # ── VAD: detection ───────────────────────────────
            webrtc_sensitivity=STT_WEBRTC_SENSITIVITY,
            silero_sensitivity=STT_SILERO_SENSITIVITY,
            silero_deactivity_detection=STT_SILERO_DEACTIVITY,

            # ── VAD: timing ──────────────────────────────────
            post_speech_silence_duration=STT_POST_SPEECH_SILENCE,
            min_length_of_recording=STT_MIN_RECORDING_LENGTH,
            min_gap_between_recordings=STT_MIN_GAP_RECORDINGS,

            # ── Misc ─────────────────────────────────────────
            spinner=False,          # no halo spinner — cleaner console output
        )

        logger.info("STT recorder ready.")

    # ─────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────

    def listen(self) -> str:
        """
        Block until one utterance is fully transcribed.

        Returns:
            Cleaned, lowercased text string.
            Empty string if nothing heard or hallucination detected.
        """
        raw = self.recorder.text()
        return self._clean(raw)

    def stop(self):
        """
        Cleanly shut down the recorder and its multiprocessing pipe.
        Must be called on exit — prevents ghost terminal output.
        """
        try:
            self.recorder.stop()
        except Exception:
            pass
        logger.info("STT recorder stopped.")

    # ─────────────────────────────────────────────────────────
    # INTERNAL: TEXT CLEANING
    # ─────────────────────────────────────────────────────────

    def _clean(self, raw: str) -> str:
        """
        Strip, lowercase, and filter out Whisper hallucinations.

        Whisper commonly outputs artefacts like "Thank you.", ".", "You"
        when it hears background noise. These are useless and would
        spam the intent parser, so we discard them here.
        """
        if not raw:
            return ""

        text = raw.strip().lower()

        # Remove trailing punctuation Whisper sometimes adds
        text = text.rstrip(".!?,;")
        text = text.strip()

        if text in STT_HALLUCINATION_PHRASES:
            logger.debug(f"Hallucination filtered: {raw!r}")
            return ""

        return text
