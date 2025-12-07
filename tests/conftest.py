"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator, Dict, List

import pytest

from bruno_core.base.ability import BaseAbility
from bruno_core.interfaces.llm import LLMInterface
from bruno_core.interfaces.memory import MemoryInterface
from bruno_core.models.ability import AbilityMetadata, AbilityRequest, AbilityResponse
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

    def list_models(self) -> List[str]:
        """Return mock model list."""
        return ["mock-model-1", "mock-model-2"]


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
        user_id: str,
        conversation_id: str,
    ) -> None:
        """Store message in memory."""
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
        return self.actions


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
    messages = [
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi there!"),
    ]
    return ConversationContext(
        conversation_id="test-conv-123",
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
    return MockLLM(responses=[
        "First response",
        "Second response",
        "Third response",
    ])
