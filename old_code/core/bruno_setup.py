"""
Shared setup functions for Bruno (voice and text interfaces)
Provides reusable initialization and shutdown logic
"""

import logging
from typing import Optional, Tuple, List, Dict, Any

from bruno.llm import LLMFactory
from bruno.utils.config import BrunoConfig
from bruno.abilities.timer_manager import TimerManager
from bruno.abilities.command_processor import CommandProcessor
from bruno.abilities.music_manager import MusicManager
from bruno.abilities.conversation_ability import ConversationAbility
from bruno.abilities.notes_manager import NotesManager
from bruno.memory import MemoryStore, ConversationManager, MemoryRetriever, ContextCompressor
from bruno.memory.background_jobs import BackgroundJobQueue, JobType
from bruno.core.bruno_interface import BrunoInterface
from bruno.core.action_executor import ActionExecutor

logger = logging.getLogger(__name__)


def setup_llm(config: BrunoConfig) -> Optional[object]:
    """
    Setup LLM client based on configured provider.
    
    Args:
        config: BrunoConfig instance
        
    Returns:
        LLM client instance or None if setup fails
    """
    try:
        provider = config.llm_provider
        logger.info(f"🧠 Setting up LLM client (provider: {provider})...")
        logger.info(f"📋 LLM Provider: {provider.upper()}")
        
        # Get provider-specific configuration
        llm_config = config.get_llm_config()
        
        # Create client using factory
        llm_client = LLMFactory.create(
            provider=provider,
            config=llm_config
        )
        
        logger.info(f"✅ LLM client ready ({provider})")
        logger.info(f"📝 LLM Model: {llm_config.get('model', 'default')}")
        return llm_client
        
    except ValueError as e:
        logger.error(f"❌ LLM configuration error: {e}")
        return None
    except ImportError as e:
        logger.error(f"❌ Missing LLM dependency: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to setup LLM: {e}")
        if config.llm_provider == 'ollama':
            logger.error("   Make sure Ollama is running: ollama serve")
        return None


def setup_memory_system(
    config: BrunoConfig,
    llm_client: Optional[object],
    db_path: Optional[str] = None,
    session_title: str = "Bruno Session"
) -> Tuple[Optional[MemoryStore], Optional[ConversationManager], Optional[MemoryRetriever], Optional[ContextCompressor], Optional[BackgroundJobQueue]]:
    """
    Setup memory system components.
    
    Args:
        config: BrunoConfig instance
        llm_client: LLM client for context compression
        db_path: Custom database path (None = use config default)
        session_title: Title for the conversation session
        
    Returns:
        Tuple of (memory_store, conversation_manager, memory_retriever, context_compressor, job_queue)
        Any component can be None if setup fails
    """
    try:
        logger.info("🧠 Setting up memory system...")
        
        # Get memory configuration
        memory_config = config.get('bruno.memory', {})
        
        if not memory_config.get('enabled', True):
            logger.info("ℹ️  Memory system disabled in config")
            return None, None, None, None, None
        
        # Initialize memory store
        if db_path is None:
            db_path = memory_config.get('database_path', 'bruno_memory.db')
        memory_store = MemoryStore(db_path)
        
        # Initialize background job queue
        job_queue = BackgroundJobQueue(num_workers=2, max_queue_size=100)
        
        # Initialize context compressor first (required by ConversationManager for auto-compression)
        context_compressor = None
        if llm_client:
            context_compressor = ContextCompressor(
                memory_store=memory_store,
                llm_client=llm_client,
                compression_threshold=memory_config.get('compression_threshold', 50)
            )
            
            # Register compression handler with job queue
            def compression_handler(conversation_id: int, context_compressor: ContextCompressor):
                """Handler for background compression jobs."""
                try:
                    logger.info(f"⚙️  Background compression started for conversation {conversation_id}")
                    results = context_compressor.auto_compress_and_promote(
                        conversation_id=conversation_id
                    )
                    logger.info(
                        f"✅ Background compression complete: "
                        f"compressed={results.get('compressed')}, "
                        f"promoted={results.get('promoted_count')} STM→LTM"
                    )
                    return results
                except Exception as e:
                    logger.error(f"❌ Background compression failed: {e}", exc_info=True)
                    return None
            
            job_queue.register_handler(JobType.COMPRESS_CONVERSATION, compression_handler)
            
            # Register immediate fact extraction handler
            def fact_extraction_handler(messages: List[Dict[str, Any]], conversation_id: int, context_compressor: ContextCompressor):
                """Handler for immediate fact extraction from message pairs."""
                try:
                    logger.debug(f"⚙️  Extracting facts from message pair (conversation {conversation_id})")
                    facts = context_compressor.extract_facts(messages)
                    
                    # Add facts as STM entries
                    added_count = 0
                    for fact_data in facts:
                        # Get source message ID if available
                        source_message_id = None
                        if messages and len(messages) > 0:
                            source_message_id = messages[-1].get('id')  # Last message in pair
                        
                        stm_id = context_compressor.memory_store.add_short_term_memory(
                            fact=fact_data['fact'],
                            category=fact_data.get('category', 'general'),
                            confidence=fact_data.get('importance', 0.7),
                            source_message_id=source_message_id
                        )
                        if stm_id:
                            added_count += 1
                    
                    if added_count > 0:
                        logger.debug(f"✅ Added {added_count} STM entries from message pair")
                    return {'added': added_count, 'facts': facts}
                except Exception as e:
                    logger.error(f"❌ Immediate fact extraction failed: {e}", exc_info=True)
                    return None
            
            job_queue.register_handler(JobType.EXTRACT_FACTS, fact_extraction_handler)
            job_queue.start()
            logger.info("✅ Background job queue started with immediate fact extraction")
        else:
            logger.warning("⚠️  Context compressor not available (no LLM)")
            job_queue = None
        
        # Initialize conversation manager (with context_compressor and job_queue for async compression)
        conversation_manager = ConversationManager(
            memory_store=memory_store,
            max_messages=memory_config.get('conversation_window', 20),
            compression_threshold=memory_config.get('compression_threshold', 50),
            auto_save=memory_config.get('auto_save', True),
            context_compressor=context_compressor,
            job_queue=job_queue
        )
        
        # Initialize memory retriever with caching enabled
        memory_retriever = MemoryRetriever(
            memory_store=memory_store,
            recency_weight=0.3,
            access_weight=0.2,
            keyword_weight=0.5,
            enable_cache=True,  # Enable caching
            cache_size=100,
            cache_ttl=300  # 5 minutes
        )
        
        # Initialize and start LTM worker for automatic STM→LTM promotion
        ltm_worker = None
        if context_compressor and memory_retriever and job_queue:
            from bruno.memory.ltm_worker import LTMWorker, LTMWorkerConfig
            
            # Get LTM worker config from memory config
            ltm_config = memory_config.get('ltm_worker', {})
            ltm_worker_config = LTMWorkerConfig(
                check_interval_seconds=ltm_config.get('check_interval_seconds', 300),  # 5 minutes
                min_access_count=ltm_config.get('min_access_count', 3),
                min_relevance=ltm_config.get('min_relevance', 0.8),
                min_age_days=ltm_config.get('min_age_days', 3.0),
                batch_size=ltm_config.get('batch_size', 10),
                consolidate_memories=ltm_config.get('consolidate_memories', True),
                enable_auto_promotion=ltm_config.get('enable_auto_promotion', True)
            )
            
            ltm_worker = LTMWorker(
                memory_retriever=memory_retriever,
                context_compressor=context_compressor,
                job_queue=job_queue,
                config=ltm_worker_config
            )
            ltm_worker.start()
            logger.info("✅ LTM worker started for automatic STM→LTM promotion")
        else:
            logger.warning("⚠️  LTM worker not available (missing dependencies)")
        
        # Start a new conversation session
        conv_id, session_id = conversation_manager.start_conversation(
            title=session_title
        )
        logger.info(f"✅ Memory system ready (conversation: {conv_id})")
        return memory_store, conversation_manager, memory_retriever, context_compressor, job_queue
        
    except Exception as e:
        logger.error(f"❌ Failed to setup memory system: {e}")
        logger.warning("⚠️  Bruno will continue without memory system")
        return None, None, None, None, None


def setup_timer_manager(config: BrunoConfig, tts_engine: Optional[object] = None) -> Optional[TimerManager]:
    """
    Setup timer manager.
    
    Args:
        config: BrunoConfig instance
        tts_engine: TTS engine for announcements (None = text-only timers)
        
    Returns:
        TimerManager instance or None if setup fails
    """
    try:
        logger.info("⏱️  Setting up timer manager...")
        timer_manager = TimerManager(tts_engine, config)
        logger.info("✅ Timer manager ready")
        return timer_manager
    except Exception as e:
        logger.error(f"❌ Failed to setup timer manager: {e}")
        return None


def setup_alarm_manager(config: BrunoConfig, tts_engine: Optional[object] = None) -> Optional[object]:
    """
    Setup alarm manager.
    
    Args:
        config: BrunoConfig instance
        tts_engine: TTS engine for announcements (None = text-only alarms)
        
    Returns:
        AlarmManager instance or None if setup fails
    """
    try:
        logger.info("⏰ Setting up alarm manager...")
        from bruno.abilities.alarm_manager import AlarmManager
        alarm_manager = AlarmManager(tts_engine, config)
        logger.info("✅ Alarm manager ready")
        return alarm_manager
    except Exception as e:
        logger.error(f"❌ Failed to setup alarm manager: {e}")
        return None


def setup_command_processor(llm_client: Optional[object]) -> Optional[CommandProcessor]:
    """
    Setup command processor.
    
    Args:
        llm_client: LLM client for command parsing
        
    Returns:
        CommandProcessor instance or None if no LLM available
    """
    if not llm_client:
        logger.warning("⚠️  Command processor not available (no LLM)")
        return None
    
    try:
        logger.info("🧠 Setting up command processor...")
        command_processor = CommandProcessor(llm_client)
        logger.info("✅ Command processor ready")
        return command_processor
    except Exception as e:
        logger.error(f"❌ Failed to setup command processor: {e}")
        return None


def setup_conversation_ability(
    memory_store: Optional[MemoryStore],
    conversation_manager: Optional[ConversationManager]
) -> Optional[ConversationAbility]:
    """
    Setup conversation ability.
    
    Args:
        memory_store: MemoryStore instance
        conversation_manager: ConversationManager instance
        
    Returns:
        ConversationAbility instance or None if memory system not available
    """
    if not memory_store or not conversation_manager:
        logger.warning("⚠️  Conversation ability not available (no memory system)")
        return None
    
    try:
        logger.info("💬 Setting up conversation ability...")
        conversation_ability = ConversationAbility(memory_store, conversation_manager)
        logger.info("✅ Conversation ability ready")
        return conversation_ability
    except Exception as e:
        logger.error(f"❌ Failed to setup conversation ability: {e}")
        return None


def setup_music_manager(config: BrunoConfig) -> Optional[MusicManager]:
    """
    Setup music manager.
    
    Args:
        config: BrunoConfig instance
        
    Returns:
        MusicManager instance or None if setup fails
    """
    try:
        logger.info("🎵 Setting up music manager...")
        music_manager = MusicManager(config)
        logger.info("✅ Music manager ready")
        return music_manager
    except Exception as e:
        logger.warning(f"⚠️  Music manager not available: {e}")
        return None


def setup_notes_manager(config: BrunoConfig, db_path: Optional[str] = None) -> Optional[NotesManager]:
    """
    Setup notes manager.
    
    Args:
        config: BrunoConfig instance
        db_path: Custom database path (None = use config default)
        
    Returns:
        NotesManager instance or None if setup fails
    """
    try:
        logger.info("📝 Setting up notes manager...")
        
        # Get notes database path from config
        if db_path is None:
            db_path = config.get('bruno.notes.database_path', 'bruno_notes.db')
        
        notes_manager = NotesManager(db_path)
        logger.info("✅ Notes manager ready")
        return notes_manager
    except Exception as e:
        logger.error(f"❌ Failed to setup notes manager: {e}")
        return None


def setup_bruno_interface(
    config: BrunoConfig,
    llm_client: Optional[object],
    command_processor: Optional[CommandProcessor],
    timer_manager: Optional[TimerManager],
    music_manager: Optional[MusicManager],
    conversation_manager: Optional[ConversationManager],
    conversation_ability: Optional[ConversationAbility],
    memory_store: Optional[MemoryStore],
    memory_retriever: Optional[MemoryRetriever],
    notes_manager: Optional[NotesManager] = None,
    alarm_manager: Optional[object] = None,
    tts_engine: Optional[object] = None
) -> Optional[BrunoInterface]:
    """
    Setup Bruno interface (unified for voice and text).
    
    Args:
        config: BrunoConfig instance
        llm_client: LLM client
        command_processor: CommandProcessor instance
        timer_manager: TimerManager instance
        music_manager: MusicManager instance
        conversation_manager: ConversationManager instance
        conversation_ability: ConversationAbility instance
        memory_store: MemoryStore instance
        memory_retriever: MemoryRetriever instance
        notes_manager: NotesManager instance (optional)
        alarm_manager: AlarmManager instance (optional)
        tts_engine: TTS engine (None for text mode)
        
    Returns:
        BrunoInterface instance or None if setup fails
    """
    try:
        logger.info("🔗 Setting up core interface...")
        bruno_interface = BrunoInterface(
            config=config,
            llm_client=llm_client,
            command_processor=command_processor,
            timer_manager=timer_manager,
            music_manager=music_manager,
            conversation_manager=conversation_manager,
            conversation_ability=conversation_ability,
            memory_store=memory_store,
            memory_retriever=memory_retriever,
            tts_engine=tts_engine,
            notes_manager=notes_manager,
            alarm_manager=alarm_manager
        )
        logger.info("✅ Core interface ready")
        return bruno_interface
    except Exception as e:
        logger.error(f"❌ Failed to setup core interface: {e}")
        return None


def setup_action_executor(
    timer_manager: Optional[TimerManager],
    music_manager: Optional[MusicManager],
    tts_engine: Optional[object] = None,
    alarm_manager: Optional[object] = None
) -> Optional[ActionExecutor]:
    """
    Setup action executor.
    
    Args:
        timer_manager: TimerManager instance
        music_manager: MusicManager instance
        tts_engine: TTS engine (None for text mode)
        alarm_manager: AlarmManager instance (None if not available)
        
    Returns:
        ActionExecutor instance or None if setup fails
    """
    try:
        action_executor = ActionExecutor(
            timer_manager=timer_manager,
            music_manager=music_manager,
            tts_engine=tts_engine,
            alarm_manager=alarm_manager
        )
        logger.info("✅ Action executor ready")
        return action_executor
    except Exception as e:
        logger.error(f"❌ Failed to setup action executor: {e}")
        return None


def shutdown_memory_system(
    config: BrunoConfig,
    memory_store: Optional[MemoryStore],
    conversation_manager: Optional[ConversationManager],
    context_compressor: Optional[ContextCompressor],
    job_queue: Optional[BackgroundJobQueue] = None
) -> None:
    """
    Gracefully shutdown memory system.
    
    Args:
        config: BrunoConfig instance
        memory_store: MemoryStore instance
        conversation_manager: ConversationManager instance
        context_compressor: ContextCompressor instance
        job_queue: BackgroundJobQueue instance
    """
    # Stop background job queue first
    if job_queue:
        try:
            logger.info("🛑 Stopping background job queue...")
            job_queue.stop(timeout=5.0)
        except Exception as e:
            logger.error(f"⚠️  Error stopping job queue: {e}")
    
    # Extract profile from conversation before ending
    if (conversation_manager and 
        context_compressor and
        config.get('bruno.memory.auto_extract_profile', True)):
        try:
            profile = memory_store.get_user_profile()
            conv_count = profile.get('conversation_count', 0)
            update_freq = config.get('bruno.memory.profile_update_frequency', 5)
            
            # Extract profile every N conversations
            if conv_count % update_freq == 0:
                logger.info(f"🔍 Extracting profile (every {update_freq} conversations)...")
                conversation_manager.update_profile_from_conversation(
                    context_compressor
                )
            
            # Increment conversation count
            memory_store.increment_conversation_count()
        except Exception as e:
            logger.error(f"⚠️  Error extracting profile: {e}")
    
    # End conversation session
    if conversation_manager:
        try:
            conversation_manager.end_conversation(
                summary="Session ended by user"
            )
        except Exception as e:
            logger.error(f"⚠️  Error ending conversation: {e}")
    
    # Close memory store
    if memory_store:
        try:
            memory_store.close()
        except Exception as e:
            logger.error(f"⚠️  Error closing memory store: {e}")


def shutdown_abilities(
    timer_manager: Optional[TimerManager],
    music_manager: Optional[MusicManager]
) -> None:
    """
    Gracefully shutdown ability managers.
    
    Args:
        timer_manager: TimerManager instance
        music_manager: MusicManager instance
    """
    # Shutdown timer manager
    if timer_manager:
        try:
            logger.info("⏱️  Shutting down timer manager...")
            timer_manager.shutdown()
        except Exception as e:
            logger.error(f"⚠️  Error shutting down timer manager: {e}")
    
    # Shutdown music manager
    if music_manager:
        try:
            logger.info("🎵 Shutting down music manager...")
            music_manager.shutdown()
        except Exception as e:
            logger.error(f"⚠️  Error shutting down music manager: {e}")
