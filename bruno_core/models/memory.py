"""
Memory models for bruno-core.

Defines structures for memory storage, retrieval, and queries.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Type of memory entry."""

    SHORT_TERM = "short_term"  # Recent conversation facts
    LONG_TERM = "long_term"  # Persistent knowledge
    EPISODIC = "episodic"  # Specific events/conversations
    SEMANTIC = "semantic"  # General knowledge
    PROCEDURAL = "procedural"  # How-to knowledge


class MemoryMetadata(BaseModel):
    """
    Metadata for a memory entry.

    Attributes:
        source: Where memory came from (conversation, user input, etc.)
        category: Memory category (preference, fact, event, etc.)
        tags: Tags for categorization
        confidence: Confidence score (0.0 to 1.0)
        importance: Importance score (0.0 to 1.0)
        access_count: How many times accessed
        embedding: Vector embedding for similarity search
        related_memories: IDs of related memories

    Example:
        >>> metadata = MemoryMetadata(
        ...     source="conversation",
        ...     category="preference",
        ...     tags=["music", "favorite"],
        ...     confidence=0.95,
        ...     importance=0.8
        ... )
    """

    source: str = Field(..., description="Memory source")
    category: Optional[str] = Field(default=None, description="Memory category")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    importance: float = Field(default=1.0, ge=0.0, le=1.0, description="Importance score")
    access_count: int = Field(default=0, ge=0, description="Access count")
    embedding: Optional[List[float]] = Field(
        default=None, description="Vector embedding"
    )
    related_memories: List[UUID] = Field(
        default_factory=list, description="Related memory IDs"
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata fields"
    )

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            UUID: lambda v: str(v),
        }


class MemoryEntry(BaseModel):
    """
    A single memory entry.

    Represents a piece of information stored in memory.

    Attributes:
        id: Unique memory identifier
        content: The actual memory content/fact
        memory_type: Type of memory
        user_id: User this memory belongs to
        conversation_id: Conversation where memory was created
        metadata: Additional memory metadata
        created_at: When memory was created
        updated_at: When memory was last updated
        last_accessed: When memory was last accessed
        expires_at: Optional expiration time

    Example:
        >>> memory = MemoryEntry(
        ...     content="User's favorite genre is jazz",
        ...     memory_type=MemoryType.LONG_TERM,
        ...     user_id="user_123",
        ...     metadata=MemoryMetadata(
        ...         source="conversation",
        ...         category="preference"
        ...     )
        ... )
    """

    id: UUID = Field(default_factory=uuid4, description="Unique memory identifier")
    content: str = Field(..., min_length=1, description="Memory content")
    memory_type: MemoryType = Field(..., description="Type of memory")
    user_id: str = Field(..., min_length=1, description="User ID")
    conversation_id: Optional[str] = Field(
        default=None, description="Conversation ID where created"
    )
    metadata: MemoryMetadata = Field(
        default_factory=MemoryMetadata, description="Memory metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )
    last_accessed: datetime = Field(
        default_factory=datetime.utcnow, description="Last access time"
    )
    expires_at: Optional[datetime] = Field(
        default=None, description="Expiration time (None = no expiration)"
    )

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }

    def update_access(self) -> None:
        """Update access timestamp and increment access count."""
        self.last_accessed = datetime.utcnow()
        self.metadata.access_count += 1

    def is_expired(self) -> bool:
        """Check if memory has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def update_content(self, new_content: str) -> None:
        """Update memory content."""
        self.content = new_content
        self.updated_at = datetime.utcnow()


class MemoryQuery(BaseModel):
    """
    Query for retrieving memories.

    Attributes:
        query_text: Text query for semantic search
        user_id: Filter by user ID
        memory_types: Filter by memory types
        categories: Filter by categories
        tags: Filter by tags
        min_confidence: Minimum confidence score
        min_importance: Minimum importance score
        limit: Maximum results to return
        include_expired: Whether to include expired memories
        similarity_threshold: Minimum similarity score (0.0 to 1.0)

    Example:
        >>> query = MemoryQuery(
        ...     query_text="music preferences",
        ...     user_id="user_123",
        ...     memory_types=[MemoryType.LONG_TERM],
        ...     limit=10
        ... )
    """

    query_text: Optional[str] = Field(default=None, description="Text query")
    user_id: str = Field(..., min_length=1, description="User ID")
    memory_types: List[MemoryType] = Field(
        default_factory=list, description="Filter by memory types"
    )
    categories: List[str] = Field(
        default_factory=list, description="Filter by categories"
    )
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    min_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum confidence"
    )
    min_importance: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum importance"
    )
    limit: int = Field(default=10, ge=1, le=1000, description="Maximum results")
    include_expired: bool = Field(
        default=False, description="Include expired memories"
    )
    similarity_threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum similarity score"
    )
