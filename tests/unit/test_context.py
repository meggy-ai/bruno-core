"""Tests for context management."""

import pytest

from bruno_core.context.manager import ContextManager
from bruno_core.context.session import SessionManager
from bruno_core.context.state import StateManager
from bruno_core.models.message import Message, MessageRole
from tests.conftest import MockMemory


@pytest.mark.asyncio
class TestContextManager:
    """Tests for ContextManager."""

    async def test_add_message(self):
        """Test adding message to context."""
        memory = MockMemory()
        manager = ContextManager(memory=memory, max_messages=5)
        
        message = Message(role=MessageRole.USER, content="Hello")
        await manager.add_message(
            message=message,
            conversation_id="conv-123",
            user_id="user-123",
        )
        
        assert manager.get_buffer_size("conv-123") == 1

    async def test_rolling_window(self):
        """Test rolling window behavior."""
        memory = MockMemory()
        manager = ContextManager(memory=memory, max_messages=3)
        
        for i in range(5):
            message = Message(role=MessageRole.USER, content=f"Message {i}")
            await manager.add_message(
                message=message,
                conversation_id="conv-123",
                user_id="user-123",
            )
        
        # Should only keep last 3 messages
        assert manager.get_buffer_size("conv-123") == 3

    async def test_get_context(self):
        """Test getting conversation context."""
        memory = MockMemory()
        manager = ContextManager(memory=memory)
        
        message = Message(role=MessageRole.USER, content="Test")
        await manager.add_message(
            message=message,
            conversation_id="conv-123",
            user_id="user-123",
        )
        
        context = await manager.get_context(
            conversation_id="conv-123",
            user_id="user-123",
        )
        
        assert context.conversation_id == "conv-123"
        assert len(context.messages) == 1

    async def test_clear_context(self):
        """Test clearing context."""
        memory = MockMemory()
        manager = ContextManager(memory=memory)
        
        message = Message(role=MessageRole.USER, content="Test")
        await manager.add_message(
            message=message,
            conversation_id="conv-123",
        )
        
        await manager.clear_context("conv-123")
        assert manager.get_buffer_size("conv-123") == 0

    async def test_get_statistics(self):
        """Test getting statistics."""
        memory = MockMemory()
        manager = ContextManager(memory=memory)
        
        message = Message(role=MessageRole.USER, content="Test")
        await manager.add_message(
            message=message,
            conversation_id="conv-123",
        )
        
        stats = manager.get_statistics()
        assert stats["active_conversations"] == 1
        assert stats["total_buffered_messages"] == 1


@pytest.mark.asyncio
class TestSessionManager:
    """Tests for SessionManager."""

    async def test_start_session(self):
        """Test starting a session."""
        manager = SessionManager()
        
        session = await manager.start_session(user_id="user-123")
        
        assert session.session_id is not None
        assert session.user_id == "user-123"
        assert session.active is True

    async def test_get_session(self):
        """Test getting a session."""
        manager = SessionManager()
        
        session = await manager.start_session(user_id="user-123")
        retrieved = await manager.get_session(session.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    async def test_update_session(self):
        """Test updating session."""
        manager = SessionManager()
        
        session = await manager.start_session(user_id="user-123")
        await manager.update_session(
            session.session_id,
            metadata={"updated": True},
        )
        
        updated = await manager.get_session(session.session_id)
        assert updated.metadata["updated"] is True

    async def test_end_session(self):
        """Test ending a session."""
        manager = SessionManager()
        
        session = await manager.start_session(user_id="user-123")
        await manager.end_session(session.session_id)
        
        # Session should be removed
        ended = await manager.get_session(session.session_id)
        assert ended is None

    async def test_list_active_sessions(self):
        """Test listing active sessions."""
        manager = SessionManager()
        
        await manager.start_session(user_id="user-1")
        await manager.start_session(user_id="user-2")
        
        active = manager.list_active_sessions()
        assert len(active) == 2

    async def test_session_statistics(self):
        """Test session statistics."""
        manager = SessionManager()
        
        await manager.start_session(user_id="user-123")
        
        stats = manager.get_statistics()
        assert stats["active_sessions"] == 1


@pytest.mark.asyncio
class TestStateManager:
    """Tests for StateManager."""

    async def test_set_and_get_state(self):
        """Test setting and getting state."""
        manager = StateManager(use_memory=True)
        
        await manager.set_state("user-123", "preference", {"theme": "dark"})
        value = await manager.get_state("user-123", "preference")
        
        assert value["theme"] == "dark"

    async def test_get_nonexistent_state(self):
        """Test getting nonexistent state."""
        manager = StateManager(use_memory=True)
        
        value = await manager.get_state("user-123", "missing", default="default")
        assert value == "default"

    async def test_delete_state(self):
        """Test deleting state."""
        manager = StateManager(use_memory=True)
        
        await manager.set_state("user-123", "test", "value")
        deleted = await manager.delete_state("user-123", "test")
        
        assert deleted is True
        value = await manager.get_state("user-123", "test")
        assert value is None

    async def test_list_keys(self):
        """Test listing keys in namespace."""
        manager = StateManager(use_memory=True)
        
        await manager.set_state("user-123", "key1", "value1")
        await manager.set_state("user-123", "key2", "value2")
        
        keys = await manager.list_keys("user-123")
        assert len(keys) == 2
        assert "key1" in keys
        assert "key2" in keys

    async def test_clear_namespace(self):
        """Test clearing namespace."""
        manager = StateManager(use_memory=True)
        
        await manager.set_state("user-123", "key1", "value1")
        await manager.set_state("user-123", "key2", "value2")
        
        count = await manager.clear_namespace("user-123")
        assert count == 2
        
        keys = await manager.list_keys("user-123")
        assert len(keys) == 0
