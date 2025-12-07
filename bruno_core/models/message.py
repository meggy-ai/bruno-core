"""
Message models for bruno-core.

Defines the structure of messages exchanged in conversations.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageRole(str, Enum):
    """Role of a message sender."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"  # For function/tool call results
    TOOL = "tool"  # Alternative naming for function results


class MessageType(str, Enum):
    """Type of message content."""

    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    FILE = "file"
    COMMAND = "command"
    ACTION = "action"


class Message(BaseModel):
    """
    Represents a single message in a conversation.

    This is the fundamental unit of communication in Bruno.
    Messages can be from users, the assistant, or the system.

    Attributes:
        id: Unique identifier for the message
        role: Who sent the message (user, assistant, system)
        content: The actual message content (text, audio path, etc.)
        message_type: Type of content (text, audio, image, etc.)
        timestamp: When the message was created
        metadata: Additional data (intent, entities, embeddings, etc.)
        parent_id: ID of the message this is responding to (optional)
        conversation_id: ID of the conversation this belongs to (optional)

    Example:
        >>> msg = Message(
        ...     role=MessageRole.USER,
        ...     content="Set a timer for 5 minutes",
        ...     message_type=MessageType.TEXT
        ... )
        >>> print(msg.role)
        MessageRole.USER
    """

    id: UUID = Field(default_factory=uuid4, description="Unique message identifier")
    role: MessageRole = Field(..., description="Role of the message sender")
    content: str = Field(..., min_length=1, description="Message content")
    message_type: MessageType = Field(
        default=MessageType.TEXT, description="Type of message content"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When message was created"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (intent, entities, etc.)"
    )
    parent_id: Optional[UUID] = Field(
        default=None, description="ID of parent message (if this is a reply)"
    )
    conversation_id: Optional[str] = Field(
        default=None, description="ID of conversation this belongs to"
    )

    model_config = ConfigDict(
        use_enum_values=False,  # Keep enums as enums, not strings
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        },
    )

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        """Ensure content is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty or whitespace only")
        return v.strip()

    def to_llm_format(self) -> Dict[str, str]:
        """
        Convert to format expected by LLM clients.

        Returns:
            Dict with 'role' and 'content' keys suitable for LLM APIs

        Example:
            >>> msg = Message(role=MessageRole.USER, content="Hello")
            >>> msg.to_llm_format()
            {'role': 'user', 'content': 'Hello'}
        """
        return {"role": self.role.value, "content": self.content}

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the message.

        Args:
            key: Metadata key
            value: Metadata value

        Example:
            >>> msg = Message(role=MessageRole.USER, content="Set timer")
            >>> msg.add_metadata("intent", "timer_set")
            >>> msg.metadata["intent"]
            'timer_set'
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def __str__(self) -> str:
        """String representation."""
        return f"Message(role={self.role.value}, type={self.message_type.value}, content='{self.content[:50]}...')"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"Message(id={self.id}, role={self.role.value}, "
            f"type={self.message_type.value}, timestamp={self.timestamp.isoformat()})"
        )
