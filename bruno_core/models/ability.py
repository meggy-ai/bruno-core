"""
Ability models for bruno-core.

Defines structures for ability requests, responses, and metadata.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AbilityParameterType(str, Enum):
    """Type of ability parameter."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ANY = "any"


class AbilityParameter(BaseModel):
    """
    Parameter definition for an ability.

    Attributes:
        name: Parameter name
        param_type: Parameter type
        description: Human-readable description
        required: Whether parameter is required
        default: Default value if not provided
        constraints: Validation constraints (min, max, pattern, etc.)

    Example:
        >>> param = AbilityParameter(
        ...     name="duration_seconds",
        ...     param_type=AbilityParameterType.INTEGER,
        ...     description="Timer duration in seconds",
        ...     required=True,
        ...     constraints={"min": 1, "max": 86400}
        ... )
    """

    name: str = Field(..., min_length=1, description="Parameter name")
    param_type: AbilityParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether required")
    default: Optional[Any] = Field(default=None, description="Default value")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Validation constraints")

    def validate_value(self, value: Any) -> bool:
        """
        Validate a value against this parameter definition.

        Args:
            value: Value to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic type checking
        if self.param_type == AbilityParameterType.STRING and not isinstance(value, str):
            return False
        elif self.param_type == AbilityParameterType.INTEGER and not isinstance(value, int):
            return False
        elif self.param_type == AbilityParameterType.FLOAT and not isinstance(value, (int, float)):
            return False
        elif self.param_type == AbilityParameterType.BOOLEAN and not isinstance(value, bool):
            return False
        elif self.param_type == AbilityParameterType.LIST and not isinstance(value, list):
            return False
        elif self.param_type == AbilityParameterType.DICT and not isinstance(value, dict):
            return False

        # Check constraints
        if "min" in self.constraints and value < self.constraints["min"]:
            return False
        if "max" in self.constraints and value > self.constraints["max"]:
            return False
        if "min_length" in self.constraints and len(value) < self.constraints["min_length"]:
            return False
        if "max_length" in self.constraints and len(value) > self.constraints["max_length"]:
            return False

        return True


class AbilityMetadata(BaseModel):
    """
    Metadata about an ability.

    Describes what an ability does and what parameters it accepts.

    Attributes:
        name: Ability name
        description: Human-readable description
        version: Ability version
        author: Ability author
        category: Ability category (timer, music, notes, etc.)
        tags: Tags for discovery
        parameters: Parameter definitions
        examples: Usage examples

    Example:
        >>> metadata = AbilityMetadata(
        ...     name="timer",
        ...     description="Manage timers",
        ...     version="1.0.0",
        ...     category="time_management",
        ...     parameters=[
        ...         AbilityParameter(
        ...             name="duration_seconds",
        ...             param_type=AbilityParameterType.INTEGER,
        ...             description="Timer duration"
        ...         )
        ...     ]
        ... )
    """

    name: str = Field(..., min_length=1, description="Ability name")
    description: str = Field(..., description="Ability description")
    version: str = Field(default="1.0.0", description="Ability version")
    author: Optional[str] = Field(default=None, description="Ability author")
    category: Optional[str] = Field(default=None, description="Ability category")
    tags: List[str] = Field(default_factory=list, description="Tags for discovery")
    parameters: List[AbilityParameter] = Field(
        default_factory=list, description="Parameter definitions"
    )
    examples: List[str] = Field(default_factory=list, description="Usage examples")

    def get_parameter(self, name: str) -> Optional[AbilityParameter]:
        """Get parameter definition by name."""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def get_required_parameters(self) -> List[AbilityParameter]:
        """Get all required parameters."""
        return [p for p in self.parameters if p.required]


class AbilityRequest(BaseModel):
    """
    Request to execute an ability.

    Attributes:
        id: Unique request identifier
        ability_name: Name of ability to execute
        action: Specific action within the ability (e.g., "set", "cancel", "status")
        parameters: Action parameters
        user_id: User making the request
        conversation_id: Conversation context
        metadata: Additional request metadata
        timestamp: When request was created

    Example:
        >>> request = AbilityRequest(
        ...     ability_name="timer",
        ...     action="set",
        ...     parameters={"duration_seconds": 300, "label": "Tea timer"},
        ...     user_id="user_123"
        ... )
    """

    id: UUID = Field(default_factory=uuid4, description="Unique request identifier")
    ability_name: str = Field(..., min_length=1, description="Ability name")
    action: str = Field(..., min_length=1, description="Action to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    user_id: str = Field(..., min_length=1, description="User ID")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get a parameter value."""
        return self.parameters.get(key, default)


class AbilityResponse(BaseModel):
    """
    Response from ability execution.

    Attributes:
        request_id: ID of the request this responds to
        ability_name: Name of ability that executed
        action: Action that was performed
        success: Whether execution succeeded
        message: Human-readable result message
        data: Structured result data
        error: Error message if failed
        metadata: Additional response metadata
        timestamp: When response was generated
        execution_time_ms: Execution time in milliseconds

    Example:
        >>> response = AbilityResponse(
        ...     request_id=request.id,
        ...     ability_name="timer",
        ...     action="set",
        ...     success=True,
        ...     message="Timer set for 5 minutes",
        ...     data={"timer_id": "timer_1", "duration": 300}
        ... )
    """

    request_id: UUID = Field(..., description="Request ID")
    ability_name: str = Field(..., description="Ability name")
    action: str = Field(..., description="Action performed")
    success: bool = Field(default=True, description="Whether execution succeeded")
    message: Optional[str] = Field(default=None, description="Result message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    execution_time_ms: Optional[float] = Field(
        default=None, description="Execution time in milliseconds"
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )

    def mark_as_failed(self, error: str) -> None:
        """Mark response as failed."""
        self.success = False
        self.error = error
