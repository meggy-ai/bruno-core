"""
Logging configuration for bruno-core.

Provides structured logging using structlog.
"""

import logging
import sys
from typing import Any, Dict, Optional

import structlog


def setup_logging(
    level: str = "INFO",
    format_type: str = "text",
    log_file: Optional[str] = None,
) -> None:
    """
    Configure structured logging for Bruno.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("text" or "json")
        log_file: Optional log file path

    Example:
        >>> setup_logging(level="DEBUG", format_type="json")
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        stream=sys.stdout,
    )

    # Configure processors based on format type
    if format_type == "json":
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:  # text format
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Add file handler if log_file specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str, **initial_values: Any) -> structlog.BoundLogger:
    """
    Get a logger instance with optional initial context.

    Args:
        name: Logger name (usually __name__)
        **initial_values: Initial context values to bind

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__, component="assistant")
        >>> logger.info("processing_message", user_id="user_123")
    """
    logger = structlog.get_logger(name)
    if initial_values:
        logger = logger.bind(**initial_values)
    return logger


def log_function_call(func_name: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Create a log entry for function calls.

    Useful for debugging and tracing execution.

    Args:
        func_name: Name of the function
        **kwargs: Function arguments

    Returns:
        Dict with structured log data

    Example:
        >>> logger.debug("function_call", **log_function_call("process_message", user_id="123"))
    """
    return {
        "function": func_name,
        "args": kwargs,
    }


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a structured log entry for errors.

    Args:
        error: Exception instance
        context: Additional context

    Returns:
        Dict with structured error data

    Example:
        >>> try:
        ...     raise ValueError("Test error")
        ... except Exception as e:
        ...     logger.error("error_occurred", **log_error(e, {"user_id": "123"}))
    """
    error_data: Dict[str, Any] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    if context:
        error_data["context"] = context

    return error_data
