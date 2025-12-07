"""Voice command listener using Google Speech Recognition."""

import logging
import speech_recognition as sr
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CommandListener:
    """
    Captures and transcribes voice commands using Google Speech Recognition.
    Much more accurate than Vosk for longer phrases.
    """
    
    def __init__(
        self,
        device_index: Optional[int] = None,
        timeout_seconds: float = 10.0,
        phrase_time_limit: int = 20,
        energy_threshold: int = 400,
        pause_threshold: float = 2.0,
        max_retries: int = 2
    ):
        """
        Initialize command listener.
        
        Args:
            device_index: Audio input device index (None = default device)
            timeout_seconds: Maximum time to wait for speech
            phrase_time_limit: Maximum phrase duration in seconds
            energy_threshold: Minimum audio energy to consider as speech
            pause_threshold: How long of a pause before considering speech ended
            max_retries: Number of times to retry if command not understood
        """
        self.device_index = device_index
        self.timeout_seconds = timeout_seconds
        self.phrase_time_limit = phrase_time_limit
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.max_retries = max_retries
        
        # Speech recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = pause_threshold
        
        # Microphone
        self.microphone = None
        self._init_microphone()
        
        logger.info("✅ Google Speech Recognition initialized for command listening")
    
    def _init_microphone(self):
        """Initialize microphone."""
        try:
            mic_kwargs = {}
            if self.device_index is not None:
                mic_kwargs['device_index'] = self.device_index
            
            self.microphone = sr.Microphone(**mic_kwargs)
            
            # Test microphone
            with self.microphone as source:
                pass
            
            logger.info("✅ Microphone initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize microphone: {e}")
            raise
    
    def listen(self) -> Optional[str]:
        """
        Listen for a voice command and return transcribed text.
        Includes retry logic for better reliability.
        
        Returns:
            Transcribed command text, or None if no command detected or error occurred
        """
        if not self.microphone:
            logger.error("Microphone not initialized")
            return None
        
        logger.info("🎤 Listening for command...")
        
        with self.microphone as source:
            # Adjust for ambient noise once
            logger.info("🔧 Adjusting for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            
            # Try multiple times for better reliability
            for attempt in range(self.max_retries + 1):
                try:
                    if attempt > 0:
                        logger.info(f"🔁 Retry {attempt}/{self.max_retries}...")
                    
                    logger.info("🔴 Recording... (speak your command)")
                    
                    # Listen for audio
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.timeout_seconds,
                        phrase_time_limit=self.phrase_time_limit
                    )
                    
                    logger.info("🔄 Processing audio with Google Speech Recognition...")
                    
                    # Recognize speech using Google
                    command_text = self.recognizer.recognize_google(audio)
                    
                    if command_text:
                        logger.info(f"✅ Command captured: '{command_text}'")
                        return command_text
                    else:
                        logger.warning("⚠️  No command detected")
                        if attempt < self.max_retries:
                            logger.info("🔁 Trying again...")
                            continue
                        return None
                        
                except sr.WaitTimeoutError:
                    logger.warning("⏱️  Timeout - no speech detected")
                    if attempt < self.max_retries:
                        logger.info("🔁 Trying again...")
                        continue
                    return None
                except sr.UnknownValueError:
                    logger.warning("⚠️  Could not understand audio")
                    if attempt < self.max_retries:
                        logger.info("🔁 Trying again...")
                        continue
                    return None
                except sr.RequestError as e:
                    logger.error(f"❌ Google Speech Recognition error: {e}")
                    logger.error("   Check your internet connection")
                    return None
                except Exception as e:
                    logger.error(f"❌ Error capturing command: {e}")
                    return None
        
        return None
