"""
Custom LLM Example

Demonstrates how to implement a custom LLM provider.
"""

import asyncio
from typing import AsyncIterator
from bruno_core.base import BaseAssistant
from bruno_core.interfaces import LLMInterface
from bruno_core.models import Message, MessageRole

# For this example, we'll use mock memory from basic_assistant
import sys
sys.path.append('.')
from examples.basic_assistant import MockMemory


class CustomLLM(LLMInterface):
    """
    Example custom LLM implementation.
    
    In a real implementation, this would connect to your LLM service
    (OpenAI, Claude, Ollama, etc.) and handle API calls, rate limiting,
    error handling, etc.
    """
    
    def __init__(self, model_name: str = "custom-model", api_key: str = None):
        """
        Initialize the custom LLM.
        
        Args:
            model_name: The model to use
            api_key: API key for authentication
        """
        self.model_name = model_name
        self.api_key = api_key
        self._initialized = False
        self._request_count = 0
    
    async def generate(self, messages: list[Message], **kwargs) -> str:
        """
        Generate a response from the LLM.
        
        In a real implementation, this would:
        1. Format messages for your LLM's API
        2. Make the API call
        3. Handle errors and retries
        4. Return the response text
        """
        self._request_count += 1
        
        # Simulate processing
        await asyncio.sleep(0.1)
        
        # Extract the last user message
        last_message = next(
            (msg.content for msg in reversed(messages) if msg.role == MessageRole.USER),
            "Hello"
        )
        
        # Generate a response based on the message
        if "weather" in last_message.lower():
            response = "I don't have real-time weather data, but I can tell you it's always sunny in the digital world! 🌞"
        elif "joke" in last_message.lower():
            response = "Why did the Python programmer not respond to the function call? Because they were lost in recursion! 😄"
        elif "calculate" in last_message.lower() or "math" in last_message.lower():
            response = "I can help with calculations! Please provide the specific math problem you'd like me to solve."
        else:
            response = f"I received your message: '{last_message}'. This is a custom LLM response from {self.model_name}!"
        
        return response
    
    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """
        Stream a response token by token.
        
        In a real implementation, this would:
        1. Make a streaming API call
        2. Yield tokens as they arrive
        3. Handle connection errors
        """
        response = await self.generate(messages, **kwargs)
        
        # Simulate streaming by yielding character by character
        for char in response:
            yield char
            await asyncio.sleep(0.02)  # Simulate network latency
    
    def get_token_count(self, text: str) -> int:
        """
        Estimate token count for the text.
        
        In a real implementation, this would use your LLM's
        tokenizer (e.g., tiktoken for OpenAI).
        """
        # Simple approximation: ~1 token per 4 characters
        return len(text) // 4
    
    def list_models(self) -> list[str]:
        """List available models."""
        return [
            "custom-model-small",
            "custom-model-medium",
            "custom-model-large",
        ]


class AdvancedCustomLLM(LLMInterface):
    """
    More advanced custom LLM with additional features.
    
    Demonstrates:
    - Rate limiting
    - Context management
    - Error handling
    - Retry logic
    """
    
    def __init__(
        self,
        model_name: str = "advanced-model",
        max_retries: int = 3,
        timeout: float = 30.0,
        rate_limit: int = 60,  # requests per minute
    ):
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout = timeout
        self.rate_limit = rate_limit
        
        self._request_count = 0
        self._last_request_time = 0.0
        self._error_count = 0
    
    async def _check_rate_limit(self):
        """Check if we're within rate limits."""
        import time
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        # Simple rate limiting: wait if needed
        min_interval = 60.0 / self.rate_limit
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    async def _make_request_with_retry(self, messages: list[Message]) -> str:
        """Make a request with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Check rate limits
                await self._check_rate_limit()
                
                # Simulate API call
                await asyncio.sleep(0.1)
                self._request_count += 1
                
                # Extract last message
                last_message = next(
                    (msg.content for msg in reversed(messages) if msg.role == MessageRole.USER),
                    "Hello"
                )
                
                return f"[{self.model_name}] Response to: {last_message}"
            
            except Exception as e:
                last_error = e
                self._error_count += 1
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
        
        raise Exception(f"Failed after {self.max_retries} attempts: {last_error}")
    
    async def generate(self, messages: list[Message], **kwargs) -> str:
        """Generate with error handling and retries."""
        return await self._make_request_with_retry(messages)
    
    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """Stream response."""
        response = await self.generate(messages, **kwargs)
        for char in response:
            yield char
            await asyncio.sleep(0.01)
    
    def get_token_count(self, text: str) -> int:
        """Estimate tokens."""
        return len(text) // 4
    
    def list_models(self) -> list[str]:
        """List models."""
        return ["advanced-model-v1", "advanced-model-v2"]
    
    def get_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate": self._error_count / max(self._request_count, 1),
        }


async def main():
    """Demo custom LLM implementations."""
    
    print("🤖 Bruno Core - Custom LLM Example")
    print("=" * 60)
    
    # Test basic custom LLM
    print("\n1️⃣  Testing Basic Custom LLM")
    print("-" * 60)
    
    llm = CustomLLM(model_name="demo-model-v1")
    memory = MockMemory()
    assistant = BaseAssistant(llm=llm, memory=memory)
    await assistant.initialize()
    
    test_messages = [
        "Hello, how are you?",
        "What's the weather like today?",
        "Tell me a joke!",
    ]
    
    for msg_text in test_messages:
        print(f"\n👤 User: {msg_text}")
        
        message = Message(role=MessageRole.USER, content=msg_text)
        response = await assistant.process_message(
            message=message,
            user_id="demo-user",
            conversation_id="demo-conv"
        )
        
        print(f"🤖 Assistant: {response.text}")
        print(f"📊 Tokens: ~{llm.get_token_count(response.text)}")
    
    print(f"\n📈 Total requests: {llm._request_count}")
    
    await assistant.shutdown()
    
    # Test streaming
    print("\n\n2️⃣  Testing Streaming Response")
    print("-" * 60)
    
    llm2 = CustomLLM(model_name="demo-model-stream")
    messages = [Message(role=MessageRole.USER, content="Tell me about Python")]
    
    print("👤 User: Tell me about Python")
    print("🤖 Assistant: ", end="", flush=True)
    
    async for token in llm2.stream(messages):
        print(token, end="", flush=True)
    
    print()  # New line after streaming
    
    # Test advanced LLM
    print("\n\n3️⃣  Testing Advanced Custom LLM (with rate limiting)")
    print("-" * 60)
    
    advanced_llm = AdvancedCustomLLM(
        model_name="advanced-demo",
        rate_limit=10,  # 10 requests per minute
        max_retries=2
    )
    
    memory2 = MockMemory()
    assistant2 = BaseAssistant(llm=advanced_llm, memory=memory2)
    await assistant2.initialize()
    
    print("\nSending multiple rapid requests to test rate limiting...")
    
    for i in range(3):
        msg = Message(role=MessageRole.USER, content=f"Test message {i+1}")
        print(f"\n👤 Request {i+1}")
        
        import time
        start = time.time()
        response = await assistant2.process_message(
            message=msg,
            user_id="demo-user",
            conversation_id="demo-conv"
        )
        elapsed = time.time() - start
        
        print(f"🤖 Response: {response.text[:50]}...")
        print(f"⏱️  Time: {elapsed:.3f}s")
    
    # Show stats
    stats = advanced_llm.get_stats()
    print(f"\n📊 Advanced LLM Statistics:")
    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Total errors: {stats['total_errors']}")
    print(f"   Error rate: {stats['error_rate']:.2%}")
    
    await assistant2.shutdown()
    
    # Show available models
    print("\n\n4️⃣  Available Models")
    print("-" * 60)
    
    print("Basic LLM models:")
    for model in llm.list_models():
        print(f"   - {model}")
    
    print("\nAdvanced LLM models:")
    for model in advanced_llm.list_models():
        print(f"   - {model}")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
