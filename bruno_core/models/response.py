"""
Response models for bruno-core.

Defines the structure of responses from the assistant.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ActionStatus(str, Enum):
    """Status of an executed action."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


class ActionResult(BaseModel):
    """
    Result of an executed action.

    Attributes:
        action_type: Type of action executed
        status: Execution status
        message: Result message
        data: Additional result data
        error: Error message if failed

    Example:
        >>> result = ActionResult(
        ...     action_type="timer_set",
        ...     status=ActionStatus.SUCCESS,
        ...     message="Timer set for 5 minutes"
        ... )
    """

    action_type: str = Field(..., description="Type of action")
    status: ActionStatus = Field(..., description="Execution status")
    message: Optional[str] = Field(default=None, description="Result message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    executed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When action was executed"
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class AssistantResponse(BaseModel):
    """
    Complete response from the assistant.

    Contains the text response and any actions that were executed.

    Attributes:
        id: Unique response identifier
        text: Text response to display/speak to user
        actions: List of action results
        success: Whether request was processed successfully
        error: Error message if processing failed
        metadata: Additional response metadata
        timestamp: When response was generated

    Example:
        >>> response = AssistantResponse(
        ...     text="I've set a timer for 5 minutes.",
        ...     actions=[
        ...         ActionResult(
        ...             action_type="timer_set",
        ...             status=ActionStatus.SUCCESS,
        ...             message="Timer started"
        ...         )
        ...     ],
        ...     success=True
        ... )
    """

    id: UUID = Field(default_factory=uuid4, description="Unique response identifier")
    text: str = Field(..., min_length=1, description="Text response")
    actions: List[ActionResult] = Field(default_factory=list, description="Executed actions")
    success: bool = Field(default=True, description="Whether request succeeded")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional response metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response generation time"
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )

    def add_action(self, action: ActionResult) -> None:
        """Add an action result to the response."""
        self.actions.append(action)

    def has_actions(self) -> bool:
        """Check if response has any actions."""
        return len(self.actions) > 0

    def get_successful_actions(self) -> List[ActionResult]:
        """Get all successful actions."""
        return [a for a in self.actions if a.status == ActionStatus.SUCCESS]

    def get_failed_actions(self) -> List[ActionResult]:
        """Get all failed actions."""
        return [a for a in self.actions if a.status == ActionStatus.FAILED]

    def mark_as_failed(self, error: str) -> None:
        """Mark response as failed with error message."""
        self.success = False
        self.error = error


class StreamResponse(BaseModel):
    """
    Streaming response chunk from the assistant.

    Used for streaming text generation.

    Attributes:
        chunk: Text chunk
        is_complete: Whether this is the final chunk
        metadata: Additional chunk metadata

    Example:
        >>> chunk = StreamResponse(chunk="Hello", is_complete=False)
        >>> final = StreamResponse(chunk="!", is_complete=True)
    """

    chunk: str = Field(..., description="Text chunk")
    is_complete: bool = Field(default=False, description="Whether this is final chunk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional chunk metadata")

    def __str__(self) -> str:
        """String representation returns the chunk."""
        return self.chunk
