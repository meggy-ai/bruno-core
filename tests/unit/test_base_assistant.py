"""Tests for BaseAssistant."""

import pytest

from bruno_core.base.assistant import BaseAssistant
from bruno_core.models.message import Message, MessageRole
from tests.conftest import MockAbility, MockLLM, MockMemory


@pytest.mark.asyncio
class TestBaseAssistant:
    """Tests for BaseAssistant class."""

    async def test_initialize(self, mock_llm, mock_memory):
        """Test assistant initialization."""
        assistant = BaseAssistant(
            llm=mock_llm,
            memory=mock_memory,
        )

        await assistant.initialize()
        assert assistant.initialized is True

    async def test_process_message(self, mock_llm, mock_memory):
        """Test processing a message."""
        assistant = BaseAssistant(
            llm=mock_llm,
            memory=mock_memory,
        )
        await assistant.initialize()

        message = Message(
            role=MessageRole.USER,
            content="Hello!",
        )

        response = await assistant.process_message(
            message=message,
            user_id="test-user",
            conversation_id="test-conv",
        )

        assert response is not None
        assert response.success is True
        assert response.text == "Mock response"

    async def test_register_ability(self, mock_llm, mock_memory, mock_ability):
        """Test registering an ability."""
        assistant = BaseAssistant(
            llm=mock_llm,
            memory=mock_memory,
        )
        await assistant.initialize()

        await assistant.register_ability(mock_ability)
        assert "mock" in assistant.abilities

    async def test_unregister_ability(self, mock_llm, mock_memory, mock_ability):
        """Test unregistering an ability."""
        assistant = BaseAssistant(
            llm=mock_llm,
            memory=mock_memory,
        )
        await assistant.initialize()

        await assistant.register_ability(mock_ability)
        await assistant.unregister_ability("mock")
        assert "mock" not in assistant.abilities

    @pytest.mark.skip(reason="WIP: Requires ability detection/NLP implementation")
    async def test_ability_execution(self, mock_llm, mock_memory):
        """Test executing an ability through message processing."""
        # LLM that suggests ability usage
        llm = MockLLM(responses=["Let me help you with that test action"])

        assistant = BaseAssistant(llm=llm, memory=mock_memory)
        await assistant.initialize()

        # Register ability with 'test' keyword
        ability = MockAbility(name="tester", actions=["test"])
        await assistant.register_ability(ability)

        message = Message(
            role=MessageRole.USER,
            content="Please run a test",
        )

        response = await assistant.process_message(
            message=message,
            user_id="test-user",
            conversation_id="test-conv",
        )

        # Should detect 'test' keyword and execute ability
        assert response.success is True
        assert len(ability.executed_requests) > 0

    async def test_shutdown(self, mock_llm, mock_memory):
        """Test assistant shutdown."""
        assistant = BaseAssistant(
            llm=mock_llm,
            memory=mock_memory,
        )
        await assistant.initialize()
        await assistant.shutdown()

        assert assistant.initialized is False

    async def test_health_check(self, mock_llm, mock_memory):
        """Test health check."""
        assistant = BaseAssistant(
            llm=mock_llm,
            memory=mock_memory,
        )
        await assistant.initialize()

        health = await assistant.health_check()
        assert health["status"] == "healthy"
        assert health["abilities_count"] == 0

    async def test_multiple_messages(self, mock_llm, mock_memory):
        """Test processing multiple messages."""
        assistant = BaseAssistant(
            llm=mock_llm,
            memory=mock_memory,
        )
        await assistant.initialize()

        messages = [
            Message(role=MessageRole.USER, content="First"),
            Message(role=MessageRole.USER, content="Second"),
            Message(role=MessageRole.USER, content="Third"),
        ]

        for msg in messages:
            response = await assistant.process_message(
                message=msg,
                user_id="test-user",
                conversation_id="test-conv",
            )
            assert response.success is True

        # Check that LLM was called 3 times
        assert mock_llm.call_count == 3
