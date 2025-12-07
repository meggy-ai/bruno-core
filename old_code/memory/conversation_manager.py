"""
ConversationManager - Manages conversation sessions and context building.

This module handles:
- Session lifecycle (start, end, resume)
- Message buffering with rolling window
- Context building for LLM queries
- Memory storage coordination
- Compression triggering
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from bruno.memory.memory_store import MemoryStore
from bruno.memory.background_jobs import BackgroundJobQueue, BackgroundJob, JobType

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation sessions and builds context for LLM interactions.
    
    Features:
    - Rolling message window (configurable size)
    - Automatic memory storage
    - Context compression triggering
    - Session management
    - Conversation history tracking
    """
    
    def __init__(
        self,
        memory_store: MemoryStore,
        max_messages: int = 20,
        compression_threshold: int = 50,
        stm_threshold: float = 0.7,
        auto_save: bool = True,
        context_compressor = None,
        job_queue: Optional[BackgroundJobQueue] = None
    ):
        """
        Initialize ConversationManager.
        
        Args:
            memory_store: MemoryStore instance for persistence
            max_messages: Maximum messages in rolling window (default: 20)
            compression_threshold: Message count to trigger compression (default: 50)
            stm_threshold: Relevance threshold for STM storage (default: 0.7)
            auto_save: Automatically save messages to database (default: True)
            context_compressor: ContextCompressor instance for auto-compression (optional)
            job_queue: BackgroundJobQueue for async operations (optional)
        """
        self.memory_store = memory_store
        self.max_messages = max_messages
        self.compression_threshold = compression_threshold
        self.stm_threshold = stm_threshold
        self.auto_save = auto_save
        self.context_compressor = context_compressor
        self.job_queue = job_queue
        
        # Current session state
        self.current_conversation_id: Optional[int] = None
        self.current_session_id: Optional[str] = None
        self.message_buffer: List[Dict[str, Any]] = []
        self.message_count: int = 0
        
        # Profile onboarding state
        self.name_prompt_pending = False
        self.profile_extraction_pending = False
        
        # Track user activity for compression deferral
        self.last_user_message_time = 0
        self.compression_defer_seconds = 30  # Defer compression if user active within 30s
        
        logger.info(
            f"✅ ConversationManager initialized "
            f"(window: {max_messages}, compression: {compression_threshold})"
        )
    
    def start_conversation(
        self,
        title: str = "New Conversation",
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[int, str]:
        """
        Start a new conversation session.
        
        Args:
            title: Conversation title (default: "New Conversation")
            context: Optional context metadata
            
        Returns:
            Tuple of (conversation_id, session_id)
        """
        # End any active conversation
        if self.current_conversation_id:
            self.end_conversation()
        
        # Generate session_id
        import uuid
        session_id = str(uuid.uuid4())
        
        # Create new conversation
        conv_id = self.memory_store.create_conversation(session_id)
        
        # Update with title and context if provided
        updates = {}
        if title:
            updates['title'] = title
        if context:
            updates['context'] = context
        
        if updates:
            self.memory_store.update_conversation(session_id, **updates)
        
        self.current_conversation_id = conv_id
        self.current_session_id = session_id
        self.message_buffer.clear()
        self.message_count = 0
        
        logger.info(
            f"🆕 Started conversation {conv_id} "
            f"(session: {self.current_session_id})"
        )
        
        return conv_id, self.current_session_id
    
    def resume_conversation(self, conversation_id: int) -> bool:
        """
        Resume an existing conversation.
        
        Args:
            conversation_id: ID of conversation to resume
            
        Returns:
            True if resumed successfully, False otherwise
        """
        conv = self.memory_store.get_conversation_by_id(conversation_id)
        if not conv:
            logger.warning(f"❌ Conversation {conversation_id} not found")
            return False
        
        # End current conversation if active
        if self.current_conversation_id:
            self.end_conversation()
        
        self.current_conversation_id = conversation_id
        self.current_session_id = conv['session_id']
        
        # Load recent messages into buffer
        messages = self.memory_store.get_recent_messages(
            conversation_id,
            count=self.max_messages
        )
        self.message_buffer = messages
        self.message_count = self.memory_store.get_message_count(conversation_id)
        
        logger.info(
            f"🔄 Resumed conversation {conversation_id} "
            f"({len(messages)} messages in buffer, {self.message_count} total)"
        )
        
        return True
    
    def end_conversation(self, summary: Optional[str] = None) -> None:
        """
        End the current conversation session.
        
        Args:
            summary: Optional conversation summary
        """
        if not self.current_conversation_id:
            logger.warning("⚠️  No active conversation to end")
            return
        
        # Update conversation with summary
        if summary:
            self.memory_store.update_conversation(
                self.current_session_id,
                compressed_summary=summary
            )
        
        # Mark as ended
        self.memory_store.end_conversation(self.current_session_id)
        
        logger.info(
            f"🏁 Ended conversation {self.current_conversation_id} "
            f"({self.message_count} messages)"
        )
        
        # Clear state
        self.current_conversation_id = None
        self.current_session_id = None
        self.message_buffer.clear()
        self.message_count = 0
    
    def add_message(
        self,
        role: str,
        content: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Add a message to the current conversation.
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            intent: Optional intent classification
            entities: Optional extracted entities
            
        Returns:
            Message ID if saved, None otherwise
        """
        if not self.current_conversation_id:
            logger.warning("⚠️  No active conversation - starting new one")
            self.start_conversation()
        
        # Create message object
        message = {
            'conversation_id': self.current_conversation_id,
            'role': role,
            'content': content,
            'intent': intent,
            'entities': entities,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add to buffer
        self.message_buffer.append(message)
        self.message_count += 1
        
        # Track user activity
        if role == 'user':
            import time
            self.last_user_message_time = time.time()
        
        # Maintain rolling window
        if len(self.message_buffer) > self.max_messages:
            self.message_buffer.pop(0)
        
        # Save to database if auto-save enabled
        message_id = None
        if self.auto_save:
            message_id = self.memory_store.add_message(
                conversation_id=self.current_conversation_id,
                role=role,
                content=content,
                intent=intent,
                entities=entities
            )
            message['id'] = message_id
        
        # IMMEDIATE FACT EXTRACTION: Create STM entries from recent exchange
        # This happens EVERY message instead of waiting for compression threshold
        if role == 'assistant' and self.context_compressor and len(self.message_buffer) >= 2:
            # Get last user-assistant pair for fact extraction
            last_two = self.message_buffer[-2:]
            if len(last_two) == 2 and last_two[0]['role'] == 'user' and last_two[1]['role'] == 'assistant':
                # Submit immediate fact extraction in background
                if self.job_queue:
                    job = BackgroundJob(
                        job_type=JobType.EXTRACT_FACTS,
                        params={
                            'messages': last_two,
                            'conversation_id': self.current_conversation_id,
                            'context_compressor': self.context_compressor
                        },
                        priority=2  # High priority (immediate context building)
                    )
                    self.job_queue.submit(job)
                    logger.debug(f"📤 Immediate fact extraction queued for message pair")
        
        # Check if compression needed (full auto-compress to consolidate and promote)
        if self.message_count >= self.compression_threshold:
            # Defer compression if user is actively chatting (avoid LLM saturation)
            import time
            time_since_last_message = time.time() - self.last_user_message_time
            
            if time_since_last_message < self.compression_defer_seconds:
                logger.info(
                    f"⏸️  Compression deferred (user active {time_since_last_message:.0f}s ago, threshold: {self.compression_defer_seconds}s)"
                )
                # Will retry on next message
                return message_id
            
            logger.info(
                f"🗜️  Compression threshold reached "
                f"({self.message_count}/{self.compression_threshold})"
            )
            # Trigger automatic compression in BACKGROUND (non-blocking)
            if self.context_compressor:
                if self.job_queue:
                    # Submit to background job queue (async, non-blocking)
                    job = BackgroundJob(
                        job_type=JobType.COMPRESS_CONVERSATION,
                        params={
                            'conversation_id': self.current_conversation_id,
                            'context_compressor': self.context_compressor
                        },
                        priority=3  # Medium priority
                    )
                    self.job_queue.submit(job)
                    logger.info(f"📤 Compression job queued for conversation {self.current_conversation_id}")
                else:
                    # Fallback: run synchronously if no job queue (legacy behavior)
                    try:
                        logger.info(f"🔄 Triggering auto-compression for conversation {self.current_conversation_id}...")
                        results = self.context_compressor.auto_compress_and_promote(
                            conversation_id=self.current_conversation_id
                        )
                        logger.info(
                            f"✅ Auto-compression complete: "
                            f"compressed={results.get('compressed')}, "
                            f"promoted={results.get('promoted_count')} STM→LTM"
                        )
                    except Exception as e:
                        logger.error(f"❌ Auto-compression failed: {e}", exc_info=True)
            else:
                logger.debug("ℹ️  ContextCompressor not available for auto-compression")
        
        logger.debug(
            f"💬 Added {role} message "
            f"(buffer: {len(self.message_buffer)}/{self.max_messages}, "
            f"total: {self.message_count})"
        )
        
        return message_id
    
    def get_conversation_context(
        self,
        include_stm: bool = True,
        include_ltm: bool = True,
        max_stm: int = 5,
        max_ltm: int = 3
    ) -> Dict[str, Any]:
        """
        Build conversation context for LLM queries.
        
        Args:
            include_stm: Include short-term memories (default: True)
            include_ltm: Include long-term memories (default: True)
            max_stm: Maximum STM entries to include (default: 5)
            max_ltm: Maximum LTM entries to include (default: 3)
            
        Returns:
            Dictionary with conversation context
        """
        context = {
            'conversation_id': self.current_conversation_id,
            'session_id': self.current_session_id,
            'message_count': self.message_count,
            'messages': self.message_buffer.copy(),
            'short_term_memory': [],
            'long_term_memory': [],
            'user_profile': None
        }
        
        if not self.current_conversation_id:
            return context
        
        # Get short-term memories
        if include_stm:
            stm_entries = self.memory_store.get_short_term_memories(
                min_relevance=self.stm_threshold,
                limit=max_stm
            )
            context['short_term_memory'] = stm_entries
        
        # Get long-term memories
        if include_ltm:
            ltm_entries = self.memory_store.get_long_term_memories(
                limit=max_ltm
            )
            context['long_term_memory'] = ltm_entries
        
        # Get user profile
        context['user_profile'] = self.memory_store.get_user_profile()
        
        logger.debug(
            f"📦 Built context: {len(context['messages'])} messages, "
            f"{len(context['short_term_memory'])} STM, "
            f"{len(context['long_term_memory'])} LTM"
        )
        
        return context
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get messages from current conversation buffer.
        
        Args:
            limit: Optional limit on number of messages
            
        Returns:
            List of messages
        """
        if limit:
            return self.message_buffer[-limit:]
        return self.message_buffer.copy()
    
    def clear_buffer(self) -> None:
        """Clear the message buffer (keeps database intact)."""
        self.message_buffer.clear()
        logger.info("🗑️  Cleared message buffer")
    
    def get_active_conversation(self) -> Optional[Dict[str, Any]]:
        """
        Get details of currently active conversation.
        
        Returns:
            Conversation details or None if no active conversation
        """
        if not self.current_conversation_id:
            return None
        
        return self.memory_store.get_conversation_by_id(self.current_conversation_id)
    
    def update_conversation_title(self, title: str) -> bool:
        """
        Update current conversation title.
        
        Args:
            title: New conversation title
            
        Returns:
            True if updated successfully
        """
        if not self.current_conversation_id:
            logger.warning("⚠️  No active conversation")
            return False
        
        self.memory_store.update_conversation(
            self.current_session_id,
            title=title
        )
        logger.info(f"✏️  Updated conversation title: '{title}'")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current conversation and overall system.
        
        Returns:
            Dictionary with statistics
        """
        stats = self.memory_store.get_statistics()
        
        # Add current session stats
        stats['current_conversation'] = {
            'id': self.current_conversation_id,
            'session_id': self.current_session_id,
            'buffer_size': len(self.message_buffer),
            'total_messages': self.message_count,
            'compression_needed': self.message_count >= self.compression_threshold
        }
        
        return stats
    
    # ==================== Profile Onboarding ====================
    
    def should_ask_for_name(
        self,
        cooldown_days: int = 30,
        min_exchanges: int = 3
    ) -> bool:
        """
        Determine if we should ask user for their name.
        
        Args:
            cooldown_days: Days to wait before asking again
            min_exchanges: Minimum conversation exchanges (user+assistant pairs)
            
        Returns:
            True if should ask, False otherwise
        """
        # Check if we have enough conversation
        if len(self.message_buffer) < (min_exchanges * 2):
            return False
        
        # Check with memory store (handles name existence and cooldown)
        return self.memory_store.should_ask_for_name(
            cooldown_days=cooldown_days,
            min_messages=len(self.message_buffer)
        )
    
    def get_name_prompt(self) -> str:
        """
        Get a natural prompt to ask for user's name.
        
        Returns:
            Name prompt string
        """
        prompts = [
            "By the way, I'd love to know your name if you're comfortable sharing!",
            "I don't think I caught your name - what should I call you?",
            "What's your name, if you don't mind me asking?",
            "I'd like to know what to call you - what's your name?"
        ]
        
        # Rotate based on conversation count to add variety
        profile = self.memory_store.get_user_profile()
        conv_count = profile.get('conversation_count', 0)
        
        prompt = prompts[conv_count % len(prompts)]
        
        # Mark that we've asked
        self.memory_store.track_name_prompt()
        self.name_prompt_pending = False
        
        logger.info(f"💬 Generated name prompt: '{prompt}'")
        return prompt
    
    def update_profile_from_conversation(
        self,
        context_compressor
    ) -> Dict[str, Any]:
        """
        Extract and update user profile from current conversation.
        
        Args:
            context_compressor: ContextCompressor instance for LLM extraction
            
        Returns:
            Dictionary with update results
        """
        if not self.message_buffer:
            return {'updated': False, 'reason': 'no_messages'}
        
        logger.info("🔍 Extracting profile from conversation...")
        
        # Extract profile data using LLM
        profile_data = context_compressor.extract_profile_from_conversation(
            self.message_buffer
        )
        
        # Update database with extracted information
        updates = {}
        updated_fields = []
        
        # Update name if extracted
        if profile_data.get('name'):
            current_profile = self.memory_store.get_user_profile()
            if not current_profile.get('name'):
                updates['name'] = profile_data['name']
                updated_fields.append('name')
        
        # Merge preferences
        if profile_data.get('preferences'):
            current_profile = self.memory_store.get_user_profile()
            prefs = current_profile.get('preferences', {})
            prefs.update(profile_data['preferences'])
            updates['preferences'] = prefs
            updated_fields.append(f"{len(profile_data['preferences'])} preferences")
        
        # Merge schedule info
        if profile_data.get('schedule'):
            current_profile = self.memory_store.get_user_profile()
            schedule = current_profile.get('schedule_info', {})
            schedule.update(profile_data['schedule'])
            updates['schedule_info'] = schedule
            updated_fields.append(f"{len(profile_data['schedule'])} schedule items")
        
        # Add habits as personal notes
        if profile_data.get('habits') or profile_data.get('personal_notes'):
            current_profile = self.memory_store.get_user_profile()
            notes = current_profile.get('personality_notes', {})
            if not isinstance(notes, dict):
                notes = {'notes': []}
            if 'notes' not in notes:
                notes['notes'] = []
            
            # Add new habits/notes
            for habit in profile_data.get('habits', []):
                if habit not in notes['notes']:
                    notes['notes'].append(habit)
                    updated_fields.append('habit')
            
            for note in profile_data.get('personal_notes', []):
                if note not in notes['notes']:
                    notes['notes'].append(note)
                    updated_fields.append('note')
            
            updates['personality_notes'] = notes
        
        # Save updates
        if updates:
            self.memory_store.update_user_profile(**updates)
            logger.info(f"✅ Profile updated: {', '.join(updated_fields)}")
            return {
                'updated': True,
                'fields': updated_fields,
                'profile_data': profile_data
            }
        else:
            logger.info("ℹ️  No new profile information extracted")
            return {'updated': False, 'reason': 'no_new_info'}
    
    def __repr__(self) -> str:
        """String representation."""
        if self.current_conversation_id:
            return (
                f"<ConversationManager "
                f"conversation={self.current_conversation_id} "
                f"messages={len(self.message_buffer)}/{self.message_count}>"
            )
        return "<ConversationManager (no active conversation)>"
