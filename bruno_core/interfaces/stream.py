"""
Stream Interface - Streaming response contract.

Defines the contract for streaming text generation.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional

from bruno_core.models.response import StreamResponse


class StreamInterface(ABC):
    """
    Abstract interface for streaming responses.

    Enables real-time streaming of LLM responses to users.

    Example:
        >>> class MyStream(StreamInterface):
        ...     async def stream_response(self, messages):
        ...         # Implementation
        ...         pass
    """

    @abstractmethod
    async def stream_response(
        self,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[StreamResponse]:
        """
        Stream response chunks.

        Args:
            prompt: Prompt to generate response for
            metadata: Optional metadata

        Yields:
            StreamResponse chunks

        Raises:
            StreamError: If streaming fails

        Example:
            >>> async for chunk in stream.stream_response("Hello"):
            ...     print(chunk.chunk, end='', flush=True)
        """
        pass

    @abstractmethod
    async def start_stream(self) -> None:
        """
        Initialize streaming connection.

        Raises:
            StreamError: If initialization fails

        Example:
            >>> await stream.start_stream()
        """
        pass

    @abstractmethod
    async def end_stream(self) -> None:
        """
        Close streaming connection.

        Example:
            >>> await stream.end_stream()
        """
        pass

    @abstractmethod
    def is_streaming(self) -> bool:
        """
        Check if currently streaming.

        Returns:
            True if streaming is active

        Example:
            >>> is_active = stream.is_streaming()
        """
        pass

    @abstractmethod
    async def cancel_stream(self) -> None:
        """
        Cancel ongoing stream.

        Example:
            >>> await stream.cancel_stream()
        """
        pass

    def supports_metadata(self) -> bool:
        """
        Check if stream supports metadata.

        Returns:
            True if metadata is supported

        Example:
            >>> supports = stream.supports_metadata()
        """
        return False
