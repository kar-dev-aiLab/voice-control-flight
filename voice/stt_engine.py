# stt_engine.py
# Wraps RealtimeSTT + cleaning pipeline for drone command recognition.

from RealtimeSTT import AudioToTextRecorder
import re
import logging
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

from utils.config import (
    STT_MODEL,
    STT_LANGUAGE,
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
        logger.info(f"Initializing STT — model={STT_MODEL!r}, language={STT_LANGUAGE!r}")

        self.recorder: AudioToTextRecorder = AudioToTextRecorder(
            model=STT_MODEL,
            language=STT_LANGUAGE,
            initial_prompt=STT_INITIAL_PROMPT,
            webrtc_sensitivity=STT_WEBRTC_SENSITIVITY,
            silero_sensitivity=STT_SILERO_SENSITIVITY,
            silero_deactivity_detection=STT_SILERO_DEACTIVITY,
            post_speech_silence_duration=STT_POST_SPEECH_SILENCE,
            min_length_of_recording=STT_MIN_RECORDING_LENGTH,
            min_gap_between_recordings=STT_MIN_GAP_RECORDINGS,
            spinner=False,
        )

        logger.info("STT recorder ready.")

    def listen(self) -> str:
        """
        Block until one utterance is transcribed.
        Returns cleaned, lowercased text. Empty string if filtered.
        """
        raw = self.recorder.text()
        return self._clean(raw)

    def stop(self):
        """Shut down recorder and close multiprocessing pipe."""
        try:
            self.recorder.stop()
        except Exception:
            pass
        logger.info("STT recorder stopped.")

    def _clean(self, raw: str) -> str:
        if not raw:
            return ""

        text = raw.strip().lower()
        text = text.rstrip(".!?,;")
        text = text.strip()

        if text in STT_HALLUCINATION_PHRASES:
            logger.debug(f"Hallucination filtered: {raw!r}")
            return ""

        # Deduplicate repeated phrases
        # e.g. "go down go down go down" → "go down"
        # Caused by VAD capturing mic echo or repeated utterance
        text = self._deduplicate(text)

        return text

    def _deduplicate(self, text: str) -> str:
        """
        Remove repeated phrase segments from VAD echo capture.
        'go down go down go down' → 'go down'
        'turn left turn left'     → 'turn left'
        """
        words = text.split()
        if len(words) < 4:
            return text  # too short to have meaningful repetition

        # Try chunk sizes from half down to 2 words
        for chunk_size in range(len(words) // 2, 1, -1):
            chunk = words[:chunk_size]
            # Check if the whole text is just this chunk repeated
            repetitions = len(words) // chunk_size
            remainder  = len(words) % chunk_size
            if repetitions >= 2 and remainder == 0:
                reconstructed = chunk * repetitions
                if reconstructed == words:
                    deduped = " ".join(chunk)
                    logger.debug(f"Deduplicated: {text!r} → {deduped!r}")
                    return deduped

        return text
