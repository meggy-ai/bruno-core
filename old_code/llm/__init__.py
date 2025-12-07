"""LLM integration module for Bruno."""

from .base import BaseLLMClient
from .ollama_client import OllamaClient
from .factory import LLMFactory

# Optional imports - these may fail if packages aren't installed
try:
    from .openai_client import OpenAIClient
except ImportError:
    OpenAIClient = None

try:
    from .claude_client import ClaudeClient
except ImportError:
    ClaudeClient = None

__all__ = [
    'BaseLLMClient',
    'OllamaClient',
    'OpenAIClient',
    'ClaudeClient',
    'LLMFactory'
]
