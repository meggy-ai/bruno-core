"""
Runtime-checkable protocols for bruno-core interfaces.

Protocols provide structural subtyping (duck typing) with type safety.
They allow classes to be compatible without explicit inheritance.
"""

from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, runtime_checkable

from bruno_core.models.ability import AbilityMetadata, AbilityRequest, AbilityResponse
from bruno_core.models.context import ConversationContext, SessionContext
from bruno_core.models.memory import MemoryEntry, MemoryQuery
from bruno_core.models.message import Message
from bruno_core.models.response import AssistantResponse, StreamResponse


@runtime_checkable
class AssistantProtocol(Protocol):
    """
    Protocol for assistant implementations.

    Any class implementing these methods is compatible with AssistantInterface.
    """

    async def process_message(
        self,
        message: Message,
        context: Optional[ConversationContext] = None,
    ) -> AssistantResponse:
        """Process a message and return response."""
        ...

    async def register_ability(self, ability: "AbilityProtocol") -> None:
        """Register an ability."""
        ...

    async def unregister_ability(self, ability_name: str) -> None:
        """Unregister an ability."""
        ...

    async def get_abilities(self) -> List[str]:
        """Get registered abilities."""
        ...

    async def initialize(self) -> None:
        """Initialize the assistant."""
        ...

    async def shutdown(self) -> None:
        """Shutdown the assistant."""
        ...

    async def health_check(self) -> Dict[str, Any]:
        """Check health status."""
        ...

    def get_metadata(self) -> Dict[str, Any]:
        """Get assistant metadata."""
        ...


@runtime_checkable
class LLMProtocol(Protocol):
    """
    Protocol for LLM implementations.

    Any class implementing these methods is compatible with LLMInterface.
    """

    async def generate(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text response."""
        ...

    async def stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream text response."""
        ...

    def get_token_count(self, text: str) -> int:
        """Get token count."""
        ...

    async def check_connection(self) -> bool:
        """Check connection status."""
        ...

    async def list_models(self) -> List[str]:
        """List available models."""
        ...

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        ...

    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
        ...

    def get_system_prompt(self) -> Optional[str]:
        """Get system prompt."""
        ...


@runtime_checkable
class MemoryProtocol(Protocol):
    """
    Protocol for memory implementations.

    Any class implementing these methods is compatible with MemoryInterface.
    """

    async def store_message(
        self,
        message: Message,
        conversation_id: str,
    ) -> None:
        """Store a message."""
        ...

    async def retrieve_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """Retrieve messages."""
        ...

    async def search_messages(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Message]:
        """Search messages."""
        ...

    async def store_memory(self, memory_entry: MemoryEntry) -> None:
        """Store memory entry."""
        ...

    async def retrieve_memories(self, query: MemoryQuery) -> List[MemoryEntry]:
        """Retrieve memories."""
        ...

    async def delete_memory(self, memory_id: str) -> None:
        """Delete memory."""
        ...

    async def create_session(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionContext:
        """Create session."""
        ...

    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get session."""
        ...

    async def end_session(self, session_id: str) -> None:
        """End session."""
        ...

    async def get_context(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> ConversationContext:
        """Get conversation context."""
        ...

    async def clear_history(
        self,
        conversation_id: str,
        keep_system_messages: bool = True,
    ) -> None:
        """Clear message history."""
        ...

    async def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics."""
        ...


@runtime_checkable
class AbilityProtocol(Protocol):
    """
    Protocol for ability implementations.

    Any class implementing these methods is compatible with AbilityInterface.
    """

    async def execute(self, request: AbilityRequest) -> AbilityResponse:
        """Execute ability action."""
        ...

    def get_metadata(self) -> AbilityMetadata:
        """Get ability metadata."""
        ...

    def can_handle(self, request: AbilityRequest) -> bool:
        """Check if can handle request."""
        ...

    async def initialize(self) -> None:
        """Initialize ability."""
        ...

    async def shutdown(self) -> None:
        """Shutdown ability."""
        ...

    async def health_check(self) -> Dict[str, Any]:
        """Check health status."""
        ...

    def get_supported_actions(self) -> List[str]:
        """Get supported actions."""
        ...

    def validate_request(self, request: AbilityRequest) -> bool:
        """Validate request."""
        ...


@runtime_checkable
class EmbeddingProtocol(Protocol):
    """
    Protocol for embedding implementations.

    Any class implementing these methods is compatible with EmbeddingInterface.
    """

    async def embed_text(self, text: str) -> List[float]:
        """Embed text."""
        ...

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        ...

    async def embed_message(self, message: Message) -> List[float]:
        """Embed message."""
        ...

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        ...

    def get_model_name(self) -> str:
        """Get model name."""
        ...

    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """Calculate similarity."""
        ...

    async def check_connection(self) -> bool:
        """Check connection."""
        ...


@runtime_checkable
class StreamProtocol(Protocol):
    """
    Protocol for streaming implementations.

    Any class implementing these methods is compatible with StreamInterface.
    """

    async def stream_response(
        self,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[StreamResponse]:
        """Stream response chunks."""
        ...

    async def start_stream(self) -> None:
        """Start streaming."""
        ...

    async def end_stream(self) -> None:
        """End streaming."""
        ...

    def is_streaming(self) -> bool:
        """Check if streaming."""
        ...

    async def cancel_stream(self) -> None:
        """Cancel stream."""
        ...
