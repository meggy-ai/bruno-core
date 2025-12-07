"""
Configuration utilities for bruno-core.

Provides configuration loading, saving, and management.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from bruno_core.models.config import BrunoConfig
from bruno_core.utils.exceptions import ConfigError


def load_config(
    config_path: Optional[str] = None,
    env_file: Optional[str] = None,
) -> BrunoConfig:
    """
    Load Bruno configuration from file.

    Supports YAML and JSON formats. Environment variables override file values.

    Args:
        config_path: Path to config file (YAML or JSON)
        env_file: Path to .env file for environment variables

    Returns:
        Loaded configuration

    Raises:
        ConfigError: If configuration cannot be loaded

    Example:
        >>> config = load_config("config.yaml")
        >>> config = load_config(env_file=".env")
    """
    # Load environment variables
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()  # Load from default .env file

    config_dict: Dict[str, Any] = {}

    # Load from file if provided
    if config_path:
        config_path_obj = Path(config_path)

        if not config_path_obj.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        try:
            if config_path.endswith((".yaml", ".yml")):
                with open(config_path_obj, "r", encoding="utf-8") as f:
                    config_dict = yaml.safe_load(f) or {}
            elif config_path.endswith(".json"):
                with open(config_path_obj, "r", encoding="utf-8") as f:
                    config_dict = json.load(f)
            else:
                raise ConfigError(f"Unsupported config file format: {config_path}")
        except Exception as e:
            raise ConfigError(
                f"Failed to load configuration from {config_path}",
                cause=e,
            )

    # Override with environment variables
    config_dict = _apply_env_overrides(config_dict)

    # Validate and create BrunoConfig
    try:
        return BrunoConfig(**config_dict)
    except Exception as e:
        raise ConfigError("Invalid configuration", cause=e)


def save_config(config: BrunoConfig, config_path: str, format: str = "yaml") -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save
        config_path: Path to save to
        format: Format ("yaml" or "json")

    Raises:
        ConfigError: If configuration cannot be saved

    Example:
        >>> save_config(config, "config.yaml", format="yaml")
    """
    config_dict = config.model_dump(exclude_none=True)

    try:
        config_path_obj = Path(config_path)
        config_path_obj.parent.mkdir(parents=True, exist_ok=True)

        if format == "yaml":
            with open(config_path_obj, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_dict, f, default_flow_style=False, indent=2)
        elif format == "json":
            with open(config_path_obj, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2)
        else:
            raise ConfigError(f"Unsupported format: {format}")
    except Exception as e:
        raise ConfigError(f"Failed to save configuration to {config_path}", cause=e)


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries.

    Override values take precedence over base values.

    Args:
        base: Base configuration
        override: Override configuration

    Returns:
        Merged configuration

    Example:
        >>> base = {"llm": {"provider": "ollama"}}
        >>> override = {"llm": {"model": "llama2"}}
        >>> merge_configs(base, override)
        {'llm': {'provider': 'ollama', 'model': 'llama2'}}
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply environment variable overrides to configuration.

    Environment variables are in format: BRUNO_SECTION_KEY
    e.g., BRUNO_LLM_PROVIDER, BRUNO_MEMORY_BACKEND

    Args:
        config: Base configuration

    Returns:
        Configuration with environment overrides
    """
    # LLM overrides
    if "llm" not in config:
        config["llm"] = {}

    if os.getenv("BRUNO_LLM_PROVIDER"):
        config["llm"]["provider"] = os.getenv("BRUNO_LLM_PROVIDER")
    if os.getenv("BRUNO_LLM_MODEL"):
        config["llm"]["model"] = os.getenv("BRUNO_LLM_MODEL")
    if os.getenv("BRUNO_LLM_API_KEY"):
        config["llm"]["api_key"] = os.getenv("BRUNO_LLM_API_KEY")
    if os.getenv("BRUNO_LLM_BASE_URL"):
        config["llm"]["base_url"] = os.getenv("BRUNO_LLM_BASE_URL")
    if os.getenv("BRUNO_LLM_TEMPERATURE"):
        config["llm"]["temperature"] = float(os.getenv("BRUNO_LLM_TEMPERATURE"))
    if os.getenv("BRUNO_LLM_MAX_TOKENS"):
        config["llm"]["max_tokens"] = int(os.getenv("BRUNO_LLM_MAX_TOKENS"))

    # Memory overrides
    if "memory" not in config:
        config["memory"] = {}

    if os.getenv("BRUNO_MEMORY_BACKEND"):
        config["memory"]["backend"] = os.getenv("BRUNO_MEMORY_BACKEND")
    if os.getenv("BRUNO_MEMORY_CONNECTION_STRING"):
        config["memory"]["connection_string"] = os.getenv("BRUNO_MEMORY_CONNECTION_STRING")
    if os.getenv("BRUNO_MEMORY_MAX_MESSAGES"):
        config["memory"]["max_messages"] = int(os.getenv("BRUNO_MEMORY_MAX_MESSAGES"))

    # Assistant overrides
    if "assistant" not in config:
        config["assistant"] = {}

    if os.getenv("BRUNO_ASSISTANT_NAME"):
        config["assistant"]["name"] = os.getenv("BRUNO_ASSISTANT_NAME")
    if os.getenv("BRUNO_ASSISTANT_LANGUAGE"):
        config["assistant"]["language"] = os.getenv("BRUNO_ASSISTANT_LANGUAGE")

    # Log level override
    if os.getenv("BRUNO_LOG_LEVEL"):
        config["log_level"] = os.getenv("BRUNO_LOG_LEVEL")

    return config
