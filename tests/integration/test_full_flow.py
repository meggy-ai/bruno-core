"""Integration tests for full workflow."""

import pytest

from bruno_core.base.assistant import BaseAssistant
from bruno_core.models.message import Message, MessageRole
from tests.conftest import MockAbility, MockLLM, MockMemory


@pytest.mark.asyncio
class TestFullWorkflow:
    """Integration tests for complete workflows."""

    @pytest.mark.skip(reason="WIP: Requires memory retrieval implementation")
    async def test_basic_conversation_flow(self):
        """Test basic conversation flow."""
        llm = MockLLM(
            responses=[
                "Hello! How can I help you?",
                "The answer is 42.",
                "Goodbye!",
            ]
        )
        memory = MockMemory()

        assistant = BaseAssistant(llm=llm, memory=memory)
        await assistant.initialize()

        # First message
        msg1 = Message(role=MessageRole.USER, content="Hi there")
        response1 = await assistant.process_message(
            message=msg1,
            user_id="user-123",
            conversation_id="conv-123",
        )

        assert response1.success is True
        assert response1.text == "Hello! How can I help you?"

        # Second message
        msg2 = Message(role=MessageRole.USER, content="What is the meaning of life?")
        response2 = await assistant.process_message(
            message=msg2,
            user_id="user-123",
            conversation_id="conv-123",
        )

        assert response2.success is True
        assert response2.text == "The answer is 42."

        # Check memory has both messages
        stored = await memory.retrieve_context(
            user_id="user-123",
            conversation_id="conv-123",
            query="",
        )
        assert len(stored) >= 2

    @pytest.mark.skip(reason="WIP: Requires ability detection/NLP implementation")
    async def test_ability_integration(self):
        """Test ability integration in workflow."""
        llm = MockLLM(responses=["I'll test that for you"])
        memory = MockMemory()

        assistant = BaseAssistant(llm=llm, memory=memory)
        await assistant.initialize()

        # Register ability
        ability = MockAbility(name="tester", actions=["test", "verify"])
        await assistant.register_ability(ability)

        # Send message that triggers ability
        msg = Message(role=MessageRole.USER, content="Please run a test")
        response = await assistant.process_message(
            message=msg,
            user_id="user-123",
            conversation_id="conv-123",
        )

        assert response.success is True
        # Ability should have been executed
        assert len(ability.executed_requests) > 0

    @pytest.mark.skip(reason="WIP: Requires memory context retrieval implementation")
    async def test_multi_user_isolation(self):
        """Test that different users have isolated contexts."""
        llm = MockLLM()
        memory = MockMemory()

        assistant = BaseAssistant(llm=llm, memory=memory)
        await assistant.initialize()

        # User 1 sends message
        msg1 = Message(role=MessageRole.USER, content="Hello from user 1")
        await assistant.process_message(
            message=msg1,
            user_id="user-1",
            conversation_id="conv-1",
        )

        # User 2 sends message
        msg2 = Message(role=MessageRole.USER, content="Hello from user 2")
        await assistant.process_message(
            message=msg2,
            user_id="user-2",
            conversation_id="conv-2",
        )

        # Check memory isolation
        user1_msgs = await memory.retrieve_context(
            user_id="user-1",
            conversation_id="conv-1",
            query="",
        )
        user2_msgs = await memory.retrieve_context(
            user_id="user-2",
            conversation_id="conv-2",
            query="",
        )

        # Each user should only see their own messages
        assert len(user1_msgs) > 0
        assert len(user2_msgs) > 0
        assert user1_msgs != user2_msgs

    @pytest.mark.skip(reason="WIP: Requires proper error recovery handling in assistant")
    async def test_error_recovery(self):
        """Test error recovery in workflow."""

        class FailingLLM(MockLLM):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            async def generate(self, messages, model="mock", temperature=0.7, max_tokens=1000):
                self.call_count += 1
                if self.call_count == 1:
                    raise Exception("LLM temporarily unavailable")
                return "Recovered response"

        llm = FailingLLM()
        memory = MockMemory()

        assistant = BaseAssistant(llm=llm, memory=memory)
        await assistant.initialize()

        # First call should fail
        msg1 = Message(role=MessageRole.USER, content="Test")
        response1 = await assistant.process_message(
            message=msg1,
            user_id="user-123",
            conversation_id="conv-123",
        )

        assert response1.success is False

        # Second call should succeed
        msg2 = Message(role=MessageRole.USER, content="Test again")
        response2 = await assistant.process_message(
            message=msg2,
            user_id="user-123",
            conversation_id="conv-123",
        )

        assert response2.success is True
        assert response2.text == "Recovered response"

    async def test_multiple_abilities_coordination(self):
        """Test coordination between multiple abilities."""
        llm = MockLLM()
        memory = MockMemory()

        assistant = BaseAssistant(llm=llm, memory=memory)
        await assistant.initialize()

        # Register multiple abilities
        ability1 = MockAbility(name="ability1", actions=["action1"])
        ability2 = MockAbility(name="ability2", actions=["action2"])

        await assistant.register_ability(ability1)
        await assistant.register_ability(ability2)

        assert len(assistant.abilities) == 2
        assert "ability1" in assistant.abilities
        assert "ability2" in assistant.abilities
