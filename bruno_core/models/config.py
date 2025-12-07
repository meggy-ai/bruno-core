"""
Configuration models for bruno-core.

Defines configuration structures for Bruno components.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    """
    Configuration for LLM provider.

    Attributes:
        provider: LLM provider name (ollama, openai, claude, etc.)
        model: Model name/identifier
        api_key: API key for provider (if needed)
        base_url: Base URL for API (if custom)
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
        system_prompt: System prompt to use
        additional_params: Provider-specific parameters

    Example:
        >>> config = LLMConfig(
        ...     provider="ollama",
        ...     model="llama2",
        ...     temperature=0.7,
        ...     max_tokens=2000
        ... )
    """

    provider: str = Field(..., min_length=1, description="LLM provider name")
    model: str = Field(..., min_length=1, description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    base_url: Optional[str] = Field(default=None, description="Base URL")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: int = Field(default=2000, ge=1, description="Max tokens")
    timeout: int = Field(default=30, ge=1, description="Timeout in seconds")
    system_prompt: Optional[str] = Field(default=None, description="System prompt")
    additional_params: Dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific params"
    )

    @field_validator("provider")
    @classmethod
    def provider_lowercase(cls, v: str) -> str:
        """Convert provider name to lowercase."""
        return v.lower()


class MemoryConfig(BaseModel):
    """
    Configuration for memory backend.

    Attributes:
        backend: Memory backend type (sqlite, postgres, redis, etc.)
        connection_string: Database connection string
        max_messages: Maximum messages in context window
        compression_threshold: When to trigger compression
        stm_threshold: Relevance threshold for STM
        ltm_threshold: Importance threshold for LTM
        enable_embeddings: Whether to generate embeddings
        embedding_model: Model for generating embeddings
        additional_params: Backend-specific parameters

    Example:
        >>> config = MemoryConfig(
        ...     backend="sqlite",
        ...     connection_string="bruno_memory.db",
        ...     max_messages=20
        ... )
    """

    backend: str = Field(..., min_length=1, description="Memory backend type")
    connection_string: str = Field(..., min_length=1, description="Connection string")
    max_messages: int = Field(default=20, ge=1, le=1000, description="Max messages in context")
    compression_threshold: int = Field(
        default=50, ge=1, description="Compression trigger threshold"
    )
    stm_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="STM relevance threshold")
    ltm_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="LTM importance threshold"
    )
    enable_embeddings: bool = Field(default=True, description="Generate embeddings")
    embedding_model: Optional[str] = Field(default=None, description="Embedding model name")
    additional_params: Dict[str, Any] = Field(
        default_factory=dict, description="Backend-specific params"
    )

    @field_validator("backend")
    @classmethod
    def backend_lowercase(cls, v: str) -> str:
        """Convert backend name to lowercase."""
        return v.lower()


class AssistantConfig(BaseModel):
    """
    Configuration for assistant behavior.

    Attributes:
        name: Assistant name
        personality: Personality description
        language: Language code (en, es, fr, etc.)
        enable_voice: Enable voice input/output
        enable_actions: Enable action execution
        max_retries: Max retries on error
        timeout: Request timeout in seconds
        abilities: List of enabled abilities
        event_handlers: List of enabled event handlers
        middleware: List of enabled middleware
        additional_params: Additional parameters

    Example:
        >>> config = AssistantConfig(
        ...     name="Bruno",
        ...     language="en",
        ...     abilities=["timer", "music", "notes"]
        ... )
    """

    name: str = Field(default="Bruno", description="Assistant name")
    personality: Optional[str] = Field(default=None, description="Personality")
    language: str = Field(default="en", description="Language code")
    enable_voice: bool = Field(default=False, description="Enable voice")
    enable_actions: bool = Field(default=True, description="Enable actions")
    max_retries: int = Field(default=3, ge=0, description="Max retries")
    timeout: int = Field(default=30, ge=1, description="Timeout in seconds")
    abilities: List[str] = Field(default_factory=list, description="Enabled abilities")
    event_handlers: List[str] = Field(default_factory=list, description="Event handlers")
    middleware: List[str] = Field(default_factory=list, description="Middleware")
    additional_params: Dict[str, Any] = Field(default_factory=dict, description="Additional params")


class BrunoConfig(BaseModel):
    """
    Complete Bruno configuration.

    Combines all configuration sections.

    Attributes:
        llm: LLM configuration
        memory: Memory configuration
        assistant: Assistant configuration
        log_level: Logging level
        log_format: Log format (json, text)
        environment: Environment (development, production)

    Example:
        >>> config = BrunoConfig(
        ...     llm=LLMConfig(provider="ollama", model="llama2"),
        ...     memory=MemoryConfig(backend="sqlite", connection_string="bruno.db"),
        ...     assistant=AssistantConfig(name="Bruno")
        ... )
    """

    llm: LLMConfig = Field(..., description="LLM configuration")
    memory: MemoryConfig = Field(..., description="Memory configuration")
    assistant: AssistantConfig = Field(
        default_factory=AssistantConfig, description="Assistant configuration"
    )
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="text", description="Log format")
    environment: str = Field(default="development", description="Environment")

    @field_validator("log_level")
    @classmethod
    def log_level_uppercase(cls, v: str) -> str:
        """Convert log level to uppercase."""
        return v.upper()

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        if v not in ["json", "text"]:
            raise ValueError("log_format must be 'json' or 'text'")
        return v.lower()
