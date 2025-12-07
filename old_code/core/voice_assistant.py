"""
Bruno Voice Assistant - Voice-specific implementation
Handles wake word detection, speech recognition, and TTS
"""

import asyncio
import logging
import time
from typing import Optional

from bruno.utils.config import BrunoConfig
from bruno.core.base_assistant import BaseBrunoAssistant
from bruno.audio.windows_audio import WindowsAudioManager
from bruno.wake_word.vosk_detector import VoskWakeWordDetector
from bruno.commands.listener import CommandListener
from bruno.tts.windows_tts import WindowsTTS

# Optional imports (may fail due to DLL issues)
try:
    from bruno.commands.faster_whisper_listener import FasterWhisperListener
    FASTER_WHISPER_AVAILABLE = True
except Exception as e:
    logging.warning(f"⚠️ Faster Whisper not available (will use Google SR): {type(e).__name__}")
    FASTER_WHISPER_AVAILABLE = False

try:
    from bruno.tts.piper_tts import PiperTTS
    PIPER_TTS_AVAILABLE = True
except Exception as e:
    logging.warning(f"⚠️ Piper TTS not available (will use Windows TTS): {type(e).__name__}")
    PIPER_TTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class BrunoVoiceAssistant(BaseBrunoAssistant):
    """Voice-activated Bruno assistant (inherits common logic from base)."""
    
    def __init__(self, config: BrunoConfig = None):
        """Initialize voice assistant."""
        super().__init__(config)
        
        # Voice-specific components
        self.audio_manager = None
        self.wake_word_detector = None
        self.command_listener = None
        self.tts_engine = None
        self.device_index = None
        
        logger.info(f"📋 Using wake words: {', '.join(self.config.wake_words)}")
    
    # ============================================
    # Implementation of Abstract Methods
    # ============================================
    
    async def _setup_input_method(self) -> bool:
        """Setup voice input (wake word + speech recognition) - ASYNC."""
        # Setup audio device (blocking operation - run in thread pool)
        if not await asyncio.to_thread(self._setup_audio):
            return False
        
        # Setup wake word detector (blocking operation - run in thread pool)
        if not await asyncio.to_thread(self._setup_wake_word_detector):
            return False
        
        # Setup command listener (blocking operation - run in thread pool)
        if not await asyncio.to_thread(self._setup_command_listener):
            return False
        
        return True
    
    async def _setup_output_method(self) -> bool:
        """Setup voice output (TTS) - ASYNC."""
        return await asyncio.to_thread(self._setup_tts)
    
    async def _get_user_input(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Get voice input from user - ASYNC.
        
        Args:
            timeout: Optional timeout for listening
            
        Returns:
            Transcribed text or None
        """
        # Run blocking audio capture in thread pool
        return await asyncio.to_thread(self.command_listener.listen, timeout=timeout)
    
    async def _send_output(self, text: str, prefix: str = "🤖") -> None:
        """
        Send voice output to user via TTS - ASYNC.
        
        Args:
            text: Text to speak
            prefix: Ignored for voice output
        """
        if self.tts_engine:
            # Run blocking TTS in thread pool
            await asyncio.to_thread(self.tts_engine.speak, text)
    
    async def _run_main_loop(self) -> bool:
        """Run voice interaction loop with wake word detection - ASYNC."""
        try:
            logger.info("\n" + "="*60)
            logger.info("✅ BRUNO IS READY!")
            logger.info("="*60)
            logger.info("Wake words: 'bruno', 'hey bruno', 'jarvis'")
            logger.info("Press Ctrl+C to stop")
            logger.info("="*60 + "\n")
            
            # Say ready message
            await self._send_output("Bruno is ready")
            
            # Start listening for wake word (blocking operation - run in thread pool)
            await asyncio.to_thread(self.wake_word_detector.start, on_wake_word=self._on_wake_word_detected)
            
            # Keep running (use short sleep to be responsive to signals)
            try:
                while self.running and not self._shutdown_requested:
                    # Update music playback (auto-advance to next track if needed)
                    if self.music_manager:
                        self.music_manager.update_playback()
                    
                    await asyncio.sleep(0.1)  # Async sleep for faster shutdown response
            except KeyboardInterrupt:
                logger.info("\n\n⏹️  KeyboardInterrupt received...")
                self._shutdown_requested = True
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Error running Bruno: {e}")
            return False
        finally:
            self.stop()
    
    def _cleanup_resources(self) -> None:
        """Cleanup voice-specific resources."""
        # Stop wake word detector
        if self.wake_word_detector:
            try:
                logger.info("🎤 Stopping wake word detector...")
                self.wake_word_detector.stop()
            except Exception as e:
                logger.error(f"⚠️  Error stopping wake word detector: {e}")
        
        # Stop TTS engine
        if self.tts_engine:
            try:
                logger.info("🔊 Stopping TTS engine...")
                self.tts_engine.stop()
            except Exception as e:
                logger.error(f"⚠️  Error stopping TTS engine: {e}")
    
    # ============================================
    # Hook Method Overrides
    # ============================================
    
    def _get_memory_db_path(self) -> Optional[str]:
        """Use default database for voice mode."""
        return None  # Use config default (bruno_memory.db)
    
    def _get_session_title(self) -> str:
        """Session title for voice interface."""
        return "Bruno Voice Session"
    
    def _get_tts_engine(self) -> Optional[object]:
        """Get TTS engine for voice mode."""
        return self.tts_engine
    
    def _should_enable_tts(self) -> bool:
        """TTS enabled for voice mode."""
        return True
    
    # ============================================
    # Voice-Specific Setup Methods
    # ============================================
    
    def _setup_audio(self) -> bool:
        """Setup audio device."""
        try:
            logger.info("🔍 Setting up audio device...")
            self.audio_manager = WindowsAudioManager()
            
            # Use configured device or auto-select
            if self.config.device_index is not None:
                self.device_index = self.config.device_index
                logger.info(f"📌 Using configured device index: {self.device_index}")
            else:
                self.device_index = self.audio_manager.select_best_device()
            
            if self.device_index is None:
                logger.error("❌ No working audio device found!")
                logger.error("   Please close apps using microphone (Edge, Chrome, etc.)")
                logger.error("   Then run: python .\\tools\\bruno-doctor.py")
                return False
            
            devices = self.audio_manager.list_all_devices()
            device_info = devices[self.device_index]
            logger.info(f"✅ Audio device selected: {device_info['name']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup audio: {e}")
            return False
    
    def _setup_wake_word_detector(self) -> bool:
        """Setup wake word detector."""
        try:
            logger.info("🎤 Setting up wake word detector...")
            
            # Use configured model path (relative to project root, not this file)
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent
            model_path = project_root / self.config.model_path
            if not model_path.exists():
                logger.error(f"❌ Vosk model not found at: {model_path}")
                return False
            
            # Get VAD settings
            vosk_config = self.config.get('bruno.vosk', {})
            use_vad = vosk_config.get('use_vad', True)
            vad_aggressiveness = vosk_config.get('vad_aggressiveness', 2)
            
            self.wake_word_detector = VoskWakeWordDetector(
                model_path=str(model_path),
                wake_words=self.config.wake_words,
                sample_rate=self.config.sample_rate,
                device_index=self.device_index,
                use_vad=use_vad,
                vad_aggressiveness=vad_aggressiveness
            )
            
            logger.info("✅ Wake word detector ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup wake word detector: {e}")
            return False
    
    def _setup_command_listener(self) -> bool:
        """Setup command listener."""
        try:
            logger.info("🎧 Setting up command listener...")
            
            # Use configured command recognition parameters
            cmd_config = self.config.get('bruno.command_recognition', {})
            engine = cmd_config.get('engine', 'google')
            
            if engine == 'faster_whisper' and FASTER_WHISPER_AVAILABLE:
                try:
                    logger.info("📦 Using Faster Whisper (local, offline)...")
                    self.command_listener = FasterWhisperListener(
                        device_index=self.device_index,
                        timeout_seconds=cmd_config.get('timeout_seconds', 10.0),
                        phrase_time_limit=cmd_config.get('phrase_time_limit', 20),
                        energy_threshold=cmd_config.get('energy_threshold', 400),
                        pause_threshold=cmd_config.get('pause_threshold', 2.0),
                        max_retries=cmd_config.get('max_retries', 2),
                        model_size=cmd_config.get('whisper_model', 'base'),
                        device=cmd_config.get('whisper_device', 'auto'),
                        compute_type=cmd_config.get('whisper_compute_type', 'default')
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Faster Whisper failed to initialize: {e}")
                    logger.info("📦 Falling back to Google Speech Recognition...")
                    engine = 'google'
            
            if engine == 'google':
                logger.info("📦 Using Google Speech Recognition (online)...")
                self.command_listener = CommandListener(
                    device_index=self.device_index,
                    timeout_seconds=cmd_config.get('timeout_seconds', 10.0),
                    phrase_time_limit=cmd_config.get('phrase_time_limit', 20),
                    energy_threshold=cmd_config.get('energy_threshold', 400),
                    pause_threshold=cmd_config.get('pause_threshold', 2.0),
                    max_retries=cmd_config.get('max_retries', 2)
                )
            
            logger.info("✅ Command listener ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup command listener: {e}")
            return False
    
    def _setup_tts(self) -> bool:
        """Setup text-to-speech engine."""
        try:
            logger.info("🔊 Setting up text-to-speech...")
            
            # Use configured TTS parameters
            tts_config = self.config.get('bruno.tts', {})
            engine = tts_config.get('engine', 'piper')
            
            if engine == 'piper' and PIPER_TTS_AVAILABLE:
                try:
                    logger.info("🎙️ Using Piper TTS (fast local neural)...")
                    self.tts_engine = PiperTTS(
                        voice=tts_config.get('piper_voice', 'en_US-lessac-medium'),
                        speed=tts_config.get('piper_speed', 1.0),
                        data_dir=tts_config.get('piper_data_dir', 'piper_voices')
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Piper TTS failed to initialize: {e}")
                    logger.info("🎙️ Falling back to Windows native TTS...")
                    engine = 'windows_native'
            
            if engine == 'windows_native':
                logger.info("🎙️ Using Windows native TTS...")
                self.tts_engine = WindowsTTS(
                    rate=tts_config.get('rate', 0),
                    volume=tts_config.get('volume', 100)
                )
            
            logger.info("✅ TTS engine ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup TTS: {e}")
            return False
    
    # ============================================
    # Voice-Specific Event Handlers
    # ============================================
    
    def _on_wake_word_detected(self, wake_word: str):
        """
        Callback when wake word is detected (called from background thread).
        
        Args:
            wake_word: The detected wake word
        """
        # Check if shutdown is in progress
        if not self.running or self._shutdown_requested:
            logger.debug("Wake word detected but shutdown in progress, ignoring")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🔔 Wake word detected: '{wake_word}'")
        logger.info(f"{'='*60}\n")
        
        # Stop wake word detection temporarily
        self.wake_word_detector.stop()
        
        # Schedule async handling in the event loop
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(self._handle_wake_word(), loop)
    
    async def _handle_wake_word(self):
        """Handle wake word detection asynchronously."""
        # Give audio feedback
        await self._send_output("Yes?")
        await asyncio.sleep(0.5)  # Extra delay to ensure audio finishes
        
        # Listen for command
        command = await self._get_user_input()
        
        if command:
            # Process command (shared logic from base class)
            response = await self.process_command(command, channel='voice')
            
            if not response['success']:
                await self._send_output("Sorry, I encountered an error.")
            
            # Update conversation state (shared logic)
            state = self.update_conversation_state(command)
            
            if state == 'exit':
                await self._send_output("Goodbye!")
            elif state == 'max_reached':
                await self._send_output("I'll be here if you need me. Just say my wake word.")
        else:
            logger.warning("⚠️  No command detected")
            await self._send_output("I didn't catch that.")
        
        # Resume listening
        await self._resume_listening()
    
    async def _resume_listening(self):
        """Resume listening (wake word or conversation mode) - ASYNC."""
        if not self.running:
            return
        
        if self.in_conversation_mode:
            logger.info(f"\n💬 Conversation mode active (exchange {self.conversation_exchange_count}) - Listening for follow-up...\n")
            await self._continue_conversation()
        else:
            logger.info("\n🎤 Listening for wake word again...\n")
            await asyncio.to_thread(self.wake_word_detector.start, on_wake_word=self._on_wake_word_detected)
    
    async def _continue_conversation(self):
        """Continue conversation mode - listen for follow-up without wake word - ASYNC."""
        timeout = self.config.get('bruno.conversation_mode.inactivity_timeout', 30)
        await asyncio.sleep(0.5)
        
        logger.info(f"🎧 Listening for follow-up (timeout: {timeout}s)...")
        
        try:
            # Use configured command listener (respects Faster Whisper or Google SR setting)
            command = await self._get_user_input(timeout=timeout)
            
            if command:
                logger.info(f"📝 Follow-up: '{command}'")
                
                # Process command (shared logic)
                response = await self.process_command(command, channel='voice')
                
                # Update conversation state (shared logic)
                state = self.update_conversation_state(command)
                
                if state == 'exit':
                    await self._send_output("Goodbye!")
                    if self.running:
                        await asyncio.to_thread(self.wake_word_detector.start, on_wake_word=self._on_wake_word_detected)
                elif state == 'max_reached':
                    await self._send_output("I'll be here if you need me.")
                    if self.running:
                        await asyncio.to_thread(self.wake_word_detector.start, on_wake_word=self._on_wake_word_detected)
                elif state == 'continue' and self.running:
                    await self._continue_conversation()
            else:
                logger.info("⏸️  No follow-up detected, going to sleep")
                await self._send_output("I'll be here if you need me")
                self.end_conversation_mode()
                if self.running:
                    await asyncio.to_thread(self.wake_word_detector.start, on_wake_word=self._on_wake_word_detected)
                    
        except Exception as e:
            logger.error(f"❌ Error in conversation mode: {e}")
            await self._send_output("I'll be here if you need me")
            self.end_conversation_mode()
            if self.running:
                await asyncio.to_thread(self.wake_word_detector.start, on_wake_word=self._on_wake_word_detected)
