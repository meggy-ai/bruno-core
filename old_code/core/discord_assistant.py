"""
Bruno Discord Assistant - Discord-specific implementation
Handles Discord messages, voice messages, and slash commands
"""

import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

from bruno.utils.config import BrunoConfig
from bruno.core.base_assistant import BaseBrunoAssistant

logger = logging.getLogger(__name__)


class BrunoDiscordAssistant(BaseBrunoAssistant):
    """Discord-based Bruno assistant (inherits common logic from base)."""
    
    def __init__(self, config: BrunoConfig = None):
        """Initialize Discord assistant."""
        super().__init__(config)
        
        # Discord-specific components (set by Discord bot)
        self.discord_message = None  # Current Discord message being processed
        self.discord_channel = None  # Current Discord channel
        self.transcriber = None      # Audio transcriber for voice messages
        
        # Initialize components immediately (Discord doesn't use start() pattern)
        self._initialize_components()
        
        logger.info("📱 Discord assistant initialized")
    
    def _initialize_components(self):
        """Initialize common components for Discord mode."""
        try:
            # Setup input/output methods (no-op for Discord)
            self._setup_input_method()
            self._setup_output_method()
            
            # Setup common components (LLM, memory, abilities)
            if not self._setup_common_components():
                logger.error("❌ Failed to setup common components")
                raise RuntimeError("Failed to initialize Discord assistant components")
            
            logger.info("✅ Discord assistant components ready")
        except Exception as e:
            logger.error(f"❌ Error initializing Discord assistant: {e}")
            raise
    
    # ============================================
    # Implementation of Abstract Methods
    # ============================================
    
    def _setup_input_method(self) -> bool:
        """Setup Discord input (handled by Discord bot events)."""
        logger.info("📱 Using Discord message events")
        return True
    
    def _setup_output_method(self) -> bool:
        """Setup Discord output (handled by Discord bot)."""
        logger.info("💬 Using Discord message sending")
        return True
    
    def _get_user_input(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Get input from Discord message.
        
        Note: This is not used in Discord mode as input is event-driven.
        Discord messages are processed via process_discord_message().
        
        Args:
            timeout: Ignored for Discord
            
        Returns:
            None (Discord uses event-driven processing)
        """
        return None
    
    def _send_output(self, text: str, prefix: str = "🤖") -> None:
        """
        Send output to Discord channel.
        
        Note: This is handled asynchronously by the Discord bot.
        Use send_discord_response() instead.
        
        Args:
            text: Text to send
            prefix: Ignored for Discord
        """
        # This is a sync method but Discord needs async
        # The actual sending is handled by send_discord_response()
        pass
    
    def _run_main_loop(self) -> bool:
        """
        Run Discord bot loop.
        
        Note: Discord bot runs its own event loop via discord.py.
        This method is not used in Discord mode.
        
        Returns:
            True (Discord bot manages its own loop)
        """
        return True
    
    def _cleanup_resources(self) -> None:
        """Cleanup Discord-specific resources."""
        # Discord bot handles its own cleanup
        pass
    
    # ============================================
    # Hook Method Overrides
    # ============================================
    
    def _get_memory_db_path(self) -> Optional[str]:
        """Use default database for Discord mode."""
        return None  # Use config default (bruno_memory.db)
    
    def _get_session_title(self) -> str:
        """Session title for Discord interface."""
        if self.discord_message:
            return f"Discord - {self.discord_message.author.display_name}"
        return "Discord Session"
    
    def _should_enable_tts(self) -> bool:
        """TTS can be enabled for Discord (local machine)."""
        return self.config.get('discord.local_actions.enable_tts', True)
    
    # ============================================
    # Discord-Specific Methods
    # ============================================
    
    async def process_discord_message(
        self,
        message,
        content: str,
        user_id: str = None,
        username: str = None
    ) -> dict:
        """
        Process Discord message using shared command processing logic.
        
        Args:
            message: Discord message object
            content: Message content (cleaned)
            user_id: Discord user ID
            username: Discord username
            
        Returns:
            Response dict with 'success', 'text', 'actions', etc.
        """
        # Store message context for session title
        self.discord_message = message
        self.discord_channel = message.channel if message else None
        
        # Use shared command processing from base class
        response = self.process_command(
            content,
            channel='discord',
            user_id=user_id or (str(message.author.id) if message else None),
            username=username or (message.author.display_name if message else None)
        )
        
        return response
    
    async def process_voice_message(
        self,
        message,
        audio_path: Path,
        language: str = 'en'
    ) -> dict:
        """
        Process Discord voice message attachment.
        
        Args:
            message: Discord message with audio attachment
            audio_path: Path to downloaded audio file
            language: Language for transcription
            
        Returns:
            Response dict with transcription and AI response
        """
        if not self.transcriber:
            return {
                'success': False,
                'error': 'Audio transcriber not available',
                'text': 'Sorry, voice message processing is not available.'
            }
        
        try:
            # Transcribe audio
            transcribed_text = self.transcriber.transcribe(audio_path, language=language)
            
            if not transcribed_text:
                return {
                    'success': False,
                    'error': 'Transcription failed',
                    'text': 'Sorry, I couldn\'t understand the audio. Please try again or send a text message.',
                    'transcription': None
                }
            
            logger.info(f"📝 Transcribed: {transcribed_text}")
            
            # Process transcribed text using shared logic
            response = await self.process_discord_message(
                message,
                transcribed_text,
                user_id=str(message.author.id),
                username=message.author.display_name
            )
            
            # Add transcription to response
            response['transcription'] = transcribed_text
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing voice message: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'text': 'Sorry, I encountered an error processing your voice message.',
                'transcription': None
            }
    
    async def send_discord_response(
        self,
        channel,
        text: str,
        max_length: int = 2000
    ):
        """
        Send response to Discord channel.
        
        Discord has a 2000 character limit, so split if needed.
        
        Args:
            channel: Discord channel to send to
            text: Text to send
            max_length: Maximum message length (default: 2000)
        """
        if not text:
            return
        
        # Split long messages
        if len(text) <= max_length:
            await channel.send(text)
        else:
            # Split by newlines first, then by chunks
            chunks = []
            current_chunk = ""
            
            for line in text.split('\n'):
                if len(current_chunk) + len(line) + 1 <= max_length:
                    current_chunk += line + '\n'
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line + '\n'
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # Send each chunk
            for i, chunk in enumerate(chunks):
                if i > 0:
                    await asyncio.sleep(0.5)  # Small delay between messages
                await channel.send(chunk)
    
    def set_transcriber(self, transcriber):
        """
        Set audio transcriber for voice messages.
        
        Args:
            transcriber: AudioTranscriber instance
        """
        self.transcriber = transcriber
        logger.info(f"✅ Audio transcriber set: {transcriber.engine if transcriber else None}")
    
    # ============================================
    # Override conversation state for Discord
    # ============================================
    
    def update_conversation_state(self, command: str) -> str:
        """
        Discord doesn't use conversation mode (always listens).
        Override to disable conversation mode behavior.
        
        Args:
            command: User command
            
        Returns:
            'continue' always (Discord doesn't sleep)
        """
        # Discord is always listening (event-driven), no conversation mode needed
        return 'continue'
