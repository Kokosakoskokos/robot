"""Text-to-Speech utilities with Czech-first preference.

Engines:
- pyttsx3 (offline, uses system voices; best if Czech voice installed)
- gTTS (online; uses Google TTS); playback via playsound

Usage:
    from utils.tts import TextToSpeech
    tts = TextToSpeech(language="cs")
    tts.speak("Ahoj, světe!")
"""

from __future__ import annotations

import os
import tempfile
from typing import List, Optional

from utils.logger import setup_logger

logger = setup_logger(__name__)


class TextToSpeech:
    """Simple TTS wrapper with prioritized engines."""

    def __init__(
        self,
        language: str = "cs",
        engine_priority: Optional[List[str]] = None,
        voice_substring: Optional[str] = None,
        playback_timeout_s: int = 15,
    ):
        self.language = language
        self.engine_priority = engine_priority or ["pyttsx3", "gtts"]
        self.voice_substring = voice_substring
        self.playback_timeout_s = playback_timeout_s

        # Lazy init; we only set up engines when first used.
        self._pyttsx3_engine = None
        self._pyttsx3_voice = None

    # ---- pyttsx3 ----
    def _init_pyttsx3(self):
        try:
            import pyttsx3
        except Exception as e:
            logger.debug(f"pyttsx3 unavailable: {e}")
            return False

        try:
            engine = pyttsx3.init()
            if self.voice_substring:
                for voice in engine.getProperty("voices"):
                    if self.voice_substring.lower() in (voice.name or "").lower():
                        engine.setProperty("voice", voice.id)
                        self._pyttsx3_voice = voice.id
                        break
            self._pyttsx3_engine = engine
            logger.info(f"pyttsx3 initialized; voice={self._pyttsx3_voice or 'default'}")
            return True
        except Exception as e:
            logger.warning(f"Failed to init pyttsx3: {e}")
            return False

    def _speak_pyttsx3(self, text: str) -> bool:
        if not self._pyttsx3_engine and not self._init_pyttsx3():
            return False
        try:
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
            return True
        except Exception as e:
            logger.warning(f"pyttsx3 speak failed: {e}")
            return False

    # ---- gTTS + playsound ----
    def _speak_gtts(self, text: str) -> bool:
        try:
            from gtts import gTTS
            from playsound import playsound
        except Exception as e:
            logger.debug(f"gTTS/playsound unavailable: {e}")
            return False

        try:
            tts = gTTS(text=text, lang=self.language)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_path = fp.name
                tts.write_to_fp(fp)
            playsound(temp_path, block=True)
            os.unlink(temp_path)
            return True
        except Exception as e:
            logger.warning(f"gTTS playback failed: {e}")
            return False

    # ---- public API ----
    def speak(self, text: str) -> bool:
        """Speak text using the first available engine in priority order."""
        text = text.strip()
        if not text:
            return False

        for engine in self.engine_priority:
            if engine == "pyttsx3":
                if self._speak_pyttsx3(text):
                    return True
            elif engine == "gtts":
                if self._speak_gtts(text):
                    return True
        logger.error("No TTS engine succeeded; speech skipped.")
        return False

