"""Vosk-based wake word detector for Bruno."""

import json
import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Optional, Callable, List

# Import sounddevice conditionally
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except (ImportError, OSError):
    # OSError is raised when PortAudio library is not found
    sd = None
    SOUNDDEVICE_AVAILABLE = False

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    vosk = None
    VOSK_AVAILABLE = False

try:
    import webrtcvad
    WEBRTC_VAD_AVAILABLE = True
except ImportError:
    WEBRTC_VAD_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoskWakeWordDetector:
    """
    Wake word detector using Vosk for offline speech recognition.
    Listens for configurable wake words using sounddevice for audio input.
    """
    
    def __init__(
        self,
        model_path: str,
        wake_words: Optional[List[str]] = None,
        sample_rate: int = 16000,
        device_index: Optional[int] = None,
        use_vad: bool = True,
        vad_aggressiveness: int = 2
    ):
        """
        Initialize Vosk wake word detector.
        
        Args:
            model_path: Path to Vosk model directory
            wake_words: List of wake words to detect (default: ["bruno", "hey bruno"])
            sample_rate: Audio sample rate in Hz (default: 16000)
            device_index: Audio input device index (None = default device)
            use_vad: Use WebRTC VAD for better speech detection (default: True)
            vad_aggressiveness: VAD aggressiveness 0-3 (0=least, 3=most aggressive)
        """
        self.model_path = model_path
        self.wake_words = wake_words or ["bruno", "hey bruno", "jarvis"]
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.use_vad = use_vad and WEBRTC_VAD_AVAILABLE
        self.vad_aggressiveness = vad_aggressiveness
        
        # Audio stream components
        self.audio_queue = queue.Queue()
        self.stream: Optional[sd.InputStream] = None
        self.running = False
        self.detection_thread: Optional[threading.Thread] = None
        
        # Vosk model
        self.model: Optional[vosk.Model] = None
        self.recognizer: Optional[vosk.KaldiRecognizer] = None
        
        # Callback for wake word detection
        self.on_wake_word: Optional[Callable[[str], None]] = None
        
        # WebRTC VAD
        self.vad: Optional[webrtcvad.Vad] = None
        if self.use_vad:
            try:
                self.vad = webrtcvad.Vad(self.vad_aggressiveness)
                logger.info(f"✅ WebRTC VAD enabled (aggressiveness: {self.vad_aggressiveness})")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize WebRTC VAD: {e}")
                self.vad = None
                self.use_vad = False
        
        logger.info(f"Initializing VoskWakeWordDetector with model: {model_path}")
        self._load_model()
    
    def _load_model(self):
        """Load Vosk model from disk."""
        if not VOSK_AVAILABLE:
            logger.warning("Vosk not available - wake word detection will not work")
            return
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Vosk model not found at: {self.model_path}")
        
        try:
            logger.info(f"Loading Vosk model from {self.model_path}...")
            self.model = vosk.Model(self.model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)
            logger.info("✅ Vosk model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Vosk model: {e}")
            raise
    
    def _audio_callback(self, indata, frames, time_info, status):
        """
        Callback for sounddevice audio input.
        Puts audio data into queue for processing.
        """
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        # If VAD is enabled, check if this frame contains speech
        audio_data = bytes(indata)
        
        if self.use_vad and self.vad:
            try:
                # WebRTC VAD requires specific frame sizes (10, 20, or 30ms)
                # For 16kHz, 30ms = 480 samples = 960 bytes (16-bit)
                frame_duration_ms = 30
                frame_size = int(self.sample_rate * frame_duration_ms / 1000) * 2  # *2 for 16-bit
                
                # Only process if we have enough data
                if len(audio_data) >= frame_size:
                    # Check first frame for speech
                    is_speech = self.vad.is_speech(audio_data[:frame_size], self.sample_rate)
                    
                    if is_speech:
                        self.audio_queue.put(audio_data)
                    # Optionally, you can uncomment this to log non-speech frames
                    # else:
                    #     logger.debug("Non-speech frame filtered by VAD")
                else:
                    # Frame too small, process anyway
                    self.audio_queue.put(audio_data)
            except Exception as e:
                # If VAD fails, fall back to processing all audio
                logger.debug(f"VAD check failed: {e}")
                self.audio_queue.put(audio_data)
        else:
            # No VAD, process all audio
            self.audio_queue.put(audio_data)
    
    def _process_audio(self):
        """
        Process audio from queue and detect wake words.
        Runs in separate thread.
        """
        logger.info("🎤 Starting wake word detection thread...")
        
        while self.running:
            try:
                # Get audio data from queue (timeout to check running flag)
                data = self.audio_queue.get(timeout=0.1)
                
                # Process audio with Vosk
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").lower().strip()
                    
                    if text:
                        logger.debug(f"Recognized: '{text}'")
                        
                        # Check for wake words
                        for wake_word in self.wake_words:
                            if wake_word.lower() in text:
                                logger.info(f"🔔 Wake word detected: '{wake_word}'")
                                
                                # Call callback if registered
                                if self.on_wake_word:
                                    try:
                                        # Run callback in separate thread to avoid blocking
                                        callback_thread = threading.Thread(
                                            target=self.on_wake_word,
                                            args=(wake_word,),
                                            daemon=True
                                        )
                                        callback_thread.start()
                                    except Exception as e:
                                        logger.error(f"Error in wake word callback: {e}")
                                break
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing audio: {e}")
                if self.running:
                    continue
                else:
                    break
        
        logger.info("👋 Wake word detection thread stopped")
    
    def start(self, on_wake_word: Optional[Callable[[str], None]] = None):
        """
        Start listening for wake words.
        
        Args:
            on_wake_word: Callback function called when wake word is detected.
                         Receives the detected wake word as argument.
        """
        if not SOUNDDEVICE_AVAILABLE:
            logger.error("Cannot start wake word detector - sounddevice not available")
            return
        
        if not VOSK_AVAILABLE:
            logger.error("Cannot start wake word detector - vosk not available")
            return
        
        if self.running:
            logger.warning("Wake word detector is already running")
            return
        
        self.on_wake_word = on_wake_word
        self.running = True
        
        try:
            # Open audio stream
            logger.info(f"Opening audio stream (device: {self.device_index}, rate: {self.sample_rate} Hz)...")
            self.stream = sd.InputStream(
                device=self.device_index,
                channels=1,
                samplerate=self.sample_rate,
                dtype='int16',
                callback=self._audio_callback,
                blocksize=8000  # ~0.5 seconds at 16kHz
            )
            self.stream.start()
            logger.info("✅ Audio stream started")
            
            # Start processing thread
            self.detection_thread = threading.Thread(target=self._process_audio, daemon=True)
            self.detection_thread.start()
            logger.info("✅ Wake word detection started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start wake word detection: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop listening for wake words."""
        if not self.running:
            logger.warning("Wake word detector is not running")
            return
        
        logger.info("Stopping wake word detection...")
        self.running = False
        
        # Stop audio stream
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                logger.info("✅ Audio stream stopped")
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")
        
        # Wait for processing thread (only if not calling from within it)
        if self.detection_thread and self.detection_thread.is_alive():
            if threading.current_thread() != self.detection_thread:
                self.detection_thread.join(timeout=2.0)
                logger.info("✅ Detection thread stopped")
        
        # Give Windows time to fully release audio device
        time.sleep(0.3)
        
        logger.info("👋 Wake word detection stopped")
    
    def is_running(self) -> bool:
        """Check if detector is currently running."""
        return self.running
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
