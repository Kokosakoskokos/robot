"""Speech-to-Text utility for Clanker Robot."""

import speech_recognition as sr
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SpeechToText:
    """Handles microphone input and converts it to text."""
    
    def __init__(self, language: str = "cs-CZ"):
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

