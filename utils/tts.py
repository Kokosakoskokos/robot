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
import time
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
            # On Windows, sapi5 is usually best. On Linux, espeak.
            driver = "sapi5" if os.name == "nt" else "espeak"
            engine = pyttsx3.init(driver)
            
            # Set rate and volume
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 1.0)

            if self.voice_substring:
                voices = engine.getProperty("voices")
                for voice in voices:
                    # Check if voice supports Czech
                    if self.voice_substring.lower() in (voice.name or "").lower() or \
                       (hasattr(voice, 'languages') and any(self.voice_substring.lower() in str(lang).lower() for lang in voice.languages)):
                        engine.setProperty("voice", voice.id)
                        self._pyttsx3_voice = voice.id
                        break
            
            self._pyttsx3_engine = engine
            logger.info(f"pyttsx3 initialized (driver={driver}); voice={self._pyttsx3_voice or 'default'}")
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

    # ---- gTTS + playback ----
    def _speak_gtts(self, text: str) -> bool:
        try:
            from gtts import gTTS
            import subprocess
        except Exception as e:
            logger.debug(f"gTTS or subprocess unavailable: {e}")
            return False

        try:
            tts = gTTS(text=text, lang=self.language)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_path = fp.name
                tts.write_to_fp(fp)
            
            # Use system player instead of buggy playsound
            # mpg123 is standard on Pi, afplay on Mac, start on Windows
            if os.name == 'nt':
                os.system(f'start /min "" "{temp_path}"')
            else:
                # Try common Linux players
                for player in ['mpg123', 'play', 'aplay', 'cvlc']:
                    try:
                        if subprocess.run(['which', player], capture_output=True).returncode == 0:
                            subprocess.run([player, temp_path], check=True)
                            break
                    except:
                        continue
            
            # Small delay to ensure file isn't locked on delete
            time.sleep(0.5)
            if os.path.exists(temp_path):
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

        logger.info(f"Attempting to speak: '{text}' (Priority: {self.engine_priority})")

        for engine in self.engine_priority:
            logger.info(f"Trying TTS engine: {engine}")
            if engine == "pyttsx3":
                if self._speak_pyttsx3(text):
                    logger.info("pyttsx3 success")
                    return True
            elif engine == "gtts":
                if self._speak_gtts(text):
                    logger.info("gTTS success")
                    return True
            logger.warning(f"Engine {engine} failed, trying next...")
            
        logger.error("No TTS engine succeeded; speech skipped.")
        return False

