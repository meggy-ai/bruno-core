"""
Context models for bruno-core.

Defines conversation context, user context, and session management structures.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from bruno_core.models.message import Message


class UserContext(BaseModel):
    """
    User-specific context and preferences.

    Stores information about the user that persists across conversations.

    Attributes:
        user_id: Unique user identifier
        name: User's name (if known)
        preferences: User preferences (language, TTS voice, etc.)
        profile: User profile data (timezone, location, etc.)
        metadata: Additional user-specific data

    Example:
        >>> user = UserContext(
        ...     user_id="user_123",
        ...     name="Alice",
        ...     preferences={"language": "en", "tts_voice": "female"}
        ... )
    """

    user_id: str = Field(..., min_length=1, description="Unique user identifier")
    name: Optional[str] = Field(default=None, description="User's name")
    preferences: Dict[str, Any] = Field(
        default_factory=dict, description="User preferences"
    )
    profile: Dict[str, Any] = Field(
        default_factory=dict, description="User profile data"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional user data"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When user was created"
    )
    last_active: datetime = Field(
        default_factory=datetime.utcnow, description="Last activity timestamp"
    )

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def update_activity(self) -> None:
        """Update last activity timestamp to now."""
        self.last_active = datetime.utcnow()

    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference."""
        self.preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.preferences.get(key, default)


class SessionContext(BaseModel):
    """
    Session-specific context.

    Represents a single conversation session with its state.

    Attributes:
        session_id: Unique session identifier
        user_id: User this session belongs to
        started_at: When session started
        ended_at: When session ended (None if active)
        is_active: Whether session is currently active
        state: Session state data (current topic, mode, etc.)
        metadata: Additional session data

    Example:
        >>> session = SessionContext(
        ...     session_id="sess_456",
        ...     user_id="user_123"
        ... )
    """

    session_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique session identifier"
    )
    user_id: str = Field(..., min_length=1, description="User ID this session belongs to")
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Session start time"
    )
    ended_at: Optional[datetime] = Field(
        default=None, description="Session end time (None if active)"
    )
    is_active: bool = Field(default=True, description="Whether session is active")
    state: Dict[str, Any] = Field(
        default_factory=dict, description="Session state data"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional session data"
    )

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def end_session(self) -> None:
        """Mark session as ended."""
        self.ended_at = datetime.utcnow()
        self.is_active = False

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get session state value."""
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Set session state value."""
        self.state[key] = value


class ConversationContext(BaseModel):
    """
    Complete conversation context.

    Contains all information needed for processing a message:
    user context, session context, message history, and additional metadata.

    Attributes:
        conversation_id: Unique conversation identifier
        user: User context
        session: Session context
        messages: Message history (rolling window)
        max_messages: Maximum messages to keep in context
        metadata: Additional conversation metadata

    Example:
        >>> user = UserContext(user_id="user_123")
        >>> session = SessionContext(user_id="user_123")
        >>> context = ConversationContext(
        ...     user=user,
        ...     session=session,
        ...     max_messages=20
        ... )
        >>> context.add_message(Message(role="user", content="Hello"))
    """

    conversation_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique conversation identifier"
    )
    user: UserContext = Field(..., description="User context")
    session: SessionContext = Field(..., description="Session context")
    messages: List[Message] = Field(
        default_factory=list, description="Message history (rolling window)"
    )
    max_messages: int = Field(
        default=20, ge=1, le=1000, description="Max messages to keep in context"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional conversation metadata"
    )

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }

    def add_message(self, message: Message) -> None:
        """
        Add a message to the context.

        Automatically manages rolling window of messages.

        Args:
            message: Message to add
        """
        # Set conversation_id on message
        if message.conversation_id is None:
            message.conversation_id = self.conversation_id

        self.messages.append(message)

        # Maintain rolling window
        if len(self.messages) > self.max_messages:
            # Keep system messages, remove oldest user/assistant messages
            system_messages = [m for m in self.messages if m.role.value == "system"]
            other_messages = [m for m in self.messages if m.role.value != "system"]
            
            # Keep most recent messages
            keep_count = self.max_messages - len(system_messages)
            kept_messages = other_messages[-keep_count:] if keep_count > 0 else []
            
            self.messages = system_messages + kept_messages

    def get_messages_for_llm(self) -> List[Dict[str, str]]:
        """
        Get messages in format suitable for LLM.

        Returns:
            List of dicts with 'role' and 'content' keys
        """
        return [msg.to_llm_format() for msg in self.messages]

    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """
        Get N most recent messages.

        Args:
            count: Number of messages to return

        Returns:
            List of recent messages
        """
        return self.messages[-count:] if self.messages else []

    def clear_messages(self, keep_system: bool = True) -> None:
        """
        Clear message history.

        Args:
            keep_system: If True, keep system messages
        """
        if keep_system:
            self.messages = [m for m in self.messages if m.role.value == "system"]
        else:
            self.messages = []

    def message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)

    def get_last_user_message(self) -> Optional[Message]:
        """Get the most recent user message."""
        for msg in reversed(self.messages):
            if msg.role.value == "user":
                return msg
        return None

    def get_last_assistant_message(self) -> Optional[Message]:
        """Get the most recent assistant message."""
        for msg in reversed(self.messages):
            if msg.role.value == "assistant":
                return msg
        return None
