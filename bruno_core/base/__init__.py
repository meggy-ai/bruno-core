"""
Base implementations for bruno-core.

This package provides default implementations of the core interfaces
that can be extended and customized.

Modules:
    assistant: BaseAssistant - Main orchestrator implementation
    executor: ActionExecutor - Action execution pipeline
    ability: BaseAbility - Base class for abilities
    chain: ChainExecutor - Workflow orchestration
"""

from bruno_core.base.assistant import BaseAssistant
from bruno_core.base.executor import ActionExecutor
from bruno_core.base.ability import BaseAbility
from bruno_core.base.chain import ChainExecutor

__all__ = [
    "BaseAssistant",
    "ActionExecutor",
    "BaseAbility",
    "ChainExecutor",
]
