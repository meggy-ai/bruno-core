"""
Audio transcription service for voice messages.

Supports multiple transcription engines with automatic fallback:
- Faster Whisper (offline, fast, accurate) - Primary
- Google Speech Recognition (online) - Fallback
"""

import logging
from pathlib import Path
from typing import Optional, Literal
import tempfile

logger = logging.getLogger("bruno.speech.transcription")


class AudioTranscriber:
    """
    Transcribes audio files to text.
    
    Supports:
    - Faster Whisper (offline, fast, accurate)
    - Google Speech Recognition (online, requires internet)
    
    Example:
        transcriber = AudioTranscriber(engine='faster_whisper')
        text = transcriber.transcribe(Path('audio.ogg'))
        print(f"Transcribed: {text}")
    """
    
    def __init__(self, 
                 engine: Literal['faster_whisper', 'google', 'auto'] = 'auto',
                 model_size: str = 'small'):
        """
        Initialize transcriber.
        
        Args:
            engine: Primary transcription engine to use
                - 'faster_whisper': Use Faster Whisper (offline)
                - 'google': Use Google Speech Recognition (online)
                - 'auto': Auto-detect best available engine
            model_size: Whisper model size ('tiny', 'small', 'base', 'medium', 'large')
        """
        self.engine = engine
        self.model_size = model_size
        self.faster_whisper_model = None
        self.google_recognizer = None
        
        # Auto-detect best engine
        if engine == 'auto':
            if self._try_load_faster_whisper():
                self.engine = 'faster_whisper'
            elif self._try_load_google():
                self.engine = 'google'
            else:
                raise ImportError("No transcription engine available! Install faster-whisper or SpeechRecognition")
        
        # Load specified engine
        elif engine == 'faster_whisper':
            if not self._try_load_faster_whisper():
                logger.warning("⚠️  faster-whisper not available, falling back to Google SR")
                self.engine = 'google'
                self._try_load_google()
        
        elif engine == 'google':
            if not self._try_load_google():
                raise ImportError("Google Speech Recognition not available!")
        
        logger.info(f"✅ AudioTranscriber initialized with engine: {self.engine}")
    
    def _try_load_faster_whisper(self) -> bool:
        """Try to load Faster Whisper model."""
        try:
            from faster_whisper import WhisperModel
            logger.info(f"📥 Loading Faster Whisper model: {self.model_size}")
            self.faster_whisper_model = WhisperModel(self.model_size, device="cpu")
            logger.info("✅ Faster Whisper loaded")
            return True
        except ImportError:
            logger.debug("faster-whisper not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to load Faster Whisper: {e}")
            return False
    
    def _try_load_google(self) -> bool:
        """Try to load Google Speech Recognition."""
        try:
            import speech_recognition as sr
            self.google_recognizer = sr.Recognizer()
            logger.info("✅ Google Speech Recognition ready")
            return True
        except ImportError:
            logger.debug("SpeechRecognition not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to load Google SR: {e}")
            return False
    
    def transcribe(self, audio_path: Path, language: Optional[str] = "en") -> Optional[str]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file (.ogg, .mp3, .wav, .m4a, .webm)
            language: Language code (e.g., 'en', 'es', 'fr') or None for auto-detect
            
        Returns:
            Transcribed text or None if failed
            
        Example:
            text = transcriber.transcribe(Path('message.ogg'))
        """
        if not audio_path.exists():
            logger.error(f"❌ Audio file not found: {audio_path}")
            return None
        
        logger.info(f"🎤 Transcribing: {audio_path.name} (engine: {self.engine})")
        
        # Try primary engine
        if self.faster_whisper_model:
            text = self._transcribe_faster_whisper(audio_path, language)
            if text:
                return text
            logger.warning("⚠️  Faster Whisper failed, trying Google SR")
        
        # Fallback to Google SR
        if self.google_recognizer:
            text = self._transcribe_google(audio_path, language)
            if text:
                return text
        
        logger.error("❌ All transcription methods failed")
        return None
    
    def _transcribe_faster_whisper(self, audio_path: Path, language: Optional[str]) -> Optional[str]:
        """Transcribe using Faster Whisper."""
        try:
            logger.debug(f"Transcribing with Faster Whisper...")
            
            segments, info = self.faster_whisper_model.transcribe(
                str(audio_path),
                beam_size=5,
                language=language,  # None for auto-detect
                vad_filter=True,  # Filter silence
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Combine all segments
            text = " ".join([segment.text.strip() for segment in segments])
            
            if text:
                logger.info(f"✅ Transcribed ({len(text)} chars): {text[:100]}...")
                return text.strip()
            
            logger.warning("No text extracted from audio")
            return None
            
        except Exception as e:
            logger.error(f"❌ Faster Whisper error: {e}")
            return None
    
    def _transcribe_google(self, audio_path: Path, language: Optional[str]) -> Optional[str]:
        """Transcribe using Google Speech Recognition."""
        try:
            import speech_recognition as sr
            
            logger.debug(f"Transcribing with Google SR...")
            
            # Convert to WAV if needed (Google SR requires WAV)
            wav_path = self._convert_to_wav(audio_path)
            
            with sr.AudioFile(str(wav_path)) as source:
                audio = self.google_recognizer.record(source)
                
                # Use language if specified
                if language:
                    text = self.google_recognizer.recognize_google(audio, language=language)
                else:
                    text = self.google_recognizer.recognize_google(audio)
                
                if text:
                    logger.info(f"✅ Transcribed ({len(text)} chars): {text[:100]}...")
                    return text.strip()
            
            return None
            
        except sr.UnknownValueError:
            logger.error("❌ Google SR could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"❌ Google SR API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Google SR error: {e}")
            return None
    
    def _convert_to_wav(self, audio_path: Path) -> Path:
        """
        Convert audio file to WAV format if needed.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Path to WAV file (original if already WAV, or converted)
        """
        if audio_path.suffix.lower() == '.wav':
            return audio_path
        
        try:
            from pydub import AudioSegment
            import shutil
            
            # Check if ffmpeg is available
            if not shutil.which('ffmpeg'):
                logger.error("❌ ffmpeg not found in PATH. Install ffmpeg to convert audio files.")
                logger.error("   Download: https://ffmpeg.org/download.html")
                logger.error("   Or install via: winget install ffmpeg")
                raise FileNotFoundError("ffmpeg is required for audio conversion but not found in PATH")
            
            logger.debug(f"Converting {audio_path.suffix} to WAV using ffmpeg...")
            
            # Load audio file (pydub auto-detects format)
            audio = AudioSegment.from_file(str(audio_path))
            
            # Export as WAV
            wav_path = audio_path.with_suffix('.wav')
            audio.export(str(wav_path), format='wav')
            
            logger.info(f"🔄 Converted to WAV: {wav_path.name}")
            return wav_path
            
        except ImportError:
            logger.error("❌ pydub not installed. Install with: pip install pydub")
            raise
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Audio conversion error: {e}")
            # Return original and hope for the best
            return audio_path
    
    def transcribe_batch(self, audio_paths: list[Path], language: Optional[str] = "en") -> dict[Path, Optional[str]]:
        """
        Transcribe multiple audio files.
        
        Args:
            audio_paths: List of paths to audio files
            language: Language code or None for auto-detect
            
        Returns:
            Dictionary mapping file paths to transcribed text
            
        Example:
            files = [Path('msg1.ogg'), Path('msg2.ogg')]
            results = transcriber.transcribe_batch(files)
            for path, text in results.items():
                print(f"{path.name}: {text}")
        """
        results = {}
        
        for audio_path in audio_paths:
            text = self.transcribe(audio_path, language)
            results[audio_path] = text
        
        return results
    
    def get_engine_info(self) -> dict:
        """
        Get information about loaded transcription engines.
        
        Returns:
            Dictionary with engine status and capabilities
        """
        return {
            'current_engine': self.engine,
            'faster_whisper_available': self.faster_whisper_model is not None,
            'google_sr_available': self.google_recognizer is not None,
            'model_size': self.model_size if self.faster_whisper_model else None,
            'offline_capable': self.faster_whisper_model is not None
        }
