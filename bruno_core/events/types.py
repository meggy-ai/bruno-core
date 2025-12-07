"""
Event type definitions.

Defines event data structures for the event bus.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event type enumeration."""

    # Message events
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    MESSAGE_PROCESSED = "message.processed"

    # Ability events
    ABILITY_REGISTERED = "ability.registered"
    ABILITY_UNREGISTERED = "ability.unregistered"
    ABILITY_EXECUTING = "ability.executing"
    ABILITY_EXECUTED = "ability.executed"
    ABILITY_FAILED = "ability.failed"

    # Session events
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    SESSION_RESUMED = "session.resumed"

    # Context events
    CONTEXT_UPDATED = "context.updated"
    CONTEXT_CLEARED = "context.cleared"
    COMPRESSION_TRIGGERED = "compression.triggered"

    # Error events
    ERROR_OCCURRED = "error.occurred"
    WARNING_OCCURRED = "warning.occurred"

    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
    HEALTH_CHECK = "health.check"


class Event(BaseModel):
    """
    Base event class.

    Attributes:
        event_id: Unique event identifier
        event_type: Type of event
        timestamp: Event timestamp
        data: Event payload
        metadata: Additional metadata
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class MessageEvent(Event):
    """
    Message-related event.

    Attributes:
        message_id: Message identifier
        user_id: User identifier
        conversation_id: Conversation identifier
        role: Message role
        content: Message content (optional for privacy)
    """

    message_id: str
    user_id: str
    conversation_id: str
    role: str
    content: Optional[str] = None


class AbilityEvent(Event):
    """
    Ability-related event.

    Attributes:
        ability_name: Ability name
        action: Action being performed
        user_id: User identifier
        success: Whether action succeeded (for executed events)
    """

    ability_name: str
    action: Optional[str] = None
    user_id: Optional[str] = None
    success: Optional[bool] = None


class SessionEvent(Event):
    """
    Session-related event.

    Attributes:
        session_id: Session identifier
        user_id: User identifier
        conversation_id: Conversation identifier
    """

    session_id: str
    user_id: str
    conversation_id: str


class ErrorEvent(Event):
    """
    Error-related event.

    Attributes:
        error_type: Type of error
        error_message: Error message
        component: Component where error occurred
        user_id: Optional user identifier
        traceback: Optional error traceback
    """

    error_type: str
    error_message: str
    component: str
    user_id: Optional[str] = None
    traceback: Optional[str] = None
