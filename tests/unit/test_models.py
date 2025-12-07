"""Tests for data models."""

import pytest
from datetime import datetime

from bruno_core.models.message import Message, MessageRole, MessageType
from bruno_core.models.context import ConversationContext, UserContext
from bruno_core.models.response import AssistantResponse, ActionResult, ActionStatus
from bruno_core.models.ability import AbilityMetadata, AbilityParameter, AbilityRequest
from bruno_core.models.memory import MemoryEntry, MemoryType


class TestMessage:
    """Tests for Message model."""

    def test_create_message(self):
        """Test creating a message."""
        msg = Message(
            role=MessageRole.USER,
            content="Hello world",
        )
        
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello world"
        assert msg.id is not None
        assert msg.timestamp is not None

    def test_message_with_metadata(self):
        """Test message with metadata."""
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Response",
            metadata={"source": "test"},
        )
        
        assert msg.metadata["source"] == "test"

    def test_to_llm_format(self):
        """Test converting to LLM format."""
        msg = Message(
            role=MessageRole.USER,
            content="Test message",
        )
        
        llm_format = msg.to_llm_format()
        assert llm_format["role"] == "user"
        assert llm_format["content"] == "Test message"


class TestConversationContext:
    """Tests for ConversationContext model."""

    def test_create_context(self):
        """Test creating conversation context."""
        messages = [
            Message(role=MessageRole.USER, content="Hi"),
            Message(role=MessageRole.ASSISTANT, content="Hello"),
        ]
        
        ctx = ConversationContext(
            conversation_id="test-123",
            messages=messages,
        )
        
        assert ctx.conversation_id == "test-123"
        assert len(ctx.messages) == 2

    def test_to_llm_format(self):
        """Test converting context to LLM format."""
        messages = [
            Message(role=MessageRole.SYSTEM, content="System"),
            Message(role=MessageRole.USER, content="User"),
        ]
        
        ctx = ConversationContext(
            conversation_id="test",
            messages=messages,
        )
        
        llm_messages = ctx.to_llm_format()
        assert len(llm_messages) == 2
        assert llm_messages[0]["role"] == "system"


class TestAssistantResponse:
    """Tests for AssistantResponse model."""

    def test_create_response(self):
        """Test creating assistant response."""
        response = AssistantResponse(
            text="Response text",
            success=True,
        )
        
        assert response.text == "Response text"
        assert response.success is True
        assert response.actions == []

    def test_response_with_actions(self):
        """Test response with action results."""
        action = ActionResult(
            action_type="test",
            status=ActionStatus.SUCCESS,
            message="Done",
        )
        
        response = AssistantResponse(
            text="Response",
            success=True,
            actions=[action],
        )
        
        assert len(response.actions) == 1
        assert response.actions[0].status == ActionStatus.SUCCESS


class TestAbilityModels:
    """Tests for ability models."""

    def test_ability_metadata(self):
        """Test ability metadata."""
        metadata = AbilityMetadata(
            name="test",
            description="Test ability",
            version="1.0.0",
        )
        
        assert metadata.name == "test"
        assert metadata.version == "1.0.0"

    def test_ability_parameter(self):
        """Test ability parameter."""
        param = AbilityParameter(
            name="count",
            type="number",
            description="Number of items",
            required=True,
        )
        
        assert param.name == "count"
        assert param.required is True

    def test_parameter_validation(self):
        """Test parameter value validation."""
        param = AbilityParameter(
            name="status",
            type="string",
            allowed_values=["active", "inactive"],
        )
        
        assert param.validate_value("active") is True
        assert param.validate_value("invalid") is False

    def test_ability_request(self):
        """Test ability request."""
        request = AbilityRequest(
            ability_name="timer",
            action="set",
            parameters={"duration": 60},
            user_id="user-123",
        )
        
        assert request.ability_name == "timer"
        assert request.parameters["duration"] == 60


class TestMemoryEntry:
    """Tests for MemoryEntry model."""

    def test_create_memory_entry(self):
        """Test creating memory entry."""
        entry = MemoryEntry(
            user_id="user-123",
            conversation_id="conv-456",
            content="User likes coffee",
            memory_type=MemoryType.FACT,
        )
        
        assert entry.user_id == "user-123"
        assert entry.memory_type == MemoryType.FACT
        assert entry.importance == 0.5  # default

    def test_memory_with_importance(self):
        """Test memory with custom importance."""
        entry = MemoryEntry(
            user_id="user-123",
            conversation_id="conv-456",
            content="Important fact",
            memory_type=MemoryType.FACT,
            importance=0.9,
        )
        
        assert entry.importance == 0.9
