"""
Memory Interface - Memory storage and retrieval contract.

Defines the contract for memory backends (SQLite, PostgreSQL, Redis, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from bruno_core.models.context import ConversationContext, SessionContext
from bruno_core.models.memory import MemoryEntry, MemoryQuery
from bruno_core.models.message import Message


class MemoryInterface(ABC):
    """
    Abstract interface for memory storage backends.

    All memory implementations (SQLite, PostgreSQL, Redis, etc.) must
    implement this interface.

    Memory handles:
    - Message storage and retrieval
    - Conversation context management
    - Short-term and long-term memory
    - Semantic search

    Example:
        >>> class SQLiteMemory(MemoryInterface):
        ...     async def store_message(self, message):
        ...         # Implementation
        ...         pass
    """

    @abstractmethod
    async def store_message(
        self,
        message: Message,
        conversation_id: str,
    ) -> None:
        """
        Store a message in memory.

        Args:
            message: Message to store
            conversation_id: Conversation this message belongs to

        Raises:
            MemoryError: If storage fails

        Example:
            >>> message = Message(role="user", content="Hello")
            >>> await memory.store_message(message, "conv_123")
        """
        pass

    @abstractmethod
    async def retrieve_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """
        Retrieve messages from a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages (most recent first)

        Raises:
            MemoryError: If retrieval fails

        Example:
            >>> messages = await memory.retrieve_messages("conv_123", limit=10)
        """
        pass

    @abstractmethod
    async def search_messages(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Message]:
        """
        Search messages by text query.

        Args:
            query: Search query
            user_id: Optional user ID to filter by
            limit: Maximum results

        Returns:
            List of matching messages

        Raises:
            MemoryError: If search fails

        Example:
            >>> results = await memory.search_messages("timer", user_id="user_123")
        """
        pass

    @abstractmethod
    async def store_memory(self, memory_entry: MemoryEntry) -> None:
        """
        Store a memory entry (fact, preference, etc.).

        Args:
            memory_entry: Memory entry to store

        Raises:
            MemoryError: If storage fails

        Example:
            >>> entry = MemoryEntry(
            ...     content="User loves jazz music",
            ...     memory_type=MemoryType.LONG_TERM,
            ...     user_id="user_123"
            ... )
            >>> await memory.store_memory(entry)
        """
        pass

    @abstractmethod
    async def retrieve_memories(self, query: MemoryQuery) -> List[MemoryEntry]:
        """
        Retrieve memories matching query criteria.

        Args:
            query: Memory query with filters

        Returns:
            List of matching memory entries

        Raises:
            MemoryError: If retrieval fails

        Example:
            >>> query = MemoryQuery(
            ...     user_id="user_123",
            ...     memory_types=[MemoryType.LONG_TERM],
            ...     limit=5
            ... )
            >>> memories = await memory.retrieve_memories(query)
        """
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str) -> None:
        """
        Delete a memory entry.

        Args:
            memory_id: Memory entry ID

        Raises:
            MemoryError: If deletion fails

        Example:
            >>> await memory.delete_memory("mem_456")
        """
        pass

    @abstractmethod
    async def create_session(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionContext:
        """
        Create a new conversation session.

        Args:
            user_id: User ID
            metadata: Optional session metadata

        Returns:
            Session context

        Raises:
            MemoryError: If creation fails

        Example:
            >>> session = await memory.create_session("user_123")
        """
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session context or None if not found

        Example:
            >>> session = await memory.get_session("sess_789")
        """
        pass

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        """
        End a conversation session.

        Args:
            session_id: Session ID

        Raises:
            MemoryError: If session not found

        Example:
            >>> await memory.end_session("sess_789")
        """
        pass

    @abstractmethod
    async def get_context(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> ConversationContext:
        """
        Get conversation context for a user.

        Args:
            user_id: User ID
            session_id: Optional session ID

        Returns:
            Conversation context

        Raises:
            MemoryError: If context cannot be retrieved

        Example:
            >>> context = await memory.get_context("user_123")
        """
        pass

    @abstractmethod
    async def clear_history(
        self,
        conversation_id: str,
        keep_system_messages: bool = True,
    ) -> None:
        """
        Clear message history for a conversation.

        Args:
            conversation_id: Conversation ID
            keep_system_messages: Whether to keep system messages

        Raises:
            MemoryError: If clearing fails

        Example:
            >>> await memory.clear_history("conv_123")
        """
        pass

    @abstractmethod
    async def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get memory statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dict with statistics

        Example:
            >>> stats = await memory.get_statistics("user_123")
            >>> print(stats)
            {'total_messages': 150, 'conversations': 10, 'memories': 25}
        """
        pass
