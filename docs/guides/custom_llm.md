# Custom LLM Provider Guide

This guide shows how to integrate custom language model providers with bruno-core.

## Overview

Bruno-core uses the `LLMInterface` to abstract language model interactions. You can implement this interface to integrate any LLM provider:

- **Cloud APIs**: OpenAI, Anthropic Claude, Google PaLM, Cohere
- **Self-hosted**: Ollama, LM Studio, text-generation-webui
- **Custom models**: Your own fine-tuned models
- **Hybrid**: Multiple providers with fallback logic

## LLMInterface Contract

```python
from bruno_core.interfaces import LLMInterface
from bruno_core.models import Message
from typing import AsyncIterator

class CustomLLM(LLMInterface):
    async def generate(self, messages: list[Message], **kwargs) -> str:
        """Generate a complete response."""
        raise NotImplementedError
    
    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """Stream response tokens."""
        raise NotImplementedError
    
    def get_token_count(self, text: str) -> int:
        """Estimate token count."""
        raise NotImplementedError
    
    def list_models(self) -> list[str]:
        """List available models."""
        raise NotImplementedError
```

## Basic Implementation

### Simple LLM Provider

```python
import asyncio
from bruno_core.interfaces import LLMInterface
from bruno_core.models import Message, MessageRole

class SimpleLLM(LLMInterface):
    """Minimal LLM implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
    
    async def generate(self, messages: list[Message], **kwargs) -> str:
        # Format messages for your API
        formatted = self._format_messages(messages)
        
        # Make API call
        response = await self._call_api(formatted, **kwargs)
        
        return response
    
    async def stream(self, messages: list[Message], **kwargs):
        formatted = self._format_messages(messages)
        
        async for token in self._stream_api(formatted, **kwargs):
            yield token
    
    def get_token_count(self, text: str) -> int:
        # Simple approximation
        return len(text.split())
    
    def list_models(self) -> list[str]:
        return ["gpt-4", "gpt-3.5-turbo"]
    
    def _format_messages(self, messages: list[Message]) -> list[dict]:
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
    
    async def _call_api(self, messages: list[dict], **kwargs) -> str:
        # Your API call logic here
        pass
    
    async def _stream_api(self, messages: list[dict], **kwargs):
        # Your streaming API call logic here
        yield "token"
```

## Real-World Implementations

### OpenAI Provider

```python
from openai import AsyncOpenAI
from bruno_core.interfaces import LLMInterface
from bruno_core.models import Message

class OpenAILLM(LLMInterface):
    """OpenAI GPT integration."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def generate(self, messages: list[Message], **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ],
            **kwargs
        )
        return response.choices[0].message.content
    
    async def stream(self, messages: list[Message], **kwargs):
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ],
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def get_token_count(self, text: str) -> int:
        import tiktoken
        encoding = tiktoken.encoding_for_model(self.model)
        return len(encoding.encode(text))
    
    def list_models(self) -> list[str]:
        return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
```

### Anthropic Claude Provider

```python
from anthropic import AsyncAnthropic
from bruno_core.interfaces import LLMInterface
from bruno_core.models import Message, MessageRole

class ClaudeLLM(LLMInterface):
    """Anthropic Claude integration."""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
    
    async def generate(self, messages: list[Message], **kwargs) -> str:
        # Separate system message if present
        system = None
        claude_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system = msg.content
            else:
                claude_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        response = await self.client.messages.create(
            model=self.model,
            messages=claude_messages,
            system=system,
            max_tokens=kwargs.get("max_tokens", 1024),
            **kwargs
        )
        
        return response.content[0].text
    
    async def stream(self, messages: list[Message], **kwargs):
        system = None
        claude_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system = msg.content
            else:
                claude_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        async with self.client.messages.stream(
            model=self.model,
            messages=claude_messages,
            system=system,
            max_tokens=kwargs.get("max_tokens", 1024),
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    def get_token_count(self, text: str) -> int:
        # Claude doesn't have a public tokenizer yet
        # Use approximation: ~1 token per 4 characters
        return len(text) // 4
    
    def list_models(self) -> list[str]:
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]
```

### Ollama Local Provider

```python
import aiohttp
from bruno_core.interfaces import LLMInterface
from bruno_core.models import Message

class OllamaLLM(LLMInterface):
    """Ollama local LLM integration."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model
    
    async def generate(self, messages: list[Message], **kwargs) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": msg.role.value, "content": msg.content}
                        for msg in messages
                    ],
                    "stream": False,
                    **kwargs
                }
            ) as response:
                data = await response.json()
                return data["message"]["content"]
    
    async def stream(self, messages: list[Message], **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": msg.role.value, "content": msg.content}
                        for msg in messages
                    ],
                    "stream": True,
                    **kwargs
                }
            ) as response:
                async for line in response.content:
                    if line:
                        import json
                        data = json.loads(line)
                        if "message" in data:
                            yield data["message"]["content"]
    
    def get_token_count(self, text: str) -> int:
        return len(text.split())
    
    def list_models(self) -> list[str]:
        import requests
        response = requests.get(f"{self.base_url}/api/tags")
        return [model["name"] for model in response.json()["models"]]
```

## Advanced Features

### Rate Limiting

```python
import time
import asyncio
from bruno_core.interfaces import LLMInterface

class RateLimitedLLM(LLMInterface):
    """LLM with rate limiting."""
    
    def __init__(self, base_llm: LLMInterface, requests_per_minute: int = 60):
        self.base_llm = base_llm
        self.rpm = requests_per_minute
        self.last_request = 0.0
    
    async def _wait_for_rate_limit(self):
        min_interval = 60.0 / self.rpm
        elapsed = time.time() - self.last_request
        
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        
        self.last_request = time.time()
    
    async def generate(self, messages, **kwargs):
        await self._wait_for_rate_limit()
        return await self.base_llm.generate(messages, **kwargs)
    
    async def stream(self, messages, **kwargs):
        await self._wait_for_rate_limit()
        async for token in self.base_llm.stream(messages, **kwargs):
            yield token
    
    def get_token_count(self, text: str) -> int:
        return self.base_llm.get_token_count(text)
    
    def list_models(self) -> list[str]:
        return self.base_llm.list_models()
```

### Retry Logic

```python
import asyncio
from bruno_core.interfaces import LLMInterface

class RetryLLM(LLMInterface):
    """LLM with automatic retries."""
    
    def __init__(self, base_llm: LLMInterface, max_retries: int = 3):
        self.base_llm = base_llm
        self.max_retries = max_retries
    
    async def generate(self, messages, **kwargs):
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await self.base_llm.generate(messages, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
        
        raise Exception(f"Failed after {self.max_retries} attempts: {last_error}")
    
    async def stream(self, messages, **kwargs):
        async for token in self.base_llm.stream(messages, **kwargs):
            yield token
    
    def get_token_count(self, text: str) -> int:
        return self.base_llm.get_token_count(text)
    
    def list_models(self) -> list[str]:
        return self.base_llm.list_models()
```

### Multi-Provider Fallback

```python
from bruno_core.interfaces import LLMInterface
from typing import List

class FallbackLLM(LLMInterface):
    """Try multiple providers in order."""
    
    def __init__(self, providers: List[LLMInterface]):
        self.providers = providers
    
    async def generate(self, messages, **kwargs):
        last_error = None
        
        for provider in self.providers:
            try:
                return await provider.generate(messages, **kwargs)
            except Exception as e:
                last_error = e
                continue
        
        raise Exception(f"All providers failed. Last error: {last_error}")
    
    async def stream(self, messages, **kwargs):
        for provider in self.providers:
            try:
                async for token in provider.stream(messages, **kwargs):
                    yield token
                return
            except Exception:
                continue
    
    def get_token_count(self, text: str) -> int:
        return self.providers[0].get_token_count(text)
    
    def list_models(self) -> list[str]:
        models = []
        for provider in self.providers:
            models.extend(provider.list_models())
        return list(set(models))
```

## Usage

### Basic Usage

```python
from bruno_core.base import BaseAssistant

# Create LLM
llm = OpenAILLM(api_key="your-key")

# Create assistant
assistant = BaseAssistant(llm=llm, memory=memory)
await assistant.initialize()
```

### With Rate Limiting

```python
base_llm = OpenAILLM(api_key="your-key")
llm = RateLimitedLLM(base_llm, requests_per_minute=30)

assistant = BaseAssistant(llm=llm, memory=memory)
```

### With Fallback

```python
primary = OpenAILLM(api_key="openai-key")
fallback = ClaudeLLM(api_key="claude-key")
local = OllamaLLM()

llm = FallbackLLM([primary, fallback, local])

assistant = BaseAssistant(llm=llm, memory=memory)
```

## Testing

```python
import pytest
from bruno_core.models import Message, MessageRole

@pytest.mark.asyncio
async def test_custom_llm():
    llm = CustomLLM(api_key="test-key")
    
    messages = [
        Message(role=MessageRole.USER, content="Hello")
    ]
    
    response = await llm.generate(messages)
    assert isinstance(response, str)
    assert len(response) > 0
    
    # Test streaming
    tokens = []
    async for token in llm.stream(messages):
        tokens.append(token)
    
    assert len(tokens) > 0
```

## Best Practices

1. **Error Handling**: Always handle API errors gracefully
2. **Rate Limiting**: Implement rate limiting for cloud APIs
3. **Retries**: Add retry logic with exponential backoff
4. **Timeouts**: Set reasonable timeouts for API calls
5. **Token Counting**: Use provider-specific tokenizers when available
6. **Streaming**: Implement streaming for better UX
7. **Context Management**: Handle context window limits
8. **Cost Tracking**: Log token usage for cost monitoring

## Next Steps

- [Memory Backends Guide](./memory_backends.md)
- [Creating Abilities Guide](./creating_abilities.md)
- [API Reference](../api/interfaces.md)
