"""
Embedding Interface - Vector embedding contract.

Defines the contract for embedding providers (OpenAI, HuggingFace, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from bruno_core.models.message import Message


class EmbeddingInterface(ABC):
    """
    Abstract interface for embedding providers.

    Embeddings are vector representations of text used for:
    - Semantic search
    - Similarity comparison
    - Memory retrieval

    All embedding implementations must implement this interface.

    Example:
        >>> class OpenAIEmbeddings(EmbeddingInterface):
        ...     async def embed_text(self, text):
        ...         # Implementation
        ...         pass
    """

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (list of floats)

        Raises:
            LLMError: If embedding generation fails

        Example:
            >>> vector = await embeddings.embed_text("Hello world")
            >>> print(len(vector))
            1536
        """
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        More efficient than calling embed_text multiple times.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            LLMError: If embedding generation fails

        Example:
            >>> texts = ["Hello", "World"]
            >>> vectors = await embeddings.embed_texts(texts)
            >>> print(len(vectors))
            2
        """
        pass

    @abstractmethod
    async def embed_message(self, message: Message) -> List[float]:
        """
        Generate embedding for a message.

        Args:
            message: Message to embed

        Returns:
            Embedding vector

        Raises:
            LLMError: If embedding generation fails

        Example:
            >>> message = Message(role="user", content="Hello")
            >>> vector = await embeddings.embed_message(message)
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get embedding vector dimension.

        Returns:
            Dimension size (e.g., 1536 for OpenAI)

        Example:
            >>> dim = embeddings.get_dimension()
            >>> print(dim)
            1536
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get embedding model name.

        Returns:
            Model name

        Example:
            >>> model = embeddings.get_model_name()
            >>> print(model)
            'text-embedding-ada-002'
        """
        pass

    @abstractmethod
    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0.0 to 1.0)

        Example:
            >>> vec1 = await embeddings.embed_text("cat")
            >>> vec2 = await embeddings.embed_text("dog")
            >>> similarity = embeddings.calculate_similarity(vec1, vec2)
            >>> print(similarity)
            0.85
        """
        pass

    @abstractmethod
    async def check_connection(self) -> bool:
        """
        Check if embedding service is accessible.

        Returns:
            True if connected, False otherwise

        Example:
            >>> is_connected = await embeddings.check_connection()
        """
        pass

    def supports_batch(self) -> bool:
        """
        Check if provider supports batch embedding.

        Returns:
            True if batch operations are supported

        Example:
            >>> supports = embeddings.supports_batch()
            >>> print(supports)
            True
        """
        return True

    def get_max_batch_size(self) -> Optional[int]:
        """
        Get maximum batch size for embed_texts.

        Returns:
            Maximum batch size or None if unlimited

        Example:
            >>> max_size = embeddings.get_max_batch_size()
            >>> print(max_size)
            100
        """
        return None
