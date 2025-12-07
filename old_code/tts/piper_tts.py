"""Piper TTS - Fast local neural text-to-speech."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional
import wave
import urllib.request
import json

try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

import pygame

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PiperTTS:
    """
    Fast local neural TTS using Piper.
    Much faster and better quality than PowerShell TTS.
    
    Voice models are automatically downloaded from Hugging Face on first use.
    """
    
    # Available voices with download URLs
    VOICE_URLS = {
        "en_US-lessac-medium": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
        },
        "en_US-lessac-low": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/low/en_US-lessac-low.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/low/en_US-lessac-low.onnx.json"
        },
        "en_US-amy-medium": {
            "model": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
            "config": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
        }
    }
    
    def __init__(
        self,
        voice: str = "en_US-lessac-medium",
        speed: float = 1.0,
        data_dir: Optional[str] = None
    ):
        """
        Initialize Piper TTS.
        
        Args:
            voice: Voice model name (e.g., "en_US-lessac-medium")
            speed: Speech speed multiplier (1.0 = normal)
            data_dir: Directory to store voice models (default: ./piper_voices)
        """
        if not PIPER_AVAILABLE:
            raise ImportError(
                "Piper TTS not available. Install with: pip install piper-tts"
            )
        
        self.voice_name = voice
        self.speed = speed
        self.data_dir = Path(data_dir or "./piper_voices")
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize pygame mixer for audio playback
        # Use settings compatible with music player (44100 Hz, stereo)
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        
        self.voice: Optional[PiperVoice] = None
        self._load_voice()
        
        logger.info(f"✅ Piper TTS initialized (voice: {voice}, speed: {speed})")
    
    def _load_voice(self):
        """Load Piper voice model, downloading if necessary."""
        try:
            logger.info(f"Loading Piper voice: {self.voice_name}...")
            
            # Check if voice is available
            if self.voice_name not in self.VOICE_URLS:
                available = ", ".join(self.VOICE_URLS.keys())
                raise ValueError(
                    f"Voice '{self.voice_name}' not available. "
                    f"Available voices: {available}"
                )
            
            # Get paths for model and config
            model_path = self.data_dir / f"{self.voice_name}.onnx"
            config_path = self.data_dir / f"{self.voice_name}.onnx.json"
            
            # Download if not present
            urls = self.VOICE_URLS[self.voice_name]
            
            if not model_path.exists():
                logger.info(f"Downloading voice model (~25MB)...")
                logger.info(f"From: {urls['model']}")
                urllib.request.urlretrieve(urls['model'], model_path)
                logger.info(f"✅ Model downloaded")
            
            if not config_path.exists():
                logger.info(f"Downloading voice config...")
                urllib.request.urlretrieve(urls['config'], config_path)
                logger.info(f"✅ Config downloaded")
            
            # Load the voice
            self.voice = PiperVoice.load(str(model_path), config_path=str(config_path))
            
            logger.info(f"✅ Piper voice loaded: {self.voice_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Piper voice: {e}")
            raise
    
    def speak(self, text: str, wait: bool = True):
        """
        Speak text using Piper TTS.
        
        Args:
            text: Text to speak
            wait: If True, wait for speech to complete. If False, return immediately.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to speak()")
            return
        
        if not self.voice:
            logger.error("Voice not loaded")
            return
        
        try:
            logger.info(f"🔊 Speaking: '{text}'")
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Synthesize speech directly to WAV file
            with wave.open(tmp_path, "wb") as wav_file:
                self.voice.synthesize_wav(text, wav_file)
            
            # Play audio using pygame
            sound = pygame.mixer.Sound(tmp_path)
            channel = sound.play()
            
            if wait:
                # Wait for playback to complete
                while channel.get_busy():
                    pygame.time.wait(10)
            
            # Cleanup temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            logger.info("✅ Speech completed")
            
        except Exception as e:
            logger.error(f"❌ Error speaking: {e}")
            import traceback
            traceback.print_exc()
    
    def speak_async(self, text: str):
        """Speak text without waiting for completion."""
        self.speak(text, wait=False)
    
    def stop(self):
        """Stop current speech."""
        try:
            pygame.mixer.stop()
            logger.info("⏸️ Speech stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping speech: {e}")
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return pygame.mixer.get_busy()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop()
