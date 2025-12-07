"""Voice command listener using Faster Whisper (local, offline)."""

import logging
import wave
import tempfile
import os
from typing import Optional
import speech_recognition as sr

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FasterWhisperListener:
    """
    Captures and transcribes voice commands using Faster Whisper.
    Fully offline and GPU-accelerated alternative to Google Speech Recognition.
    """
    
    def __init__(
        self,
        device_index: Optional[int] = None,
        timeout_seconds: float = 10.0,
        phrase_time_limit: int = 20,
        energy_threshold: int = 400,
        pause_threshold: float = 2.0,
        max_retries: int = 2,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "default"
    ):
        """
        Initialize Faster Whisper listener.
        
        Args:
            device_index: Audio input device index (None = default device)
            timeout_seconds: Maximum time to wait for speech
            phrase_time_limit: Maximum phrase duration in seconds
            energy_threshold: Minimum audio energy to consider as speech
            pause_threshold: How long of a pause before considering speech ended
            max_retries: Number of times to retry if command not understood
            model_size: Whisper model size ("tiny", "base", "small", "medium", "large-v3")
            device: Device to run on ("cpu", "cuda", "auto")
            compute_type: Compute type ("int8", "float16", "float32", "default")
        """
        if not FASTER_WHISPER_AVAILABLE:
            raise ImportError(
                "Faster Whisper not available. Install with: pip install faster-whisper"
            )
        
        self.device_index = device_index
        self.timeout_seconds = timeout_seconds
        self.phrase_time_limit = phrase_time_limit
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.max_retries = max_retries
        
        # Speech recognition (for audio capture)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = pause_threshold
        
        # Microphone
        self.microphone = None
        self._init_microphone()
        
        # Determine device
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        
        self.device = device
        
        # Determine compute type
        if compute_type == "default":
            compute_type = "float16" if device == "cuda" else "int8"
        
        self.compute_type = compute_type
        
        # Load Whisper model
        self.model = None
        self._load_model(model_size)
        
        logger.info(f"✅ Faster Whisper initialized (model: {model_size}, device: {device})")
    
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
    
    def _load_model(self, model_size: str):
        """Load Whisper model."""
        try:
            logger.info(f"Loading Whisper model '{model_size}' on {self.device}...")
            logger.info("⏳ First run may take a while to download model...")
            
            self.model = WhisperModel(
                model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            
            logger.info(f"✅ Whisper model loaded ({model_size})")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            raise
    
    def listen(self) -> Optional[str]:
        """
        Listen for a voice command and return transcribed text.
        Includes retry logic for better reliability.
        
        Returns:
            Transcribed command text, or None if no command detected or error occurred
        """
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retry attempt {attempt}/{self.max_retries}")
                
                with self.microphone as source:
                    # Adjust for ambient noise briefly
                    if attempt == 0:
                        logger.info("🎤 Adjusting for ambient noise...")
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    
                    logger.info("🎧 Listening for command...")
                    
                    # Listen for audio
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.timeout_seconds,
                        phrase_time_limit=self.phrase_time_limit
                    )
                    
                    logger.info("🔄 Processing audio with Whisper...")
                    
                    # Save audio to temporary WAV file
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                        with wave.open(tmp_path, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(audio.sample_width)
                            wav_file.setframerate(audio.sample_rate)
                            wav_file.writeframes(audio.get_wav_data())
                    
                    try:
                        # Transcribe with Whisper
                        segments, info = self.model.transcribe(
                            tmp_path,
                            language="en",
                            beam_size=5,
                            vad_filter=True,  # Voice activity detection
                            vad_parameters=dict(
                                min_silence_duration_ms=500
                            )
                        )
                        
                        # Collect all segments
                        text_segments = []
                        for segment in segments:
                            text_segments.append(segment.text)
                        
                        command_text = " ".join(text_segments).strip()
                        
                        # Cleanup temp file
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
                        
                        if command_text:
                            logger.info(f"✅ Command recognized: '{command_text}'")
                            return command_text
                        else:
                            logger.warning("⚠️ No speech detected in audio")
                            if attempt < self.max_retries:
                                continue
                            return None
                            
                    except Exception as e:
                        logger.error(f"❌ Whisper transcription error: {e}")
                        # Cleanup temp file
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
                        
                        if attempt < self.max_retries:
                            continue
                        return None
                    
            except sr.WaitTimeoutError:
                logger.warning(f"⏱️ No speech detected within {self.timeout_seconds}s timeout")
                if attempt < self.max_retries:
                    continue
                return None
                
            except sr.UnknownValueError:
                logger.warning("⚠️ Could not understand audio")
                if attempt < self.max_retries:
                    continue
                return None
                
            except Exception as e:
                logger.error(f"❌ Error during listening: {e}")
                if attempt < self.max_retries:
                    continue
                return None
        
        # All retries exhausted
        logger.warning(f"❌ Failed after {self.max_retries + 1} attempts")
        return None
