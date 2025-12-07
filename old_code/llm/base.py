"""Base LLM client interface for Bruno."""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Generator, Any

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.
    
    All LLM providers (Ollama, OpenAI, Claude) must implement this interface
    to ensure consistent behavior across the application.
    """
    
    def __init__(
        self,
        model: str,
        system_prompt: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize base LLM client.
        
        Args:
            model: Model name/identifier
            system_prompt: System prompt to set context (optional)
            timeout: Request timeout in seconds (default: 30)
        """
        self.model = model
        self.timeout = timeout
        self.conversation_history: List[Dict[str, str]] = []
        
        # Set system prompt if provided
        if system_prompt:
            self.conversation_history.append({
                "role": "system",
                "content": system_prompt
            })
    
    @abstractmethod
    def _check_connection(self) -> bool:
        """
        Check if the LLM service is accessible.
        
        Returns:
            True if service is accessible, False otherwise
        """
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """
        List available models from the provider.
        
        Returns:
            List of model names
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: str, use_history: bool = True) -> Optional[str]:
        """
        Generate a response to the given prompt.
        
        Args:
            prompt: User prompt/question
            use_history: If True, include conversation history for context
        
        Returns:
            Generated response text, or None on error
        """
        pass
    
    @abstractmethod
    def generate_streaming(self, prompt: str, use_history: bool = True) -> Generator[str, None, None]:
        """
        Generate a streaming response (yields chunks as they arrive).
        
        Args:
            prompt: User prompt/question
            use_history: If True, include conversation history for context
        
        Yields:
            Response chunks as they are generated
        """
        pass
    
    def clear_history(self):
        """Clear conversation history (keeps system prompt if set)."""
        system_messages = [msg for msg in self.conversation_history if msg.get("role") == "system"]
        self.conversation_history = system_messages
        logger.info("🗑️  Conversation history cleared")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get current conversation history."""
        return self.conversation_history.copy()
    
    def set_system_prompt(self, prompt: str):
        """
        Set or update system prompt.
        
        Args:
            prompt: System prompt text
        """
        # Remove existing system prompts
        self.conversation_history = [
            msg for msg in self.conversation_history 
            if msg.get("role") != "system"
        ]
        
        # Add new system prompt at the beginning
        self.conversation_history.insert(0, {
            "role": "system",
            "content": prompt
        })
        
        logger.info("✅ System prompt updated")
    
    def _add_to_history(self, role: str, content: str):
        """
        Add a message to conversation history.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    @property
    def provider_name(self) -> str:
        """Get the provider name for logging."""
        return self.__class__.__name__
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.provider_name} model={self.model}>"
