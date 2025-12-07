"""
Validation utilities for bruno-core.

Provides input validation helpers.
"""

import re
from typing import Any, Dict, List, Optional

from bruno_core.utils.exceptions import ValidationError


def validate_user_id(user_id: str) -> str:
    """
    Validate user ID.

    Args:
        user_id: User ID to validate

    Returns:
        Validated user ID (stripped)

    Raises:
        ValidationError: If user_id is invalid

    Example:
        >>> validate_user_id("user_123")
        'user_123'
        >>> validate_user_id("")
        ValidationError: user_id cannot be empty
    """
    if not user_id or not user_id.strip():
        raise ValidationError("user_id cannot be empty")

    user_id = user_id.strip()

    if len(user_id) > 255:
        raise ValidationError(
            "user_id too long",
            details={"max_length": 255, "actual_length": len(user_id)},
        )

    return user_id


def validate_message_content(content: str, min_length: int = 1, max_length: int = 10000) -> str:
    """
    Validate message content.

    Args:
        content: Message content to validate
        min_length: Minimum content length
        max_length: Maximum content length

    Returns:
        Validated content (stripped)

    Raises:
        ValidationError: If content is invalid

    Example:
        >>> validate_message_content("Hello")
        'Hello'
    """
    if not content or not content.strip():
        raise ValidationError("Message content cannot be empty")

    content = content.strip()

    if len(content) < min_length:
        raise ValidationError(
            "Message content too short",
            details={"min_length": min_length, "actual_length": len(content)},
        )

    if len(content) > max_length:
        raise ValidationError(
            "Message content too long",
            details={"max_length": max_length, "actual_length": len(content)},
        )

    return content


def validate_config(config: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate configuration dictionary.

    Args:
        config: Configuration dictionary
        required_fields: List of required field names

    Raises:
        ValidationError: If validation fails

    Example:
        >>> validate_config({"llm": "ollama"}, ["llm", "memory"])
        ValidationError: Missing required fields: memory
    """
    missing_fields = [field for field in required_fields if field not in config]

    if missing_fields:
        raise ValidationError(
            "Missing required configuration fields",
            details={"missing_fields": missing_fields},
        )


def validate_email(email: str) -> str:
    """
    Validate email address.

    Args:
        email: Email address to validate

    Returns:
        Validated email (lowercase)

    Raises:
        ValidationError: If email is invalid

    Example:
        >>> validate_email("user@example.com")
        'user@example.com'
    """
    email = email.strip().lower()

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValidationError("Invalid email address", details={"email": email})

    return email


def validate_url(url: str) -> str:
    """
    Validate URL.

    Args:
        url: URL to validate

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid

    Example:
        >>> validate_url("https://example.com")
        'https://example.com'
    """
    url = url.strip()

    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    if not re.match(pattern, url, re.IGNORECASE):
        raise ValidationError("Invalid URL", details={"url": url})

    return url


def validate_range(
    value: float,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    field_name: str = "value",
) -> float:
    """
    Validate numeric value is within range.

    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Field name for error messages

    Returns:
        Validated value

    Raises:
        ValidationError: If value is out of range

    Example:
        >>> validate_range(0.5, 0.0, 1.0, "temperature")
        0.5
    """
    if min_value is not None and value < min_value:
        raise ValidationError(
            f"{field_name} below minimum",
            details={"value": value, "min": min_value},
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"{field_name} above maximum",
            details={"value": value, "max": max_value},
        )

    return value
