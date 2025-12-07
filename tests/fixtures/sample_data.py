"""Sample test data fixtures."""

from datetime import datetime
from typing import Dict, List

from bruno_core.models.ability import (AbilityMetadata, AbilityParameter,
                                       AbilityRequest)
from bruno_core.models.memory import MemoryEntry, MemoryType
from bruno_core.models.message import Message, MessageRole


def create_sample_messages(count: int = 5) -> List[Message]:
    """Create sample messages for testing."""
    messages = []
    for i in range(count):
        if i % 2 == 0:
            messages.append(
                Message(
                    role=MessageRole.USER,
                    content=f"User message {i + 1}",
                    metadata={"index": i},
                )
            )
        else:
            messages.append(
                Message(
                    role=MessageRole.ASSISTANT,
                    content=f"Assistant response {i + 1}",
                    metadata={"index": i},
                )
            )
    return messages


def create_sample_memory_entries(user_id: str = "test-user") -> List[MemoryEntry]:
    """Create sample memory entries."""
    return [
        MemoryEntry(
            user_id=user_id,
            conversation_id="conv-1",
            content="User likes pizza",
            memory_type=MemoryType.FACT,
            importance=0.8,
            metadata={"category": "preferences"},
        ),
        MemoryEntry(
            user_id=user_id,
            conversation_id="conv-1",
            content="User's name is John",
            memory_type=MemoryType.FACT,
            importance=0.9,
            metadata={"category": "profile"},
        ),
        MemoryEntry(
            user_id=user_id,
            conversation_id="conv-2",
            content="Discussed Python programming",
            memory_type=MemoryType.EPISODIC,
            importance=0.6,
            metadata={"topic": "programming"},
        ),
    ]


def create_sample_ability_metadata() -> AbilityMetadata:
    """Create sample ability metadata."""
    return AbilityMetadata(
        name="calculator",
        description="Perform mathematical calculations",
        version="1.0.0",
        parameters=[
            AbilityParameter(
                name="operation",
                type="string",
                description="Math operation to perform",
                required=True,
                allowed_values=["add", "subtract", "multiply", "divide"],
            ),
            AbilityParameter(
                name="a",
                type="number",
                description="First number",
                required=True,
            ),
            AbilityParameter(
                name="b",
                type="number",
                description="Second number",
                required=True,
            ),
        ],
        examples=[
            "add 5 and 3",
            "multiply 4 by 7",
            "divide 10 by 2",
        ],
    )


def create_sample_ability_request(
    ability_name: str = "calculator",
    action: str = "calculate",
) -> AbilityRequest:
    """Create sample ability request."""
    return AbilityRequest(
        ability_name=ability_name,
        action=action,
        parameters={
            "operation": "add",
            "a": 5,
            "b": 3,
        },
        user_id="test-user",
        conversation_id="test-conv",
    )


def create_conversation_history() -> List[Dict[str, str]]:
    """Create sample conversation history."""
    return [
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi! How can I help you?"},
        {"role": "user", "content": "What's the weather?"},
        {"role": "assistant", "content": "I don't have access to weather data."},
        {"role": "user", "content": "Can you set a timer?"},
        {"role": "assistant", "content": "Sure! How long should it be?"},
    ]
