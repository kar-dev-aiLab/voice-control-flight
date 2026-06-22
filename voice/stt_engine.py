# stt_engine.py
# Wraps RealtimeSTT + cleaning pipeline for drone command recognition.

import os
os.environ["HF_HUB_OFFLINE"] = "1"   # never attempt network calls for model checks

from RealtimeSTT import AudioToTextRecorder
import re
import sys
import time
import logging
import threading
import multiprocessing
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
        logger.info(f"[STT RAW] {raw!r}")
        return self._clean(raw)


    def stop(self):
        """
        Shut down the STT recorder cleanly on Windows.

        Sequence:
          1. Silence all loggers — no more output after disconnect
          2. Signal recorder to abort current transcription
          3. Redirect stderr to null — suppresses Windows pipe error spam
             (WinError 232 broken pipe, WinError 6 invalid handle)
          4. Call recorder.stop() in a thread with a 2-second timeout
             — if it hangs on a Windows named pipe, we don't wait forever
          5. Terminate any remaining child processes directly
          6. Restore stderr and return — os._exit(0) fires from main()
        """

        # ── Step 1: Silence all loggers immediately ──────────────────
        logging.disable(logging.CRITICAL)

        # ── Step 2: Signal abort to subprocess ───────────────────────
        try:
            self.recorder.abort()
        except Exception:
            pass

        # ── Step 3: Redirect stderr to null (Windows pipe error spam) ─
        try:
            _devnull = open(os.devnull, "w")
            sys.stderr = _devnull
        except Exception:
            _devnull = None

        # ── Step 4: recorder.stop() with timeout ─────────────────────
        # On Windows, recorder.stop() can hang if the audio subprocess
        # pipe is in a blocking read. Run it in a thread and abandon
        # it after 2 seconds if it doesn't return.
        def _stop_recorder():
            try:
                self.recorder.stop()
            except Exception:
                pass

        stop_thread = threading.Thread(target=_stop_recorder, daemon=True)
        stop_thread.start()
        stop_thread.join(timeout=2.0)
        # If still alive after 2s, we move on — os._exit(0) will kill it

        # ── Step 5: Terminate any lingering child processes ───────────
        # RealtimeSTT spawns audio_process and transcript_process.
        # If recorder.stop() timed out, they are still alive.
        # multiprocessing.active_children() lists all of them.
        for child in multiprocessing.active_children():
            try:
                child.terminate()
                child.join(timeout=1.0)
            except Exception:
                pass

        # ── Step 6: Restore stderr ────────────────────────────────────
        try:
            sys.stderr = sys.__stderr__
            if _devnull:
                _devnull.close()
        except Exception:
            pass

        # Caller (voice_controller finally block) prints goodbye message,
        # then main() calls os._exit(0) to hard-exit without GC/atexit hooks.


    def _clean(self, raw: str) -> str:
        if not raw:
            return ""

        # Strip ALL punctuation before any processing —
        # commas inside "go down, go down" were breaking deduplication
        text = raw.strip().lower()
        text = re.sub(r'[^\w\s]', ' ', text)   # replace punctuation with space
        text = ' '.join(text.split())           # collapse multiple spaces

        if not text:
            return ""

        if text in STT_HALLUCINATION_PHRASES:
            logger.info(f"[STT FILTERED] hallucination: {raw!r}")
            return ""

        deduped = self._deduplicate(text)
        if deduped != text:
            logger.info(f"[STT DEDUPED] {text!r} → {deduped!r}")

        return deduped


    def _deduplicate(self, text: str) -> str:
        """
        Remove repeated phrase segments from VAD echo capture.
        'go down go down go down' → 'go down'
        'turn left turn left'     → 'turn left'

        Iterates from smallest chunk upward so the minimal repeating
        unit is always found first (e.g. 'go down' not 'go down go down go down').
        """
        words = text.split()
        if len(words) < 4:
            return text

        for chunk_size in range(2, len(words) // 2 + 1):
            chunk = words[:chunk_size]
            repetitions = len(words) // chunk_size
            remainder   = len(words) % chunk_size
            if repetitions >= 2 and remainder == 0:
                if chunk * repetitions == words:
                    return " ".join(chunk)

        return text