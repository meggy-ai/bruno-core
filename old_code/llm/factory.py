"""LLM Factory for Bruno - Creates LLM clients based on configuration."""

import logging
from typing import Optional, Dict, Any

from bruno.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory class for creating LLM clients based on provider configuration.
    
    Supports:
    - ollama: Local Ollama server (default)
    - openai: OpenAI GPT models
    - claude: Anthropic Claude models
    """
    
    # Provider name constants
    OLLAMA = "ollama"
    OPENAI = "openai"
    CLAUDE = "claude"
    
    # Supported providers
    SUPPORTED_PROVIDERS = [OLLAMA, OPENAI, CLAUDE]
    
    @classmethod
    def create(
        cls,
        provider: str = "ollama",
        config: Optional[Dict[str, Any]] = None
    ) -> BaseLLMClient:
        """
        Create an LLM client based on provider type.
        
        Args:
            provider: Provider name ('ollama', 'openai', 'claude')
            config: Provider-specific configuration dictionary
                For ollama:
                    - base_url: Ollama server URL (default: http://localhost:11434)
                    - model: Model name (default: llama3.2)
                    - system_prompt: Optional system prompt
                    - timeout: Request timeout in seconds
                For openai:
                    - api_key: OpenAI API key (required)
                    - model: Model name (default: gpt-3.5-turbo)
                    - system_prompt: Optional system prompt
                    - timeout: Request timeout in seconds
                    - base_url: Optional custom base URL
                For claude:
                    - api_key: Anthropic API key (required)
                    - model: Model name (default: claude-3-sonnet-20240229)
                    - system_prompt: Optional system prompt
                    - timeout: Request timeout in seconds
                    - max_tokens: Max response tokens (default: 4096)
        
        Returns:
            Configured LLM client instance
        
        Raises:
            ValueError: If provider is not supported
            ValueError: If required configuration is missing
        """
        provider = provider.lower().strip()
        config = config or {}
        
        if provider not in cls.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported LLM provider: '{provider}'. "
                f"Supported providers: {', '.join(cls.SUPPORTED_PROVIDERS)}"
            )
        
        logger.info(f"🏭 Creating LLM client for provider: {provider}")
        
        if provider == cls.OLLAMA:
            return cls._create_ollama_client(config)
        elif provider == cls.OPENAI:
            return cls._create_openai_client(config)
        elif provider == cls.CLAUDE:
            return cls._create_claude_client(config)
        
        # This should never happen due to earlier validation
        raise ValueError(f"Unknown provider: {provider}")
    
    @classmethod
    def _create_ollama_client(cls, config: Dict[str, Any]) -> BaseLLMClient:
        """
        Create an Ollama client.
        
        Args:
            config: Ollama configuration
        
        Returns:
            Configured OllamaClient
        """
        from bruno.llm.ollama_client import OllamaClient
        
        return OllamaClient(
            base_url=config.get('url', 'http://localhost:11434'),
            model=config.get('model', 'llama3.2'),
            system_prompt=config.get('system_prompt'),
            timeout=config.get('timeout', 30)
        )
    
    @classmethod
    def _create_openai_client(cls, config: Dict[str, Any]) -> BaseLLMClient:
        """
        Create an OpenAI client.
        
        Args:
            config: OpenAI configuration
        
        Returns:
            Configured OpenAIClient
        
        Raises:
            ValueError: If API key is missing
        """
        api_key = config.get('api_key')
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. Set 'bruno.llm.openai.api_key' in config.yaml "
                "or use environment variable OPENAI_API_KEY"
            )
        
        from bruno.llm.openai_client import OpenAIClient
        
        return OpenAIClient(
            api_key=api_key,
            model=config.get('model', 'gpt-3.5-turbo'),
            system_prompt=config.get('system_prompt'),
            timeout=config.get('timeout', 30),
            base_url=config.get('base_url')
        )
    
    @classmethod
    def _create_claude_client(cls, config: Dict[str, Any]) -> BaseLLMClient:
        """
        Create a Claude client.
        
        Args:
            config: Claude configuration
        
        Returns:
            Configured ClaudeClient
        
        Raises:
            ValueError: If API key is missing
        """
        api_key = config.get('api_key')
        if not api_key:
            raise ValueError(
                "Anthropic API key is required. Set 'bruno.llm.claude.api_key' in config.yaml "
                "or use environment variable ANTHROPIC_API_KEY"
            )
        
        from bruno.llm.claude_client import ClaudeClient
        
        return ClaudeClient(
            api_key=api_key,
            model=config.get('model', 'claude-3-sonnet-20240229'),
            system_prompt=config.get('system_prompt'),
            timeout=config.get('timeout', 30),
            max_tokens=config.get('max_tokens', 4096)
        )
    
    @classmethod
    def get_supported_providers(cls) -> list:
        """Get list of supported provider names."""
        return cls.SUPPORTED_PROVIDERS.copy()
    
    @classmethod
    def is_supported(cls, provider: str) -> bool:
        """
        Check if a provider is supported.
        
        Args:
            provider: Provider name to check
        
        Returns:
            True if supported, False otherwise
        """
        return provider.lower().strip() in cls.SUPPORTED_PROVIDERS
