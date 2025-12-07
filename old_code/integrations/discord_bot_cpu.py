"""
Discord bot for Bruno Voice Assistant.

Allows users to interact with Bruno via Discord text and voice messages.
"""

import discord
from discord.ext import commands
import os
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from bruno.speech.transcription import AudioTranscriber
from bruno.integrations.discord_embeds import BrunoEmbeds
from bruno.core.base_assistant import BaseBrunoAssistant
from bruno.utils.config import BrunoConfig

logger = logging.getLogger("bruno.discord.bot")


class BrunoDiscordBot(BaseBrunoAssistant):
    """
    Discord bot for Bruno Voice Assistant.
    
    Extends BaseBrunoAssistant to inherit shared logic (LLM, memory, abilities).
    
    Features:
    - Responds to text messages mentioning "bruno"
    - Responds to DMs automatically
    - Maintains separate conversation context per Discord user
    - Optional: Speaks responses via TTS on local machine
    """
    
    def __init__(self, token: str, config: BrunoConfig):
        """
        Initialize Discord bot.
        
        Args:
            token: Discord bot token
            config: BrunoConfig instance
        """
        # Initialize base assistant (sets up LLM, memory, abilities)
        super().__init__(config)
        
        # Store token for later use
        self.token = token
        
        # Audio transcriber for voice messages (lazy-loaded to avoid crash on Windows)
        self.transcriber = None
        self._transcriber_initialized = False
        self._transcriber_failed = False
        
        # TTS engine for local responses (if enabled in config)
        self.tts_engine = None
        if self.config.get('discord.local_actions.enable_tts', True):
            self._setup_tts()
        
        # Bot configuration
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message text
        intents.guilds = True
        intents.guild_messages = True
        intents.dm_messages = True
        
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Rich embeds
        self.embeds = None  # Will be initialized in on_ready
        
        # Slash commands enabled
        self.slash_commands_enabled = config.get('discord.slash_commands.enabled', True)
        
        # Rate limiting
        self.user_last_message: dict[int, datetime] = {}
        self.cooldown_seconds = config.get('discord.rate_limit.cooldown_seconds', 2)
        
        # Per-user conversation context (Discord user ID -> context)
        self.user_contexts: dict[int, dict] = {}
        
        # Per-user conversation sessions (Discord user ID -> conversation_id)
        # Tracks active memory sessions for each Discord user
        self.user_conversation_sessions: dict[int, int] = {}
        
        # Components initialization flag
        self._components_initialized = False
        
        # Register event handlers
        self._register_handlers()
        
        # Register slash commands if enabled
        if self.slash_commands_enabled:
            self._register_slash_commands()
        
        logger.info("✅ BrunoDiscordBot initialized")
    
    # ===== BaseBrunoAssistant Abstract Methods =====
    
    async def _setup_input_method(self) -> bool:
        """Setup input method (no-op for Discord - uses events)."""
        return True
    
    async def _setup_output_method(self) -> bool:
        """Setup output method (no-op for Discord - uses Discord API)."""
        return True
    
    async def _get_user_input(self, timeout: Optional[float] = None) -> Optional[str]:
        """Get user input (not used in Discord - handled by events)."""
        raise NotImplementedError("Discord bot uses event-driven message handling")
    
    async def _send_output(self, text: str, prefix: str = "🤖") -> None:
        """Send output (not used in Discord - handled by send_discord_response)."""
        raise NotImplementedError("Discord bot uses send_discord_response")
    
    async def _run_main_loop(self) -> bool:
        """Run main loop (Discord uses bot.run instead)."""
        raise NotImplementedError("Discord bot uses bot.run")
    
    def _cleanup_resources(self) -> None:
        """Cleanup Discord resources."""
        try:
            if self.transcriber:
                self.transcriber.cleanup()
            logger.info("✅ Discord resources cleaned up")
        except Exception as e:
            logger.error(f"❌ Error cleaning up Discord resources: {e}")
    
    def _get_memory_db_path(self) -> str:
        """Get Discord-specific memory database path."""
        return "bruno_memory_discord.db"
    
    def _get_session_title(self) -> str:
        """Get session title with Discord username if available."""
        if hasattr(self, '_current_discord_user') and self._current_discord_user:
            return f"Discord: {self._current_discord_user}"
        return "Discord Session"
    
    def _should_enable_tts(self) -> bool:
        """Check if TTS should be enabled (Discord local actions)."""
        return self.config.get('discord.local_actions.enable_tts', True)
    
    def _handle_timer_notification(self, event_type: str, message: str, timer_info: dict):
        """
        Handle timer notifications and send to Discord.
        
        Args:
            event_type: 'progress' or 'complete'
            message: Message text to send
            timer_info: Dictionary with timer details
        """
        # Find the most recent Discord user who set a timer
        # In a more sophisticated implementation, you'd track which user created which timer
        if self.user_contexts:
            # Get the most recent user context
            most_recent_user_id = max(self.user_contexts.keys())
            context = self.user_contexts[most_recent_user_id]
            channel = context.get('channel')
            
            if channel:
                # Schedule sending the message using the bot's event loop
                # This is called from a background thread, so we need to use asyncio.run_coroutine_threadsafe
                try:
                    loop = self.bot.loop
                    if loop and loop.is_running():
                        asyncio.run_coroutine_threadsafe(self._send_timer_notification(channel, message), loop)
                except Exception as e:
                    logger.error(f"Failed to schedule timer notification: {e}")
    
    async def _send_timer_notification(self, channel, message: str):
        """Send timer notification to Discord channel."""
        try:
            await channel.send(message)
        except Exception as e:
            logger.error(f"Failed to send timer notification: {e}")
    
    def _handle_alarm_notification(self, event_type: str, message: str, alarm_info: dict):
        """
        Handle alarm notifications and send to Discord.
        
        Args:
            event_type: 'trigger'
            message: Message text to send
            alarm_info: Dictionary with alarm details
        """
        # Find the most recent Discord user who set an alarm
        if self.user_contexts:
            # Get the most recent user context
            most_recent_user_id = max(self.user_contexts.keys())
            context = self.user_contexts[most_recent_user_id]
            channel = context.get('channel')
            
            if channel:
                # Schedule sending the message using the bot's event loop
                try:
                    loop = self.bot.loop
                    if loop and loop.is_running():
                        asyncio.run_coroutine_threadsafe(self._send_alarm_notification(channel, message), loop)
                except Exception as e:
                    logger.error(f"Failed to schedule alarm notification: {e}")
    
    async def _send_alarm_notification(self, channel, message: str):
        """Send alarm notification to Discord channel."""
        try:
            await channel.send(message)
        except Exception as e:
            logger.error(f"Failed to send alarm notification: {e}")
    
    def _ensure_user_conversation(self, user_id: int, username: str) -> bool:
        """
        Ensure a conversation session exists for this Discord user.
        
        Creates a new conversation or resumes existing one based on:
        - Active session in memory (same user continued chatting)
        - Recent session in database (user returned after bot restart)
        
        Args:
            user_id: Discord user ID
            username: Discord username for session title
            
        Returns:
            True if conversation is ready, False if memory unavailable
        """
        if not self.conversation_manager:
            logger.warning("⚠️  Memory system not available for Discord user conversations")
            return False
        
        # Check if user already has active session (cached)
        if user_id in self.user_conversation_sessions:
            conv_id = self.user_conversation_sessions[user_id]
            # Resume only if not currently active (avoid redundant DB queries)
            if self.conversation_manager.current_conversation_id != conv_id:
                # Switch to user's conversation
                if self.conversation_manager.resume_conversation(conv_id):
                    logger.debug(f"🔄 Switched to conversation {conv_id} for user {user_id}")
                else:
                    # Conversation no longer valid, remove from cache
                    logger.warning(f"⚠️ Cached conversation {conv_id} invalid, will search for new one")
                    del self.user_conversation_sessions[user_id]
            else:
                logger.debug(f"✅ Using active conversation {conv_id} for user {user_id}")
                return True
            return True
        
        # Try to find recent conversation for this user
        if self.memory_store:
            # Search for conversations with this user's Discord ID in title/context
            recent_convs = self.memory_store.get_recent_conversations(limit=10)
            user_conv = None
            
            for conv in recent_convs:
                # Check if conversation belongs to this Discord user
                # Match by session title containing Discord user ID
                title = conv.get('title') or ''  # Handle None case
                if f"Discord:{user_id}" in title or f"@{username}" in title:
                    # Found user's conversation
                    user_conv = conv
                    break
            
            # Resume existing conversation if found
            if user_conv and not user_conv.get('ended_at'):
                conv_id = user_conv['id']
                if self.conversation_manager.resume_conversation(conv_id):
                    self.user_conversation_sessions[user_id] = conv_id
                    logger.info(f"🔄 Resumed conversation {conv_id} for Discord user {username} (ID: {user_id})")
                    return True
        
        # Start new conversation for this user
        title = f"Discord:{user_id} @{username}"
        
        conv_id, session_id = self.conversation_manager.start_conversation(
            title=title
        )
        
        self.user_conversation_sessions[user_id] = conv_id
        logger.info(f"🆕 Started new conversation {conv_id} for Discord user {username} (ID: {user_id})")
        
        return True
    
    def _get_tts_engine(self) -> Optional[object]:
        """Get TTS engine for Discord local actions."""
        logger.debug(f"🔍 _get_tts_engine() called, tts_engine={self.tts_engine}")
        return self.tts_engine
    
    def _setup_tts(self) -> bool:
        """
        Setup text-to-speech engine for Discord local actions.
        
        Returns:
            True if TTS is available, False otherwise
        """
        try:
            # Import TTS engines
            from bruno.tts.windows_tts import WindowsTTS
            try:
                from bruno.tts.piper_tts import PiperTTS
                PIPER_TTS_AVAILABLE = True
            except ImportError:
                PIPER_TTS_AVAILABLE = False
            
            logger.info("🔊 Setting up text-to-speech for Discord local actions...")
            
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
                    logger.info("✅ TTS engine ready (Piper)")
                    return True
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
                logger.info("✅ TTS engine ready (Windows native)")
                return True
            
            logger.warning("⚠️ No TTS engine configured")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to setup TTS: {e}", exc_info=True)
            return False
    
    # ===== Discord-Specific Methods =====
    
    def _ensure_transcriber_initialized(self) -> bool:
        """
        Lazy-initialize transcriber on first use to avoid Windows crashes.
        
        Returns:
            True if transcriber is available, False otherwise
        """
        if self._transcriber_initialized or self._transcriber_failed:
            return self.transcriber is not None
        
        try:
            transcription_engine = self.config.get('speech.transcription_engine', 'auto')
            model_size = self.config.get('speech.faster_whisper.model', 'small')
            logger.info(f"📥 Initializing transcriber (engine={transcription_engine}, model={model_size})...")
            self.transcriber = AudioTranscriber(engine=transcription_engine, model_size=model_size)
            logger.info(f"✅ Audio transcriber ready: {self.transcriber.engine}")
            self._transcriber_initialized = True
            return True
        except Exception as e:
            logger.error(f"❌ Could not initialize transcriber: {e}", exc_info=True)
            logger.warning("⚠️  Voice message transcription disabled - audio attachments will be ignored")
            self._transcriber_failed = True
            self.transcriber = None
            return False
    
    def _register_handlers(self):
        """Register Discord event handlers."""
        
        @self.bot.event
        async def on_ready():
            """Called when bot successfully connects to Discord."""
            # Initialize components on first ready (only once)
            if not self._components_initialized:
                logger.info("🔧 Initializing Bruno components...")
                try:
                    if not await self._setup_common_components():
                        logger.error("❌ Failed to initialize components")
                        return
                    self._components_initialized = True
                    logger.info("✅ Components initialized")
                except Exception as e:
                    logger.error(f"❌ Error initializing components: {e}", exc_info=True)
                    return
            
            logger.info(f"🤖 Bruno Discord bot logged in as {self.bot.user} (ID: {self.bot.user.id})")
            logger.info(f"📊 Connected to {len(self.bot.guilds)} server(s)")
            
            # Print server IDs for easy config setup
            if self.bot.guilds:
                logger.info("=" * 70)
                logger.info("📋 Your Discord Servers (copy Guild ID for config.yaml):")
                for guild in self.bot.guilds:
                    logger.info(f"   • {guild.name}: {guild.id}")
                logger.info("=" * 70)
            
            # Initialize embeds with bot user
            self.embeds = BrunoEmbeds(bot_user=self.bot.user)
            
            # Register timer callback for Discord notifications
            if self.timer_manager:
                self.timer_manager.set_external_callback(self._handle_timer_notification)
                logger.info("✅ Timer Discord callback registered")
            else:
                logger.warning("⚠️  Timer manager not available, notifications disabled")
            
            # Register alarm callback for Discord notifications
            if self.alarm_manager:
                self.alarm_manager.set_external_callback(self._handle_alarm_notification)
                logger.info("✅ Alarm Discord callback registered")
            else:
                logger.warning("⚠️  Alarm manager not available, notifications disabled")
            
            # Sync slash commands if enabled
            if self.slash_commands_enabled:
                try:
                    # Check if dev guild ID specified for faster sync
                    dev_guild_id = self.config.get('discord.slash_commands.dev_guild_id')
                    
                    if dev_guild_id:
                        # Sync to specific guild (instant)
                        guild = discord.Object(id=dev_guild_id)
                        self.bot.tree.copy_global_to(guild=guild)
                        await self.bot.tree.sync(guild=guild)
                        logger.info(f"✅ Slash commands synced to dev guild {dev_guild_id}")
                    elif self.config.get('discord.slash_commands.sync_global', False):
                        # Sync globally (takes up to 1 hour)
                        await self.bot.tree.sync()
                        logger.info("✅ Slash commands synced globally (may take up to 1 hour)")
                    else:
                        logger.info("⚠️  Slash commands registered but not synced. Set sync_global=true or dev_guild_id in config.")
                except Exception as e:
                    logger.error(f"❌ Failed to sync slash commands: {e}")
            
            # Set bot status
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name="your commands | Say 'bruno' to talk"
            )
            await self.bot.change_presence(activity=activity)
            
            logger.info("✅ Bruno Discord bot ready")
        
        @self.bot.event
        async def on_message(message: discord.Message):
            """Handle incoming Discord messages."""
            # Don't respond to ourselves or other bots
            if message.author.bot:
                return
            
            # Check if we should respond to this message
            if not self._should_respond(message):
                return
            
            # Rate limiting check
            if not self._check_rate_limit(message.author.id):
                logger.debug(f"⏱️  Rate limit hit for user {message.author.id}")
                return
            
            # Check for voice message attachments
            has_audio = any(
                attachment.content_type and 'audio' in attachment.content_type 
                for attachment in message.attachments
            )
            
            if has_audio and self.transcriber:
                # Process as voice message
                await self._handle_voice_message(message)
            else:
                # Process as text message
                await self._handle_text_message(message)
    
    def _should_respond(self, message: discord.Message) -> bool:
        """
        Determine if bot should respond to this message.
        
        Rules:
        - Respond to DMs automatically
        - In servers, respond only if "bruno" mentioned
        - Configurable prefix (default: none)
        
        Args:
            message: Discord message
            
        Returns:
            True if should respond, False otherwise
        """
        # Always respond to DMs
        is_dm = isinstance(message.channel, discord.DMChannel)
        if is_dm:
            respond_to_dms = self.config.get('discord.respond_to_dms', True)
            return respond_to_dms
        
        # In servers, check for "bruno" mention
        content_lower = message.content.lower()
        respond_to_mentions = self.config.get('discord.respond_to_mentions', True)
        
        if respond_to_mentions and 'bruno' in content_lower:
            return True
        
        # Check if bot was @mentioned
        if self.bot.user in message.mentions:
            return True
        
        return False
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user is rate limited.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.now()
        
        if user_id in self.user_last_message:
            time_since_last = (now - self.user_last_message[user_id]).total_seconds()
            if time_since_last < self.cooldown_seconds:
                return False
        
        self.user_last_message[user_id] = now
        return True
    
    async def _handle_text_message(self, message: discord.Message):
        """
        Process text-only message.
        
        Args:
            message: Discord message
        """
        try:
            # Clean message content
            content = message.content.strip()
            
            # Remove "bruno" from the message if present
            content_clean = content.lower().replace('bruno', '', 1).strip()
            if not content_clean:
                content_clean = content  # Keep original if nothing left
            
            # Show typing indicator
            show_typing = self.config.get('discord.formatting.show_typing', True)
            
            async with message.channel.typing() if show_typing else asyncio.nullcontext():
                # Store Discord context for this user
                user_id = message.author.id
                self.user_contexts[user_id] = {
                    'message': message,
                    'channel': message.channel,
                    'username': message.author.display_name
                }
                self._current_discord_user = message.author.display_name
                
                # Ensure user has active conversation session (per-user memory)
                await asyncio.to_thread(
                    self._ensure_user_conversation,
                    user_id,
                    message.author.display_name
                )
                
                # Process command using inherited async process_command
                logger.info(f"📨 Processing message from {message.author}: '{content_clean}'")
                response = await self.process_command(
                    command=content_clean,
                    channel='discord',
                    user_id=str(message.author.id),
                    username=message.author.display_name
                )
                
                # Send response
                if response['success']:
                    await self._send_discord_response(message.channel, response['text'])
                else:
                    error_msg = response.get('error', 'Unknown error')
                    await self._send_discord_response(message.channel, f"Sorry, I encountered an error: {error_msg}")
        
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}", exc_info=True)
            await message.channel.send("Sorry, I encountered an error processing your message.")
    
    async def _handle_voice_message(self, message: discord.Message):
        """
        Process voice message attachment.
        
        Args:
            message: Discord message with audio attachment
        """
        try:
            # Ensure transcriber is initialized
            if not self._ensure_transcriber_initialized():
                await message.channel.send("Sorry, audio transcription is not available.")
                return
            
            # Find first audio attachment
            audio_attachment = None
            for attachment in message.attachments:
                if attachment.content_type and 'audio' in attachment.content_type:
                    audio_attachment = attachment
                    break
            
            if not audio_attachment:
                return
            
            logger.info(f"🎤 Voice message detected: {audio_attachment.filename} from {message.author}")
            
            # Show typing indicator
            show_typing = self.config.get('discord.formatting.show_typing', True)
            
            async with message.channel.typing() if show_typing else asyncio.nullcontext():
                # Create temp directory for audio files
                temp_dir = Path(tempfile.gettempdir()) / "bruno_discord_audio"
                temp_dir.mkdir(exist_ok=True)
                
                # Download audio file
                audio_path = temp_dir / f"{message.id}_{audio_attachment.filename}"
                
                try:
                    await audio_attachment.save(audio_path)
                    logger.info(f"📥 Downloaded: {audio_path.name}")
                    
                    # Transcribe audio
                    transcription = await asyncio.to_thread(
                        self.transcriber.transcribe_audio_file,
                        str(audio_path)
                    )
                    
                    if not transcription:
                        await message.channel.send("Sorry, I couldn't understand the audio.")
                        return
                    
                    # Show transcription to user
                    use_emoji = self.config.get('discord.formatting.use_emoji', True)
                    transcription_msg = f"🎤 Heard: *{transcription}*" if use_emoji else f"Heard: {transcription}"
                    await message.channel.send(transcription_msg)
                    
                    # Store Discord context for this user
                    user_id = message.author.id
                    self.user_contexts[user_id] = {
                        'message': message,
                        'channel': message.channel,
                        'username': message.author.display_name
                    }
                    self._current_discord_user = message.author.display_name
                    
                    # Ensure user has active conversation session (per-user memory)
                    await asyncio.to_thread(
                        self._ensure_user_conversation,
                        user_id,
                        message.author.display_name
                    )
                    
                    # Process command using inherited async process_command
                    logger.info(f"🎤 Processing voice command from {message.author}: '{transcription}'")
                    response = await self.process_command(
                        command=transcription,
                        channel='discord',
                        user_id=str(message.author.id),
                        username=message.author.display_name
                    )
                    
                    # Send response
                    if response['success']:
                        await self._send_discord_response(message.channel, response['text'])
                    else:
                        error_msg = response.get('error', 'Unknown error')
                        await self._send_discord_response(message.channel, f"Sorry, I encountered an error: {error_msg}")
                
                finally:
                    # Clean up temp file
                    cleanup = self.config.get('speech.audio.cleanup_temp_files', True)
                    if cleanup and audio_path.exists():
                        try:
                            audio_path.unlink()
                            logger.debug(f"🗑️  Cleaned up: {audio_path.name}")
                        except Exception as e:
                            logger.warning(f"⚠️  Could not delete temp file: {e}")
        
        except Exception as e:
            logger.error(f"❌ Error handling voice message: {e}", exc_info=True)
            await message.channel.send("Sorry, I encountered an error processing your voice message.")
    
    async def _send_discord_response(self, channel, text: str, max_length: int = 2000):
        """
        Send response to Discord channel with proper formatting and splitting.
        
        Args:
            channel: Discord channel to send to
            text: Text to send
            max_length: Maximum message length (default: 2000)
        """
        try:
            if not text:
                return
            
            # Split message if too long
            if len(text) <= max_length:
                await channel.send(text)
            else:
                # Split by paragraphs first
                paragraphs = text.split('\n\n')
                current_chunk = ""
                
                for para in paragraphs:
                    if len(current_chunk) + len(para) + 2 <= max_length:
                        current_chunk += para + "\n\n"
                    else:
                        # Send current chunk
                        if current_chunk:
                            await channel.send(current_chunk.strip())
                        current_chunk = para + "\n\n"
                
                # Send remaining chunk
                if current_chunk:
                    await channel.send(current_chunk.strip())
        
        except Exception as e:
            logger.error(f"❌ Error sending Discord response: {e}")
            await channel.send("Sorry, I encountered an error sending the response.")
    
    def _register_slash_commands(self):
        """Register slash commands with the bot."""
        tree = self.bot.tree
        
        # Helper to check admin permissions
        def is_admin(user: discord.User) -> bool:
            admin_ids = self.config.get('discord.admin.admin_user_ids', [])
            return user.id in admin_ids
        
        # ========================================================================
        # TIMER COMMANDS
        # ========================================================================
        
        timer_group = discord.app_commands.Group(name="timer", description="Manage timers")
        
        @timer_group.command(name="set", description="Set a timer")
        @discord.app_commands.describe(
            duration="Timer duration (e.g., '5 minutes', '30 seconds')",
            label="Optional label for the timer"
        )
        async def timer_set(interaction: discord.Interaction, duration: str, label: str = None):
            await interaction.response.defer()
            command = f"set a timer for {duration}"
            if label:
                command += f" called {label}"
            
            # Store Discord context
            self._current_discord_user = interaction.user.display_name
            
            # Ensure user has active conversation session
            await asyncio.to_thread(
                self._ensure_user_conversation,
                interaction.user.id,
                interaction.user.display_name
            )
            
            # Process command using async process_command
            response = await self.process_command(
                command=command,
                channel='discord',
                user_id=str(interaction.user.id),
                username=interaction.user.display_name
            )
            await interaction.followup.send(response.get('text', 'Timer command processed'))
        
        @timer_group.command(name="list", description="List all active timers")
        async def timer_list(interaction: discord.Interaction):
            await interaction.response.defer()
            
            # Store Discord context
            self._current_discord_user = interaction.user.display_name
            
            # Process command using async process_command
            response = await self.process_command(
                command="list timers",
                channel='discord',
                user_id=str(interaction.user.id),
                username=interaction.user.display_name
            )
            await interaction.followup.send(response.get('text', 'No active timers'))
        
        @timer_group.command(name="cancel", description="Cancel a specific timer")
        @discord.app_commands.describe(timer_id="Timer ID to cancel")
        async def timer_cancel(interaction: discord.Interaction, timer_id: int):
            await interaction.response.defer()
            
            # Store Discord context
            self._current_discord_user = interaction.user.display_name
            
            # Process command using async process_command
            response = await self.process_command(
                command=f"cancel timer {timer_id}",
                channel='discord',
                user_id=str(interaction.user.id),
                username=interaction.user.display_name
            )
            await interaction.followup.send(response.get('text', 'Timer cancel processed'))
        
        tree.add_command(timer_group)
        
        # ========================================================================
        # MUSIC COMMANDS
        # ========================================================================
        
        music_group = discord.app_commands.Group(name="music", description="Control music playback")
        
        @music_group.command(name="play", description="Play music")
        @discord.app_commands.describe(query="Music category or search query")
        async def music_play(interaction: discord.Interaction, query: str):
            await interaction.response.defer()
            
            # Store Discord context
            self._current_discord_user = interaction.user.display_name
            
            # Process command using async process_command
            response = await self.process_command(
                command=f"play {query} music",
                channel='discord',
                user_id=str(interaction.user.id),
                username=interaction.user.display_name
            )
            await interaction.followup.send(response.get('text', 'Music command processed'))
        
        @music_group.command(name="pause", description="Pause music playback")
        async def music_pause(interaction: discord.Interaction):
            await interaction.response.defer()
            
            # Store Discord context
            self._current_discord_user = interaction.user.display_name
            
            # Process command using async process_command
            response = await self.process_command(
                command="pause music",
                channel='discord',
                user_id=str(interaction.user.id),
                username=interaction.user.display_name
            )
            await interaction.followup.send(response.get('text', 'Music paused'))
        
        @music_group.command(name="stop", description="Stop music playback")
        async def music_stop(interaction: discord.Interaction):
            await interaction.response.defer()
            
            # Store Discord context
            self._current_discord_user = interaction.user.display_name
            
            # Process command using async process_command
            response = await self.process_command(
                command="stop music",
                channel='discord',
                user_id=str(interaction.user.id),
                username=interaction.user.display_name
            )
            await interaction.followup.send(response.get('text', 'Music stopped'))
        
        tree.add_command(music_group)
        
        # ========================================================================
        # MEMORY COMMANDS
        # ========================================================================
        
        memory_group = discord.app_commands.Group(name="memory", description="Manage conversation memory")
        
        @memory_group.command(name="search", description="Search conversation history")
        @discord.app_commands.describe(query="What to search for")
        async def memory_search(interaction: discord.Interaction, query: str):
            await interaction.response.defer()
            
            # Store Discord context
            self._current_discord_user = interaction.user.display_name
            
            # Process command using async process_command
            response = await self.process_command(
                command=f"search memory for {query}",
                channel='discord',
                user_id=str(interaction.user.id),
                username=interaction.user.display_name
            )
            await interaction.followup.send(response.get('text', 'Memory search completed'))
        
        @memory_group.command(name="summary", description="Get conversation summary")
        async def memory_summary(interaction: discord.Interaction):
            await interaction.response.defer()
            
            # Store Discord context
            self._current_discord_user = interaction.user.display_name
            
            # Process command using async process_command
            response = await self.process_command(
                command="summarize our conversation",
                channel='discord',
                user_id=str(interaction.user.id),
                username=interaction.user.display_name
            )
            await interaction.followup.send(response.get('text', 'Conversation summary generated'))
        
        tree.add_command(memory_group)
        
        # ========================================================================
        # ADMIN COMMANDS
        # ========================================================================
        
        if self.config.get('discord.admin.enabled', True):
            admin_group = discord.app_commands.Group(name="admin", description="Bot administration (admin only)")
            
            @admin_group.command(name="stats", description="Show bot statistics")
            async def admin_stats(interaction: discord.Interaction):
                """Get bot statistics (admin only)."""
                if not is_admin(interaction.user):
                    await interaction.response.send_message(
                        "❌ This command is restricted to bot administrators.",
                        ephemeral=True
                    )
                    return
                
                await interaction.response.defer(ephemeral=True)
                
                # Collect stats
                stats = {
                    "Latency": f"{self.bot.latency * 1000:.0f}ms",
                    "Guilds": len(self.bot.guilds),
                    "Users": len(self.bot.users),
                    "Uptime": "Ready",  # Could add actual uptime tracking
                }
                
                # Add timer stats if available
                if hasattr(self, 'timer_manager') and self.timer_manager:
                    stats["Active Timers"] = len(self.timer_manager.active_timers)
                
                # Add music stats if available
                if hasattr(self, 'music_manager') and self.music_manager:
                    stats["Music Playing"] = "Yes" if self.music_manager.is_playing() else "No"
                
                # Create embed
                if self.embeds:
                    embed = self.embeds.admin_stats(stats)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    response = "**📊 Bot Statistics**\n\n"
                    for key, value in stats.items():
                        response += f"• **{key}**: {value}\n"
                    await interaction.followup.send(response, ephemeral=True)
            
            @admin_group.command(name="servers", description="List all servers bot is in")
            async def admin_servers(interaction: discord.Interaction):
                """List all servers (admin only)."""
                if not is_admin(interaction.user):
                    await interaction.response.send_message(
                        "❌ This command is restricted to bot administrators.",
                        ephemeral=True
                    )
                    return
                
                await interaction.response.defer(ephemeral=True)
                
                response = f"**📋 Connected Servers ({len(self.bot.guilds)})**\n\n"
                for guild in self.bot.guilds:
                    response += f"• **{guild.name}** (ID: `{guild.id}`)\n"
                    response += f"  Members: {guild.member_count}\n\n"
                
                await interaction.followup.send(response, ephemeral=True)
            
            tree.add_command(admin_group)
            logger.info("✅ Admin commands registered")
        
        logger.info("✅ Slash commands registered")
    
    def run(self):
        """Start the Discord bot."""
        logger.info("🚀 Starting Bruno Discord bot...")
        try:
            self.bot.run(self.token)
        except discord.errors.LoginFailure:
            logger.error("❌ Invalid Discord token. Please check DISCORD_TOKEN environment variable.")
            raise
        except Exception as e:
            logger.error(f"❌ Bot error: {e}", exc_info=True)
            raise


def main():
    """Main entry point for running Discord bot standalone."""
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    # Load .env file if it exists
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"✅ Loaded environment variables from {env_path}")
    except ImportError:
        logger.debug("python-dotenv not installed, skipping .env file loading")
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get Discord token from environment or config
    token = os.getenv('DISCORD_TOKEN')
    
    # If not in environment, try loading from config
    if not token:
        try:
            config_temp = BrunoConfig()
            token = config_temp.get('discord.token')
        except:
            pass
    
    if not token:
        logger.error("❌ DISCORD_TOKEN environment variable not set")
        logger.error("Please set it with: export DISCORD_TOKEN='your_token_here'")
        sys.exit(1)
    
    try:
        # Load config
        config = BrunoConfig()
        
        # Check if Discord is enabled
        if not config.get('discord.enabled', False):
            logger.warning("⚠️  Discord integration is disabled in config.yaml")
            logger.warning("Set discord.enabled: true to enable")
            sys.exit(1)
        
        # Create and run Discord bot (inherits component initialization from BaseBrunoAssistant)
        logger.info("🔧 Initializing Discord bot...")
        bot = BrunoDiscordBot(token=token, config=config)
        
        bot.run()
    
    except KeyboardInterrupt:
        logger.info("\n👋 Discord bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
