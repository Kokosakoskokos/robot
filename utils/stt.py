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
    """Handles microphone input and converts it to text."""
    
    def __init__(self, language: str = "cs-CZ"):
        suppress_alsa_errors()
        self.language = language
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        try:
            self.microphone = sr.Microphone()
            logger.info(f"Speech recognition initialized (lang={language})")
        except Exception as e:
            logger.warning(f"Microphone not available: {e}")

    def listen(self) -> str:
        """Listens for a command and returns it as text."""
        if not self.microphone:
            return ""
            
        try:
            with self.microphone as source:
                # Adjust for noise briefly
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("Listening for voice command...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                text = self.recognizer.recognize_google(audio, language=self.language)
                logger.info(f"Recognized: {text}")
                return text.lower()
        except Exception:
            return ""

