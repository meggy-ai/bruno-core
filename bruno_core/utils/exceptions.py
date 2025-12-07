"""
Custom exceptions for bruno-core.

Defines a hierarchy of exceptions for better error handling.
"""

from typing import Any, Dict, Optional


class BrunoError(Exception):
    """
    Base exception for all Bruno errors.

    All custom Bruno exceptions inherit from this class.

    Attributes:
        message: Error message
        details: Additional error details
        cause: Original exception that caused this error
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize Bruno error.

        Args:
            message: Error message
            details: Additional error details
            cause: Original exception
        """
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)

    def __str__(self) -> str:
        """String representation of error."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"{self.__class__.__name__}(message='{self.message}', details={self.details})"


class ConfigError(BrunoError):
    """
    Configuration-related errors.

    Raised when configuration is invalid, missing, or cannot be loaded.

    Example:
        >>> raise ConfigError("Invalid LLM provider", details={"provider": "unknown"})
    """

    pass


class LLMError(BrunoError):
    """
    LLM-related errors.

    Raised when LLM operations fail (connection, generation, etc.).

    Example:
        >>> raise LLMError("Failed to generate response", details={"status_code": 500})
    """

    pass


class MemoryError(BrunoError):
    """
    Memory-related errors.

    Raised when memory operations fail (storage, retrieval, etc.).

    Example:
        >>> raise MemoryError("Failed to store message", details={"conversation_id": "123"})
    """

    pass


class AbilityError(BrunoError):
    """
    Ability-related errors.

    Raised when ability execution fails.

    Example:
        >>> raise AbilityError(
        ...     "Timer creation failed",
        ...     details={"ability": "timer", "action": "set"}
        ... )
    """

    pass


class ValidationError(BrunoError):
    """
    Validation errors.

    Raised when input validation fails.

    Example:
        >>> raise ValidationError(
        ...     "Invalid user_id",
        ...     details={"user_id": "", "reason": "empty string"}
        ... )
    """

    pass


class RegistryError(BrunoError):
    """
    Registry-related errors.

    Raised when plugin registration/discovery fails.

    Example:
        >>> raise RegistryError("Ability not found", details={"ability_name": "timer"})
    """

    pass


class ContextError(BrunoError):
    """
    Context management errors.

    Raised when context operations fail.

    Example:
        >>> raise ContextError("Session not found", details={"session_id": "sess_123"})
    """

    pass


class EventError(BrunoError):
    """
    Event system errors.

    Raised when event operations fail.

    Example:
        >>> raise EventError("Failed to emit event", details={"event_type": "message.sent"})
    """

    pass


class StreamError(BrunoError):
    """
    Streaming errors.

    Raised when streaming operations fail.

    Example:
        >>> raise StreamError("Stream interrupted", details={"chunk_count": 42})
    """

    pass
