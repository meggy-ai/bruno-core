"""
LLM Interface - Language model integration contract.

Defines the contract for LLM providers (OpenAI, Claude, Ollama, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from bruno_core.models.message import Message


class LLMInterface(ABC):
    """
    Abstract interface for Language Model providers.

    All LLM implementations (OpenAI, Claude, Ollama, etc.) must implement
    this interface to ensure consistent behavior.

    Example:
        >>> class OllamaClient(LLMInterface):
        ...     async def generate(self, messages, **kwargs):
        ...         # Implementation
        ...         pass
    """

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate a text response from the LLM.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            Generated text response

        Raises:
            LLMError: If generation fails

        Example:
            >>> messages = [Message(role="user", content="Hello")]
            >>> response = await llm.generate(messages, temperature=0.7)
            >>> print(response)
            "Hello! How can I help you today?"
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream text response from the LLM.

        Yields text chunks as they are generated.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Yields:
            Text chunks as they arrive

        Raises:
            LLMError: If streaming fails

        Example:
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk, end='', flush=True)
        """
        pass

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """
        Estimate token count for given text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count

        Example:
            >>> count = llm.get_token_count("Hello world")
            >>> print(count)
            2
        """
        pass

    @abstractmethod
    async def check_connection(self) -> bool:
        """
        Check if LLM service is accessible.

        Returns:
            True if connected, False otherwise

        Example:
            >>> is_connected = await llm.check_connection()
            >>> print(is_connected)
            True
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        List available models from the provider.

        Returns:
            List of model names/identifiers

        Example:
            >>> models = await llm.list_models()
            >>> print(models)
            ['gpt-4', 'gpt-3.5-turbo']
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dict with model information

        Example:
            >>> info = llm.get_model_info()
            >>> print(info)
            {'model': 'gpt-4', 'max_tokens': 8192, 'provider': 'openai'}
        """
        pass

    @abstractmethod
    def set_system_prompt(self, prompt: str) -> None:
        """
        Set or update the system prompt.

        Args:
            prompt: System prompt text

        Example:
            >>> llm.set_system_prompt("You are a helpful assistant named Bruno.")
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> Optional[str]:
        """
        Get the current system prompt.

        Returns:
            Current system prompt or None

        Example:
            >>> prompt = llm.get_system_prompt()
            >>> print(prompt)
            "You are a helpful assistant."
        """
        pass
