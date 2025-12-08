"""
Context Manager implementation.

Manages conversation context windows with rolling message buffers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from bruno_core.interfaces.memory import MemoryInterface
from bruno_core.models.context import ConversationContext
from bruno_core.models.message import Message, MessageRole
from bruno_core.utils.exceptions import ContextError
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class ContextManager:
    """
    Manages conversation context with rolling window and memory integration.

    Features:
    - Rolling message window (configurable size)
    - Automatic context window management
    - Memory storage coordination
    - Token counting and optimization
    - Context compression triggers

    Example:
        >>> manager = ContextManager(memory=memory_store, max_messages=20)
        >>> await manager.add_message(message, conversation_id="conv_123")
        >>> context = await manager.get_context(conversation_id="conv_123")
    """

    def __init__(
        self,
        memory: MemoryInterface,
        max_messages: int = 20,
        compression_threshold: int = 50,
        auto_save: bool = True,
    ):
        """
        Initialize context manager.

        Args:
            memory: Memory backend for persistence
            max_messages: Maximum messages in rolling window
            compression_threshold: Message count triggering compression
            auto_save: Automatically save messages to memory
        """
        self.memory = memory
        self.max_messages = max_messages
        self.compression_threshold = compression_threshold
        self.auto_save = auto_save

        # Context buffers per conversation
        self._buffers: Dict[str, List[Message]] = {}
        self._message_counts: Dict[str, int] = {}

        logger.info(
            "context_manager_initialized",
            max_messages=max_messages,
            compression_threshold=compression_threshold,
        )

    async def add_message(
        self,
        message: Message,
        conversation_id: str,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Add a message to the conversation context.

        Args:
            message: Message to add
            conversation_id: Conversation identifier
            user_id: Optional user identifier for memory storage
        """
        try:
            # Initialize buffer if needed
            if conversation_id not in self._buffers:
                self._buffers[conversation_id] = []
                self._message_counts[conversation_id] = 0

            # Add to buffer
            self._buffers[conversation_id].append(message)
            self._message_counts[conversation_id] += 1

            # Apply rolling window
            if len(self._buffers[conversation_id]) > self.max_messages:
                removed = self._buffers[conversation_id].pop(0)
                logger.debug(
                    "message_removed_from_window",
                    conversation_id=conversation_id,
                    message_id=removed.id,
                )

            # Save to memory if enabled
            if self.auto_save and user_id:
                await self.memory.store_message(message, conversation_id)

            # Check compression trigger
            if self._should_trigger_compression(conversation_id):
                logger.info(
                    "compression_threshold_reached",
                    conversation_id=conversation_id,
                    message_count=self._message_counts[conversation_id],
                )
                # Note: Actual compression would be handled by a background job
                # This just logs the trigger point

            logger.debug(
                "message_added_to_context",
                conversation_id=conversation_id,
                role=message.role,
                buffer_size=len(self._buffers[conversation_id]),
            )

        except Exception as e:
            logger.error(
                "failed_to_add_message",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise ContextError(
                "Failed to add message to context",
                details={"conversation_id": conversation_id},
                cause=e,
            )

    async def get_context(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
        include_system: bool = True,
    ) -> ConversationContext:
        """
        Get conversation context for a conversation.

        Args:
            conversation_id: Conversation identifier
            user_id: Optional user identifier for memory retrieval
            include_system: Include system messages in context

        Returns:
            ConversationContext with messages and metadata
        """
        try:
            # Get messages from buffer
            buffer_messages = self._buffers.get(conversation_id, [])

            # Filter system messages if needed
            if not include_system:
                buffer_messages = [m for m in buffer_messages if m.role != MessageRole.SYSTEM]

            # Retrieve relevant memories if user_id provided
            relevant_memories = []
            if user_id and buffer_messages:
                # Get the last user message as query context
                user_messages = [m for m in buffer_messages if m.role == MessageRole.USER]
                if user_messages and hasattr(self.memory, "retrieve_context"):
                    last_query = user_messages[-1].content
                    # retrieve_context is an optional extension method
                    relevant_memories = await self.memory.retrieve_context(
                        user_id=user_id, query=last_query, limit=5
                    )

            # Create user and session contexts
            from bruno_core.models.context import SessionContext, UserContext

            # Ensure user_id and conversation_id are not None
            safe_user_id = user_id or "unknown"
            safe_conversation_id = conversation_id or "default"

            user_context = UserContext(user_id=safe_user_id)
            session_context = SessionContext(
                user_id=safe_user_id, conversation_id=safe_conversation_id
            )

            # Build context
            context = ConversationContext(
                conversation_id=conversation_id,
                user=user_context,
                session=session_context,
                messages=buffer_messages,
                metadata={
                    "buffer_size": len(buffer_messages),
                    "total_messages": self._message_counts.get(conversation_id, 0),
                    "relevant_memories_count": len(relevant_memories),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            # Add relevant memories to metadata
            if relevant_memories:
                context.metadata["relevant_memories"] = [
                    {"content": m.content, "role": m.role.value} for m in relevant_memories
                ]

            logger.debug(
                "context_retrieved",
                conversation_id=conversation_id,
                message_count=len(buffer_messages),
                memories_count=len(relevant_memories),
            )

            return context

        except Exception as e:
            logger.error(
                "failed_to_get_context",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise ContextError(
                "Failed to retrieve context",
                details={"conversation_id": conversation_id},
                cause=e,
            )

    async def clear_context(self, conversation_id: str) -> None:
        """
        Clear context buffer for a conversation.

        Args:
            conversation_id: Conversation identifier
        """
        if conversation_id in self._buffers:
            message_count = len(self._buffers[conversation_id])
            del self._buffers[conversation_id]

            if conversation_id in self._message_counts:
                del self._message_counts[conversation_id]

            logger.info(
                "context_cleared",
                conversation_id=conversation_id,
                messages_removed=message_count,
            )

    def get_buffer_size(self, conversation_id: str) -> int:
        """
        Get current buffer size for a conversation.

        Args:
            conversation_id: Conversation identifier

        Returns:
            Number of messages in buffer
        """
        return len(self._buffers.get(conversation_id, []))

    def get_total_messages(self, conversation_id: str) -> int:
        """
        Get total message count for a conversation.

        Args:
            conversation_id: Conversation identifier

        Returns:
            Total messages processed
        """
        return self._message_counts.get(conversation_id, 0)

    def _should_trigger_compression(self, conversation_id: str) -> bool:
        """
        Check if compression should be triggered.

        Args:
            conversation_id: Conversation identifier

        Returns:
            True if compression threshold reached
        """
        count = self._message_counts.get(conversation_id, 0)
        return count > 0 and count % self.compression_threshold == 0

    def list_active_conversations(self) -> List[str]:
        """
        List all active conversation IDs.

        Returns:
            List of conversation IDs with active buffers
        """
        return list(self._buffers.keys())

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get context manager statistics.

        Returns:
            Dict with statistics
        """
        total_buffered = sum(len(buffer) for buffer in self._buffers.values())
        total_messages = sum(self._message_counts.values())

        return {
            "active_conversations": len(self._buffers),
            "total_buffered_messages": total_buffered,
            "total_messages_processed": total_messages,
            "max_messages": self.max_messages,
            "compression_threshold": self.compression_threshold,
        }
