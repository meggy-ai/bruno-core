"""Windows native TTS using PowerShell as fallback."""

import subprocess
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WindowsTTS:
    """
    Windows native TTS using PowerShell's Speech Synthesizer.
    More reliable than pyttsx3 on Windows.
    """
    
    def __init__(self, rate: int = 0, volume: int = 100):
        """
        Initialize Windows TTS.
        
        Args:
            rate: Speech rate -10 to 10 (0 = normal)
            volume: Volume 0 to 100
        """
        self.rate = rate
        self.volume = volume
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="TTS")
        self._speaking = False
        logger.info(f"✅ Windows TTS initialized (rate: {rate}, volume: {volume})")
    
    def speak(self, text: str, blocking: bool = False):
        """
        Speak text using Windows TTS.
        
        Args:
            text: Text to speak
            blocking: If True, wait for speech to complete. If False, run in background.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to speak()")
            return
        
        if blocking:
            # Blocking mode - wait for completion
            self._speak_blocking(text)
        else:
            # Non-blocking mode - run in thread pool
            self.executor.submit(self._speak_blocking, text)
    
    def _speak_blocking(self, text: str):
        """
        Internal method that performs the actual blocking TTS operation.
        
        Args:
            text: Text to speak
        """
        try:
            self._speaking = True
            logger.info(f"🔊 Speaking: '{text}'")
            
            # Escape single quotes in text
            text = text.replace("'", "''")
            
            # PowerShell command to speak
            ps_command = f"""
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Rate = {self.rate}
$speak.Volume = {self.volume}
$speak.Speak('{text}')
"""
            
            # Run PowerShell command
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("✅ Speech completed")
            else:
                logger.error(f"❌ TTS error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("❌ TTS timeout")
        except Exception as e:
            logger.error(f"❌ Error speaking: {e}")
        finally:
            self._speaking = False
    
    def stop(self):
        """Stop speaking (not implemented for PowerShell TTS)."""
        pass
    
    def shutdown(self):
        """Shutdown TTS engine and cleanup resources."""
        logger.info("🔇 Shutting down TTS engine")
        self.executor.shutdown(wait=False)
    
    def is_speaking(self) -> bool:
        """Check if TTS is currently speaking."""
        return self._speaking
