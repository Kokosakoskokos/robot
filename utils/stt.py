"""Speech-to-Text utility for Clanker Robot."""

import speech_recognition as sr
import os
import sys
import ctypes
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Suppress ALSA/Jack error messages on Linux
def suppress_alsa_errors():
    if os.name != 'nt':
        try:
            asound = ctypes.cdll.LoadLibrary('libasound.so.2')
            asound.snd_lib_error_set_handler(None)
        except:
            pass

class SpeechToText:
    """Handles microphone input in the background."""
    
    def __init__(self, language: str = "cs-CZ"):
        suppress_alsa_errors()
        self.language = language
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.last_command = ""
        
        try:
            self.microphone = sr.Microphone()
            # Start background listening immediately WITHOUT blocking for noise adjustment
            self.stop_listening = self.recognizer.listen_in_background(self.microphone, self._callback)
            logger.info(f"Background STT initialized (lang={language})")
        except Exception as e:
            logger.warning(f"Microphone not available: {e}")

    def _callback(self, recognizer, audio):
        """Called by background thread when audio is captured."""
        try:
            text = recognizer.recognize_google(audio, language=self.language)
            logger.info(f"Recognized: {text}")
            self.last_command = text.lower()
        except sr.UnknownValueError:
            pass
        except Exception as e:
            logger.debug(f"STT Error: {e}")

    def listen(self) -> str:
        """Returns the last recognized command and clears it."""
        cmd = self.last_command
        self.last_command = ""
        return cmd

