"""Text-to-Speech engine using pyttsx3."""

import logging
import time
from typing import Optional

import pyttsx3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTSEngine:
    """
    Text-to-Speech engine for Bruno using pyttsx3.
    Provides voice responses with configurable voice, rate, and volume.
    """
    
    def __init__(
        self,
        voice_id: Optional[str] = None,
        rate: int = 175,
        volume: float = 0.9
    ):
        """
        Initialize TTS engine.
        
        Args:
            voice_id: Voice ID to use (None = default voice)
            rate: Speech rate in words per minute (default: 175)
            volume: Volume level 0.0 to 1.0 (default: 0.9)
        """
        self.voice_id = voice_id
        self.rate = rate
        self.volume = volume
        self.engine: Optional[pyttsx3.Engine] = None
        
        logger.info("Initializing TTSEngine...")
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize pyttsx3 engine with configured settings."""
        try:
            # Try to initialize with sapi5 driver explicitly
            try:
                self.engine = pyttsx3.init('sapi5')
            except:
                # Fallback to default
                self.engine = pyttsx3.init()
            
            # Set voice if specified
            if self.voice_id:
                self.engine.setProperty('voice', self.voice_id)
            
            # Set rate and volume
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
            
            logger.info(f"✅ TTS Engine initialized (rate: {self.rate}, volume: {self.volume})")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize TTS engine: {e}")
            raise
    
    def list_voices(self):
        """List all available voices."""
        if not self.engine:
            logger.error("TTS engine not initialized")
            return []
        
        voices = self.engine.getProperty('voices')
        logger.info(f"\n📢 Available Voices ({len(voices)}):")
        
        for i, voice in enumerate(voices):
            logger.info(f"  {i}: {voice.name}")
            logger.info(f"     ID: {voice.id}")
            logger.info(f"     Languages: {voice.languages}")
            logger.info(f"     Gender: {getattr(voice, 'gender', 'unknown')}")
            logger.info("")
        
        return voices
    
    def set_voice(self, voice_id: str):
        """
        Set voice by ID.
        
        Args:
            voice_id: Voice ID from list_voices()
        """
        if not self.engine:
            logger.error("TTS engine not initialized")
            return
        
        try:
            self.engine.setProperty('voice', voice_id)
            self.voice_id = voice_id
            logger.info(f"✅ Voice changed to: {voice_id}")
        except Exception as e:
            logger.error(f"❌ Failed to set voice: {e}")
    
    def set_rate(self, rate: int):
        """
        Set speech rate.
        
        Args:
            rate: Words per minute (typically 100-200)
        """
        if not self.engine:
            logger.error("TTS engine not initialized")
            return
        
        try:
            self.engine.setProperty('rate', rate)
            self.rate = rate
            logger.info(f"✅ Speech rate set to: {rate} wpm")
        except Exception as e:
            logger.error(f"❌ Failed to set rate: {e}")
    
    def set_volume(self, volume: float):
        """
        Set volume level.
        
        Args:
            volume: Volume level 0.0 to 1.0
        """
        if not self.engine:
            logger.error("TTS engine not initialized")
            return
        
        volume = max(0.0, min(1.0, volume))  # Clamp to valid range
        
        try:
            self.engine.setProperty('volume', volume)
            self.volume = volume
            logger.info(f"✅ Volume set to: {volume:.1f}")
        except Exception as e:
            logger.error(f"❌ Failed to set volume: {e}")
    
    def speak(self, text: str, wait: bool = True):
        """
        Speak the given text.
        
        Args:
            text: Text to speak
            wait: If True, wait for speech to complete before returning
        """
        if not self.engine:
            logger.error("TTS engine not initialized")
            return
        
        if not text or not text.strip():
            logger.warning("Empty text provided to speak()")
            return
        
        try:
            logger.info(f"🔊 Speaking: '{text}'")
            self.engine.say(text)
            
            if wait:
                self.engine.runAndWait()
                # Add small delay to ensure audio buffer is flushed
                time.sleep(0.3)
            
        except Exception as e:
            logger.error(f"❌ Error speaking text: {e}")
    
    def speak_async(self, text: str):
        """
        Speak text asynchronously (non-blocking).
        
        Args:
            text: Text to speak
        """
        self.speak(text, wait=False)
    
    def stop(self):
        """Stop current speech."""
        if not self.engine:
            return
        
        try:
            self.engine.stop()
            logger.info("🛑 Speech stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping speech: {e}")
    
    def __del__(self):
        """Cleanup TTS engine."""
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
