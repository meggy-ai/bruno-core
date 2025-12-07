"""Pytest configuration and shared fixtures."""

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

import pytest

from bruno_core.base.ability import BaseAbility
from bruno_core.interfaces.llm import LLMInterface
from bruno_core.interfaces.memory import MemoryInterface
from bruno_core.models.ability import (AbilityMetadata, AbilityRequest,
                                       AbilityResponse)
from bruno_core.models.config import BrunoConfig, LLMConfig, MemoryConfig
from bruno_core.models.context import ConversationContext
from bruno_core.models.memory import MemoryEntry
from bruno_core.models.message import Message, MessageRole
from bruno_core.models.response import AssistantResponse


# Configure pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock LLM Implementation
class MockLLM(LLMInterface):
    """Mock LLM for testing."""

    def __init__(self, responses: List[str] = None):
        """Initialize with predefined responses."""
        self.responses = responses or ["Mock response"]
        self.call_count = 0
        self.last_messages = []

    async def generate(
        self,
        messages: List[Message],
        model: str = "mock",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Return predefined response."""
        self.last_messages = messages
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response

    async def stream(
        self,
        messages: List[Message],
        model: str = "mock",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        """Stream mock response."""
        response = await self.generate(messages, model, temperature, max_tokens)
        for char in response:
            yield char

    def get_token_count(self, text: str) -> int:
        """Return simple token count."""
        return len(text.split())

    async def list_models(self) -> List[str]:
        """Return mock model list."""
        return ["mock-model-1", "mock-model-2"]

    async def check_connection(self) -> bool:
        """Check if LLM is accessible."""
        return True

    def get_model_info(self) -> Dict[str, any]:
        """Get model information."""
        return {
            "model": "mock",
            "provider": "test",
            "max_tokens": 1000,
        }

    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
        self.system_prompt = prompt

    def get_system_prompt(self) -> str:
        """Get system prompt."""
        return getattr(self, "system_prompt", "You are a helpful assistant.")


# Mock Memory Implementation
class MockMemory(MemoryInterface):
    """Mock memory for testing."""

    def __init__(self):
        """Initialize mock memory."""
        self.messages: Dict[str, List[Message]] = {}
        self.memories: List[MemoryEntry] = []

    async def store_message(
        self,
        message: Message,
        conversation_id: str,
    ) -> None:
        """Store message in memory."""
        # Extract user_id from message metadata or use default
        user_id = message.metadata.get("user_id", "default")
        key = f"{user_id}:{conversation_id}"
        if key not in self.messages:
            self.messages[key] = []
        self.messages[key].append(message)

    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        conversation_id: str = None,
    ) -> List[Message]:
        """Retrieve messages."""
        key = f"{user_id}:{conversation_id}" if conversation_id else None

        if key and key in self.messages:
            return self.messages[key][-limit:]

        # Return all messages for user
        all_messages = []
        for k, msgs in self.messages.items():
            if k.startswith(f"{user_id}:"):
                all_messages.extend(msgs)

        return all_messages[-limit:]

    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> List[MemoryEntry]:
        """Search memories."""
        return [m for m in self.memories if m.user_id == user_id][:limit]

    async def clear_conversation(
        self,
        user_id: str,
        conversation_id: str,
    ) -> None:
        """Clear conversation."""
        key = f"{user_id}:{conversation_id}"
        if key in self.messages:
            del self.messages[key]

    async def retrieve_messages(
        self,
        conversation_id: str,
        limit: int = None,
    ) -> List[Message]:
        """Retrieve messages from a conversation."""
        for key, msgs in self.messages.items():
            if key.endswith(f":{conversation_id}"):
                return msgs[-limit:] if limit else msgs
        return []

    async def search_messages(
        self,
        query: str,
        user_id: str = None,
        limit: int = 10,
    ) -> List[Message]:
        """Search messages by query."""
        results = []
        for key, msgs in self.messages.items():
            if user_id and not key.startswith(f"{user_id}:"):
                continue
            for msg in msgs:
                if query.lower() in msg.content.lower():
                    results.append(msg)
        return results[:limit]

    async def store_memory(self, memory_entry: MemoryEntry) -> None:
        """Store a memory entry."""
        self.memories.append(memory_entry)

    async def retrieve_memories(self, query) -> List[MemoryEntry]:
        """Retrieve memories matching query."""
        results = [m for m in self.memories if m.user_id == query.user_id]
        if query.memory_types:
            results = [m for m in results if m.memory_type in query.memory_types]
        return results[: query.limit] if query.limit else results

    async def delete_memory(self, memory_id: str) -> None:
        """Delete a memory entry."""
        self.memories = [m for m in self.memories if str(m.id) != memory_id]

    async def create_session(
        self,
        user_id: str,
        metadata: Dict[str, any] = None,
    ) -> "SessionContext":
        """Create a new session."""
        from bruno_core.models.context import SessionContext

        return SessionContext(user_id=user_id, metadata=metadata or {})

    async def get_session(self, session_id: str) -> Optional["SessionContext"]:
        """Get a session by ID."""
        # Mock implementation - always returns None
        return None

    async def end_session(self, session_id: str) -> None:
        """End a session."""
        pass  # Mock implementation

    async def get_context(
        self,
        user_id: str,
        session_id: str = None,
    ) -> "ConversationContext":
        """Get conversation context."""
        from bruno_core.models.context import (ConversationContext,
                                               SessionContext, UserContext)

        user = UserContext(user_id=user_id)
        session = SessionContext(user_id=user_id)
        return ConversationContext(user=user, session=session)

    async def clear_history(
        self,
        conversation_id: str,
        keep_system_messages: bool = True,
    ) -> None:
        """Clear conversation history."""
        for key in list(self.messages.keys()):
            if key.endswith(f":{conversation_id}"):
                if keep_system_messages:
                    self.messages[key] = [m for m in self.messages[key] if m.role.value == "system"]
                else:
                    del self.messages[key]

    async def get_statistics(self, user_id: str) -> Dict[str, any]:
        """Get memory statistics."""
        user_messages = sum(1 for key in self.messages.keys() if key.startswith(f"{user_id}:"))
        user_memories = sum(1 for m in self.memories if m.user_id == user_id)
        return {
            "total_messages": user_messages,
            "total_memories": user_memories,
        }


# Mock Ability Implementation
class MockAbility(BaseAbility):
    """Mock ability for testing."""

    def __init__(self, name: str = "mock", actions: List[str] = None):
        """Initialize mock ability."""
        self.name = name
        self.actions = actions or ["test"]
        self.executed_requests = []
        super().__init__()

    def get_metadata(self) -> AbilityMetadata:
        """Return mock metadata."""
        return AbilityMetadata(
            name=self.name,
            description="Mock ability for testing",
            version="1.0.0",
            examples=["test action"],
        )

    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        """Execute mock action."""
        self.executed_requests.append(request)

        return AbilityResponse(
            request_id=request.id,
            ability_name=self.name,
            action=request.action,
            success=True,
            message=f"Executed {request.action}",
            data={"mock": True},
        )

    def get_supported_actions(self) -> List[str]:
        """Return supported actions."""
        # Return actions list, but also accept any action in tests
        return self.actions

    def validate_request(self, request: AbilityRequest) -> bool:
        """Override validation to accept any action in tests."""
        return True


# Fixtures
@pytest.fixture
def mock_llm() -> MockLLM:
    """Provide mock LLM."""
    return MockLLM()


@pytest.fixture
def mock_memory() -> MockMemory:
    """Provide mock memory."""
    return MockMemory()


@pytest.fixture
def mock_ability() -> MockAbility:
    """Provide mock ability."""
    return MockAbility()


@pytest.fixture
def sample_message() -> Message:
    """Provide sample message."""
    return Message(
        role=MessageRole.USER,
        content="Hello, how are you?",
        metadata={"test": True},
    )


@pytest.fixture
def sample_messages() -> List[Message]:
    """Provide list of sample messages."""
    return [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="What is 2+2?"),
        Message(role=MessageRole.ASSISTANT, content="2+2 equals 4."),
    ]


@pytest.fixture
def sample_context() -> ConversationContext:
    """Provide sample conversation context."""
    from bruno_core.models.context import SessionContext, UserContext

    user = UserContext(user_id="test-user-123")
    session = SessionContext(user_id="test-user-123")

    messages = [
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi there!"),
    ]
    return ConversationContext(
        conversation_id="test-conv-123",
        user=user,
        session=session,
        messages=messages,
        metadata={"test": True},
    )


@pytest.fixture
def bruno_config() -> BrunoConfig:
    """Provide test configuration."""
    return BrunoConfig(
        llm=LLMConfig(
            provider="mock",
            model="mock-model",
            temperature=0.7,
            max_tokens=1000,
        ),
        memory=MemoryConfig(
            backend="mock",
            max_context_messages=20,
        ),
    )


@pytest.fixture
async def mock_llm_with_responses() -> MockLLM:
    """Provide mock LLM with multiple responses."""
    return MockLLM(
        responses=[
            "First response",
            "Second response",
            "Third response",
        ]
    )
