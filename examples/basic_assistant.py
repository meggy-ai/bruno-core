"""
Basic Assistant Example

Demonstrates the simplest possible bruno-core assistant setup.
"""

import asyncio
from bruno_core.base import BaseAssistant
from bruno_core.models import Message, MessageRole
from bruno_core.interfaces import LLMInterface, MemoryInterface


# Mock LLM for demo purposes
class MockLLM(LLMInterface):
    """Simple mock LLM that echoes back."""
    
    async def generate(self, messages: list[Message], **kwargs) -> str:
        last_message = messages[-1].content if messages else "Hello"
        return f"You said: {last_message}. How can I help you?"
    
    async def stream(self, messages: list[Message], **kwargs):
        response = await self.generate(messages, **kwargs)
        for char in response:
            yield char
            await asyncio.sleep(0.01)  # Simulate streaming
    
    def get_token_count(self, text: str) -> int:
        return len(text.split())
    
    def list_models(self) -> list[str]:
        return ["mock-model-1"]


# Mock Memory for demo purposes
class MockMemory(MemoryInterface):
    """Simple in-memory storage."""
    
    def __init__(self):
        self.messages = {}
    
    async def store_message(self, message: Message, user_id: str, conversation_id: str):
        key = f"{user_id}:{conversation_id}"
        if key not in self.messages:
            self.messages[key] = []
        self.messages[key].append(message)
        print(f"📝 Stored message in memory (total: {len(self.messages[key])})")
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        conversation_id: str = None
    ):
        key = f"{user_id}:{conversation_id}" if conversation_id else user_id
        messages = self.messages.get(key, [])
        return messages[-limit:]
    
    async def search_memories(self, user_id: str, query: str, limit: int = 5):
        return []
    
    async def clear_conversation(self, user_id: str, conversation_id: str):
        key = f"{user_id}:{conversation_id}"
        self.messages.pop(key, None)


async def main():
    """Run basic assistant demo."""
    
    print("🤖 Bruno Core - Basic Assistant Example")
    print("=" * 50)
    
    # Initialize components
    print("\n1️⃣  Initializing LLM and Memory...")
    llm = MockLLM()
    memory = MockMemory()
    
    # Create assistant
    print("2️⃣  Creating assistant...")
    assistant = BaseAssistant(llm=llm, memory=memory)
    await assistant.initialize()
    print("✅ Assistant initialized!")
    
    # Simulate a conversation
    user_id = "demo-user"
    conversation_id = "demo-conversation"
    
    messages_to_send = [
        "Hello, how are you?",
        "What's the weather like?",
        "Tell me a joke",
    ]
    
    print(f"\n3️⃣  Starting conversation (user={user_id})...")
    print("=" * 50)
    
    for user_input in messages_to_send:
        print(f"\n👤 User: {user_input}")
        
        # Create message
        message = Message(
            role=MessageRole.USER,
            content=user_input
        )
        
        # Process message
        response = await assistant.process_message(
            message=message,
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        # Display response
        if response.success:
            print(f"🤖 Assistant: {response.text}")
        else:
            print(f"❌ Error: {response.error}")
    
    # Get statistics
    print("\n" + "=" * 50)
    print("4️⃣  Conversation Statistics:")
    print(f"   Total messages stored: {len(memory.messages.get(f'{user_id}:{conversation_id}', []))}")
    
    health = await assistant.health_check()
    print(f"   Assistant status: {health['status']}")
    print(f"   Registered abilities: {health['abilities_count']}")
    
    # Cleanup
    print("\n5️⃣  Shutting down...")
    await assistant.shutdown()
    print("✅ Cleanup complete!")


if __name__ == "__main__":
    asyncio.run(main())
