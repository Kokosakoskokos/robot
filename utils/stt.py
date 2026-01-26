"""Speech-to-Text utility for Clanker Robot."""

import speech_recognition as sr
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SpeechToText:
    """Handles microphone input and converts it to text."""
    
    def __init__(self, language: str = "cs-CZ"):
        self.language = language
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Adjust for ambient noise on init
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        
        logger.info(f"Speech recognition initialized (lang={language})")

    def listen(self) -> str:
        """Listens for a command and returns it as text."""
        with self.microphone as source:
            logger.info("Listening for voice command...")
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                text = self.recognizer.recognize_google(audio, language=self.language)
                logger.info(f"Recognized: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                logger.debug("Could not understand audio")
                return ""
            except sr.RequestError as e:
                logger.error(f"STT Error: {e}")
                return ""
            except Exception as e:
                logger.error(f"Unexpected STT error: {e}")
                return ""
