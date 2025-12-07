"""Configuration management for Bruno."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

logger = logging.getLogger(__name__)


class BrunoConfig:
    """Bruno configuration manager."""
    
    DEFAULT_CONFIG = {
        'bruno': {
            'user_name': 'User',
            'assistant_name': 'Bruno',
            'wake_words': ['bruno', 'hey bruno', 'jarvis'],
            'audio': {
                'device_index': None,
                'sample_rate': 16000,
                'avoid_bluetooth': True,
                'buffer_size': 2048
            },
            'vosk': {
                'model_path': 'vosk-model-small-en-us-0.15'
            },
            'command_recognition': {
                'timeout_seconds': 10.0,
                'phrase_time_limit': 20,
                'energy_threshold': 400,
                'pause_threshold': 2.0,
                'max_retries': 2
            },
            'llm': {
                'provider': 'ollama',  # ollama, openai, or claude
                'url': 'http://localhost:11434',
                'model': 'llama3.2',
                'timeout': 30,
                'system_prompt': 'You are Bruno, a helpful and friendly voice assistant.',
                # Provider-specific configurations
                'openai': {
                    'api_key': None,  # Can also use OPENAI_API_KEY env var
                    'model': 'gpt-3.5-turbo',
                    'base_url': None  # Optional custom base URL
                },
                'claude': {
                    'api_key': None,  # Can also use ANTHROPIC_API_KEY env var
                    'model': 'claude-3-sonnet-20240229',
                    'max_tokens': 4096
                }
            },
            'tts': {
                'engine': 'windows_native',
                'rate': 0,
                'volume': 100
            }
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config.yaml file (None = auto-detect)
        """
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config.yaml"
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load configuration from file or use defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"✅ Configuration loaded from {self.config_path}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load config: {e}, using defaults")
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            logger.info("ℹ️  No config file found, using defaults")
            self.config = self.DEFAULT_CONFIG.copy()
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path (e.g., 'bruno.audio.sample_rate')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"✅ Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save config: {e}")
    
    @property
    def wake_words(self) -> list:
        """Get wake words list."""
        return self.get('bruno.wake_words', ['bruno'])
    
    @property
    def model_path(self) -> str:
        """Get Vosk model path."""
        return self.get('bruno.vosk.model_path', 'vosk-model-small-en-us-0.15')
    
    @property
    def device_index(self) -> Optional[int]:
        """Get audio device index."""
        return self.get('bruno.audio.device_index')
    
    @property
    def sample_rate(self) -> int:
        """Get audio sample rate."""
        return self.get('bruno.audio.sample_rate', 16000)
    
    @property
    def llm_provider(self) -> str:
        """Get LLM provider name."""
        return self.get('bruno.llm.provider', 'ollama')
    
    @property
    def llm_url(self) -> str:
        """Get LLM base URL (for Ollama)."""
        return self.get('bruno.llm.url', 'http://localhost:11434')
    
    @property
    def llm_model(self) -> str:
        """Get LLM model name."""
        return self.get('bruno.llm.model', 'llama3.2')
    
    @property
    def llm_timeout(self) -> int:
        """Get LLM request timeout."""
        return self.get('bruno.llm.timeout', 30)
    
    @property
    def llm_system_prompt(self) -> Optional[str]:
        """Get LLM system prompt."""
        return self.get('bruno.llm.system_prompt')
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get complete LLM configuration for the current provider.
        
        Returns:
            Dictionary with provider-specific configuration
        """
        provider = self.llm_provider
        base_config = {
            'system_prompt': self.llm_system_prompt,
            'timeout': self.llm_timeout
        }
        
        if provider == 'ollama':
            return {
                **base_config,
                'url': self.llm_url,
                'model': self.llm_model
            }
        elif provider == 'openai':
            openai_config = self.get('bruno.llm.openai', {})
            api_key = openai_config.get('api_key') or os.environ.get('OPENAI_API_KEY')
            return {
                **base_config,
                'api_key': api_key,
                'model': openai_config.get('model', 'gpt-3.5-turbo'),
                'base_url': openai_config.get('base_url')
            }
        elif provider == 'claude':
            claude_config = self.get('bruno.llm.claude', {})
            api_key = claude_config.get('api_key') or os.environ.get('ANTHROPIC_API_KEY')
            return {
                **base_config,
                'api_key': api_key,
                'model': claude_config.get('model', 'claude-3-sonnet-20240229'),
                'max_tokens': claude_config.get('max_tokens', 4096)
            }
        else:
            # Fallback to ollama config
            return {
                **base_config,
                'url': self.llm_url,
                'model': self.llm_model
            }
