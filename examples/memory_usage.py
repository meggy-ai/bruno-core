"""
Memory Usage Example

Demonstrates different memory backend patterns and usage.
"""

import asyncio

# Use mock LLM from basic_assistant
import sys
from datetime import datetime
from typing import Optional

from bruno_core.base import BaseAssistant
from bruno_core.interfaces import EmbeddingInterface, MemoryInterface
from bruno_core.models import MemoryEntry, Message, MessageRole

sys.path.append(".")
from examples.basic_assistant import MockLLM


class SimpleMemory(MemoryInterface):
    """Simple in-memory storage with message history."""

    def __init__(self):
        self.storage = {}  # {user_id: {conversation_id: [messages]}}
        self.stats = {"stores": 0, "retrievals": 0}

    async def store_message(self, message: Message, user_id: str, conversation_id: str):
        """Store a message."""
        if user_id not in self.storage:
            self.storage[user_id] = {}

        if conversation_id not in self.storage[user_id]:
            self.storage[user_id][conversation_id] = []

        self.storage[user_id][conversation_id].append(message)
        self.stats["stores"] += 1
        print(f"💾 Stored message (user={user_id}, conv={conversation_id})")

    async def retrieve_context(
        self, user_id: str, query: str, limit: int = 10, conversation_id: Optional[str] = None
    ) -> list[Message]:
        """Retrieve recent messages."""
        self.stats["retrievals"] += 1

        if user_id not in self.storage:
            return []

        if conversation_id:
            messages = self.storage[user_id].get(conversation_id, [])
        else:
            # Get from all conversations
            messages = []
            for conv_messages in self.storage[user_id].values():
                messages.extend(conv_messages)

        return messages[-limit:]

    async def search_memories(self, user_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Search for relevant memories."""
        # Simple keyword search
        results = []

        if user_id in self.storage:
            for conv_id, messages in self.storage[user_id].items():
                for msg in messages:
                    if query.lower() in msg.content.lower():
                        entry = MemoryEntry(
                            id=f"{user_id}:{conv_id}:{msg.timestamp}",
                            user_id=user_id,
                            content=msg.content,
                            metadata={"conversation_id": conv_id},
                            timestamp=msg.timestamp,
                        )
                        results.append(entry)

        return results[:limit]

    async def clear_conversation(self, user_id: str, conversation_id: str):
        """Clear a conversation."""
        if user_id in self.storage and conversation_id in self.storage[user_id]:
            del self.storage[user_id][conversation_id]
            print(f"🗑️  Cleared conversation {conversation_id}")


class SemanticMemory(MemoryInterface):
    """
    Memory backend with semantic search capabilities.

    In a real implementation, this would use:
    - Vector embeddings (OpenAI, Sentence Transformers, etc.)
    - Vector database (Pinecone, Weaviate, ChromaDB, etc.)
    - Similarity search
    """

    def __init__(self, embedding_model: Optional[EmbeddingInterface] = None):
        self.embedding_model = embedding_model
        self.messages = []
        self.embeddings = []  # Would store actual embeddings

    async def store_message(self, message: Message, user_id: str, conversation_id: str):
        """Store message with embedding."""
        # In a real implementation:
        # 1. Generate embedding for message content
        # 2. Store in vector database with metadata

        entry = {
            "message": message,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(),
        }
        self.messages.append(entry)

        # Simulate embedding generation
        if self.embedding_model:
            # embedding = await self.embedding_model.embed(message.content)
            # self.embeddings.append(embedding)
            pass

        print(f"🧠 Stored message with semantic indexing")

    async def retrieve_context(
        self, user_id: str, query: str, limit: int = 10, conversation_id: Optional[str] = None
    ) -> list[Message]:
        """Retrieve semantically similar context."""
        # In a real implementation:
        # 1. Generate embedding for query
        # 2. Search vector database for similar embeddings
        # 3. Return messages sorted by similarity

        # For demo, return recent messages
        filtered = [
            entry["message"]
            for entry in self.messages
            if entry["user_id"] == user_id
            and (conversation_id is None or entry["conversation_id"] == conversation_id)
        ]

        return filtered[-limit:]

    async def search_memories(self, user_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Search using semantic similarity."""
        # In a real implementation:
        # 1. Embed the query
        # 2. Find top-k similar memories
        # 3. Return with similarity scores

        results = []
        for entry in self.messages:
            if entry["user_id"] == user_id:
                memory = MemoryEntry(
                    id=f"{entry['user_id']}:{entry['timestamp']}",
                    user_id=entry["user_id"],
                    content=entry["message"].content,
                    metadata={"conversation_id": entry["conversation_id"]},
                    timestamp=entry["timestamp"],
                )
                results.append(memory)

        return results[:limit]

    async def clear_conversation(self, user_id: str, conversation_id: str):
        """Clear conversation from vector store."""
        self.messages = [
            entry
            for entry in self.messages
            if not (entry["user_id"] == user_id and entry["conversation_id"] == conversation_id)
        ]


async def test_simple_memory():
    """Test simple memory backend."""
    print("1️⃣  Testing Simple Memory Backend")
    print("=" * 60)

    memory = SimpleMemory()
    llm = MockLLM()
    assistant = BaseAssistant(llm=llm, memory=memory)
    await assistant.initialize()

    user_id = "alice"
    conv_id = "conv_001"

    # Have a conversation
    messages = [
        "My favorite color is blue",
        "I like pizza",
        "I work as a software engineer",
    ]

    for msg_text in messages:
        msg = Message(role=MessageRole.USER, content=msg_text)
        await assistant.process_message(msg, user_id, conv_id)

    # Retrieve context
    print("\n📚 Retrieving conversation context...")
    context = await memory.retrieve_context(user_id, "", conversation_id=conv_id)
    print(f"   Found {len(context)} messages")
    for i, msg in enumerate(context, 1):
        print(f"   {i}. {msg.content}")

    # Search memories
    print("\n🔍 Searching for 'pizza'...")
    results = await memory.search_memories(user_id, "pizza")
    for result in results:
        print(f"   - {result.content}")

    # Stats
    print(f"\n📊 Memory stats:")
    print(f"   Stores: {memory.stats['stores']}")
    print(f"   Retrievals: {memory.stats['retrievals']}")

    await assistant.shutdown()


async def test_semantic_memory():
    """Test semantic memory backend."""
    print("\n\n2️⃣  Testing Semantic Memory Backend")
    print("=" * 60)

    memory = SemanticMemory()
    llm = MockLLM()
    assistant = BaseAssistant(llm=llm, memory=memory)
    await assistant.initialize()

    user_id = "bob"
    conv_id = "conv_002"

    # Store messages with different topics
    messages = [
        "I love machine learning and AI",
        "Neural networks are fascinating",
        "I enjoy hiking on weekends",
        "Deep learning requires lots of data",
        "Mountains are beautiful this time of year",
    ]

    print("\n💾 Storing messages with semantic indexing...")
    for msg_text in messages:
        msg = Message(role=MessageRole.USER, content=msg_text)
        await memory.store_message(msg, user_id, conv_id)

    # In a real implementation with embeddings, semantic search would
    # find related messages even without exact keyword matches
    print("\n🔍 Semantic search for 'AI and machine learning'...")
    results = await memory.search_memories(user_id, "AI")
    print(f"   Found {len(results)} related memories")
    for result in results:
        print(f"   - {result.content}")

    await assistant.shutdown()


async def test_memory_management():
    """Test memory management operations."""
    print("\n\n3️⃣  Testing Memory Management")
    print("=" * 60)

    memory = SimpleMemory()
    llm = MockLLM()
    assistant = BaseAssistant(llm=llm, memory=memory)
    await assistant.initialize()

    user_id = "charlie"

    # Create multiple conversations
    conversations = {
        "work": ["Let's discuss the project", "The deadline is next week"],
        "personal": ["Weekend plans?", "Let's meet for lunch"],
        "support": ["I need help with the app", "How do I reset my password?"],
    }

    print("\n💾 Creating multiple conversations...")
    for conv_id, messages in conversations.items():
        for msg_text in messages:
            msg = Message(role=MessageRole.USER, content=msg_text)
            await memory.store_message(msg, user_id, conv_id)
        print(f"   ✅ Created conversation: {conv_id} ({len(messages)} messages)")

    # Retrieve from specific conversation
    print("\n📚 Retrieving from 'work' conversation...")
    work_context = await memory.retrieve_context(user_id, "", conversation_id="work")
    for msg in work_context:
        print(f"   - {msg.content}")

    # Retrieve from all conversations
    print("\n📚 Retrieving from all conversations...")
    all_context = await memory.retrieve_context(user_id, "", limit=10)
    print(f"   Total messages: {len(all_context)}")

    # Clear a conversation
    print("\n🗑️  Clearing 'support' conversation...")
    await memory.clear_conversation(user_id, "support")

    # Verify
    remaining = await memory.retrieve_context(user_id, "", limit=100)
    print(f"   Remaining messages: {len(remaining)}")

    await assistant.shutdown()


async def main():
    """Run all memory examples."""
    print("🤖 Bruno Core - Memory Usage Examples")
    print("=" * 60)

    await test_simple_memory()
    await test_semantic_memory()
    await test_memory_management()

    print("\n\n✅ All memory examples completed!")
    print("\n💡 Key Takeaways:")
    print("   - Choose memory backend based on your needs")
    print("   - Simple in-memory for development/testing")
    print("   - Semantic memory for production with search")
    print("   - Implement clear_conversation for privacy")
    print("   - Track usage statistics for monitoring")


if __name__ == "__main__":
    asyncio.run(main())
