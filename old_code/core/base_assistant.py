"""
Base Bruno Assistant - Abstract base class for all Bruno interfaces
Provides common functionality for voice, text, and future interfaces
"""

import asyncio
import logging
import signal
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from bruno.utils.config import BrunoConfig
from bruno.core.bruno_setup import (
    setup_llm,
    setup_memory_system,
    setup_timer_manager,
    setup_alarm_manager,
    setup_command_processor,
    setup_conversation_ability,
    setup_music_manager,
    setup_notes_manager,
    setup_bruno_interface,
    setup_action_executor,
    shutdown_memory_system,
    shutdown_abilities
)

logger = logging.getLogger(__name__)


class BaseBrunoAssistant(ABC):
    """
    Abstract base class for all Bruno interfaces (Single Responsibility + Template Method pattern).
    
    Provides:
    - Common initialization
    - Shared command processing logic
    - Conversation mode management
    - Graceful shutdown
    
    Subclasses must implement:
    - _setup_input_method() - How to capture user input (voice/text/etc)
    - _setup_output_method() - How to respond to user (TTS/print/etc)
    - _get_user_input() - Get command from user
    - _send_output() - Send response to user
    """
    
    def __init__(self, config: BrunoConfig = None):
        """
        Initialize base Bruno assistant.
        
        Args:
            config: BrunoConfig instance (None = load from config.yaml)
        """
        self.running = False
        self.config = config or BrunoConfig()
        
        # Core components (shared across all interfaces)
        self.llm_client = None
        self.timer_manager = None
        self.command_processor = None
        self.music_manager = None
        self.notes_manager = None
        self.conversation_ability = None
        self.bruno_interface = None
        self.action_executor = None
        
        # Memory system components
        self.memory_store = None
        self.conversation_manager = None
        self.memory_retriever = None
        self.context_compressor = None
        self.job_queue = None  # Background job queue for async operations
        
        # Conversation mode state
        self.in_conversation_mode = False
        self.conversation_exchange_count = 0
        
        # Signal handling
        self._shutdown_requested = False
        self._stop_called = False
        
        logger.info(f"🤖 Initializing {self.__class__.__name__}...")
    
    # ============================================
    # Template Method Pattern - Common Flow
    # ============================================
    
    async def start(self) -> bool:
        """
        Start Bruno assistant (Template Method) - ASYNC.
        
        Returns:
            True if started successfully, False otherwise
        """
        logger.info("\n" + "="*60)
        logger.info(f"🚀 Starting {self.__class__.__name__}...")
        logger.info("="*60 + "\n")
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Setup input method (voice/text/etc) - implemented by subclass
        if not await self._setup_input_method():
            return False
        
        # Setup output method (TTS/print/etc) - implemented by subclass
        if not await self._setup_output_method():
            return False
        
        # Setup common components
        if not await self._setup_common_components():
            return False
        
        # Start main loop - implemented by subclass
        self.running = True
        return await self._run_main_loop()
    
    def stop(self):
        """Stop Bruno assistant gracefully."""
        if not self.running and self._stop_called:
            return
        
        self._stop_called = True
        self.running = False
        logger.info("🛑 Initiating shutdown sequence...")
        
        # Shutdown memory system
        shutdown_memory_system(
            self.config,
            self.memory_store,
            self.conversation_manager,
            self.context_compressor,
            self.job_queue
        )
        
        # Shutdown abilities
        shutdown_abilities(self.timer_manager, self.music_manager)
        
        # Additional cleanup - implemented by subclass
        self._cleanup_resources()
        
        logger.info(f"👋 {self.__class__.__name__} stopped. Goodbye!")
    
    # ============================================
    # Common Setup Methods (Shared Logic)
    # ============================================
    
    async def _setup_common_components(self) -> bool:
        """
        Setup components common to all interfaces - ASYNC.
        
        Returns:
            True if setup successful, False otherwise
        """
        # Setup LLM
        self.llm_client = setup_llm(self.config)
        if not self.llm_client:
            logger.error("❌ LLM not available, cannot continue")
            return False
        
        # Setup memory system (optional) - with interface-specific DB path
        db_path = self._get_memory_db_path()
        session_title = self._get_session_title()
        self.memory_store, self.conversation_manager, self.memory_retriever, self.context_compressor, self.job_queue = \
            setup_memory_system(self.config, self.llm_client, db_path=db_path, session_title=session_title)
        
        # Setup timer manager
        tts_engine = self._get_tts_engine()
        self.timer_manager = setup_timer_manager(self.config, tts_engine=tts_engine)
        
        # Setup alarm manager
        self.alarm_manager = setup_alarm_manager(self.config, tts_engine=tts_engine)
        
        # Setup command processor
        self.command_processor = setup_command_processor(self.llm_client)
        
        # Setup conversation ability
        self.conversation_ability = setup_conversation_ability(self.memory_store, self.conversation_manager)
        
        # Setup music manager
        self.music_manager = setup_music_manager(self.config)
        
        # Setup notes manager
        self.notes_manager = setup_notes_manager(self.config)
        
        # Setup core interface
        self.bruno_interface = setup_bruno_interface(
            config=self.config,
            llm_client=self.llm_client,
            command_processor=self.command_processor,
            timer_manager=self.timer_manager,
            music_manager=self.music_manager,
            conversation_manager=self.conversation_manager,
            conversation_ability=self.conversation_ability,
            memory_store=self.memory_store,
            memory_retriever=self.memory_retriever,
            notes_manager=self.notes_manager,
            alarm_manager=self.alarm_manager,
            tts_engine=tts_engine
        )
        
        # Setup action executor
        self.action_executor = setup_action_executor(
            timer_manager=self.timer_manager,
            music_manager=self.music_manager,
            tts_engine=tts_engine,
            alarm_manager=self.alarm_manager
        )
        
        return True
    
    # ============================================
    # Common Command Processing (Shared Logic)
    # ============================================
    
    async def process_command(
        self,
        command: str,
        channel: str = 'generic',
        user_id: str = None,
        username: str = None
    ) -> Dict[str, Any]:
        """
        Process a command through unified interface (SHARED LOGIC) - ASYNC.
        
        Args:
            command: The command text
            channel: Channel identifier (voice/text/discord)
            user_id: User ID (for Discord, multi-user tracking)
            username: Username (for personalization)
            
        Returns:
            Response dictionary with success, text, actions
        """
        if not command or not command.strip():
            return {'success': False, 'text': '', 'error': 'Empty command'}
        
        logger.info(f"📝 Command: '{command}'")
        
        # Create request
        request = {
            'user_id': user_id or f'{channel}:local',
            'channel': channel,
            'text': command
        }
        
        # Add username if provided
        if username:
            request['username'] = username
        
        # Process through unified interface (run in thread pool for blocking I/O)
        response = await asyncio.to_thread(self.bruno_interface.handle_message, request)
        
        if response['success']:
            # Execute actions (run in thread pool for blocking I/O)
            if response.get('actions'):
                enable_tts = self._should_enable_tts()
                await asyncio.to_thread(
                    self.action_executor.execute,
                    response['actions'],
                    enable_tts=enable_tts,
                    enable_timers=True,
                    enable_music=True
                )
                
                # Check if music was played and update response text with track info
                for action in response['actions']:
                    if action.get('type') == 'music_play' and action.get('_result'):
                        result = action['_result']
                        if result.get('success') and result.get('track_name'):
                            track_name = result['track_name']
                            track_count = result.get('track_count', 1)
                            if track_count > 1:
                                response['text'] = f"🎵 Now playing: **{track_name}** ({track_count} songs in queue)"
                            else:
                                response['text'] = f"🎵 Now playing: **{track_name}**"
                        break
                    elif action.get('type') in ['music_next', 'music_skip'] and action.get('_result'):
                        result = action['_result']
                        if result.get('success') and result.get('track_name'):
                            track_name = result['track_name']
                            response['text'] = f"⏭️ Now playing: **{track_name}**"
                        break
                    elif action.get('type') == 'music_pause' and action.get('_result'):
                        result = action['_result']
                        if result.get('success') and result.get('track_name'):
                            track_name = result['track_name']
                            response['text'] = f"⏸️ Paused: **{track_name}**"
                        break
                    elif action.get('type') == 'music_resume' and action.get('_result'):
                        result = action['_result']
                        if result.get('success') and result.get('track_name'):
                            track_name = result['track_name']
                            response['text'] = f"▶️ Resumed: **{track_name}**"
                        break
                    elif action.get('type') == 'music_stop' and action.get('_result'):
                        result = action['_result']
                        if result.get('success') and result.get('track_name'):
                            track_name = result['track_name']
                            response['text'] = f"⏹️ Stopped: **{track_name}**"
                        break
            
            logger.info(f"💬 Response: '{response['text']}'")
        else:
            error_msg = response.get('error', 'Unknown error')
            logger.error(f"❌ Error: {error_msg}")
        
        return response
    
    # ============================================
    # Common Conversation Mode (Shared Logic)
    # ============================================
    
    def should_enter_conversation_mode(self, command: Optional[str]) -> bool:
        """
        Check if should enter conversation mode (SHARED LOGIC).
        
        Args:
            command: The command text
            
        Returns:
            True if should enter conversation mode
        """
        if not self.config.get('bruno.conversation_mode.enabled', True):
            return False
        
        if not command:
            return False
        
        # Check for exit keywords
        exit_keywords = self.config.get('bruno.conversation_mode.exit_keywords', [])
        should_exit = any(kw.lower() in command.lower() for kw in exit_keywords)
        
        return not should_exit
    
    def update_conversation_state(self, command: Optional[str]) -> str:
        """
        Update conversation mode state (SHARED LOGIC).
        
        Args:
            command: The command that was processed
            
        Returns:
            'exit' if should exit conversation, 'continue' if should continue, 'inactive' if not in conversation
        """
        if not self.should_enter_conversation_mode(command):
            # User said goodbye or conversation disabled
            self.in_conversation_mode = False
            self.conversation_exchange_count = 0
            return 'exit'
        
        # Enter/continue conversation mode
        if not self.in_conversation_mode:
            self.in_conversation_mode = True
            self.conversation_exchange_count = 0
        
        self.conversation_exchange_count += 1
        
        # Check if max exchanges reached
        max_exchanges = self.config.get('bruno.conversation_mode.max_continuous_exchanges', 10)
        if self.conversation_exchange_count >= max_exchanges:
            logger.info(f"ℹ️  Max exchanges ({max_exchanges}) reached")
            self.in_conversation_mode = False
            self.conversation_exchange_count = 0
            return 'max_reached'
        
        return 'continue'
    
    def end_conversation_mode(self):
        """End conversation mode (SHARED LOGIC)."""
        self.in_conversation_mode = False
        self.conversation_exchange_count = 0
        logger.info("⏸️  Conversation mode ended")
    
    # ============================================
    # Utility Methods (Shared Logic)
    # ============================================
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals (SIGINT, SIGTERM)."""
        if not self._shutdown_requested:
            self._shutdown_requested = True
            logger.info("\n\n⏹️  Shutdown signal received...")
            self.running = False
    
    def _handle_exit_keywords(self, command: str) -> bool:
        """
        Check if command contains exit keywords.
        
        Args:
            command: The command text
            
        Returns:
            True if should exit
        """
        exit_keywords = self.config.get('bruno.conversation_mode.exit_keywords', [])
        exit_keywords.extend(['exit', 'quit'])  # Always include these
        return any(kw.lower() in command.lower() for kw in exit_keywords)
    
    # ============================================
    # Abstract Methods (Must Implement in Subclass)
    # ============================================
    
    @abstractmethod
    async def _setup_input_method(self) -> bool:
        """
        Setup input method (voice/text/etc) - ASYNC.
        
        Returns:
            True if setup successful
        """
        pass
    
    @abstractmethod
    async def _setup_output_method(self) -> bool:
        """
        Setup output method (TTS/print/etc) - ASYNC.
        
        Returns:
            True if setup successful
        """
        pass
    
    @abstractmethod
    async def _get_user_input(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Get input from user - ASYNC.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            User input text or None
        """
        pass
    
    @abstractmethod
    async def _send_output(self, text: str, prefix: str = "🤖") -> None:
        """
        Send output to user - ASYNC.
        
        Args:
            text: Text to output
            prefix: Optional prefix/emoji
        """
        pass
    
    @abstractmethod
    async def _run_main_loop(self) -> bool:
        """
        Run the main interaction loop - ASYNC.
        
        Returns:
            True if ran successfully
        """
        pass
    
    @abstractmethod
    def _cleanup_resources(self) -> None:
        """Cleanup interface-specific resources."""
        pass
    
    # ============================================
    # Hook Methods (Optional Override)
    # ============================================
    
    def _get_memory_db_path(self) -> Optional[str]:
        """
        Get database path for this interface.
        
        Returns:
            Database path or None for default
        """
        return None  # Use default from config
    
    def _get_session_title(self) -> str:
        """
        Get session title for this interface.
        
        Returns:
            Session title
        """
        return "Bruno Session"
    
    def _get_tts_engine(self) -> Optional[Any]:
        """
        Get TTS engine for this interface.
        
        Returns:
            TTS engine or None
        """
        return None  # Override in voice interface
    
    def _should_enable_tts(self) -> bool:
        """
        Check if TTS should be enabled for actions.
        
        Returns:
            True if TTS should be enabled
        """
        return False  # Override in voice interface
