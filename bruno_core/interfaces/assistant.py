"""
Assistant Interface - Main orchestrator for Bruno.

Defines the contract for the main assistant that coordinates
LLM, memory, abilities, and other components.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from bruno_core.models.context import ConversationContext
from bruno_core.models.message import Message
from bruno_core.models.response import AssistantResponse


class AssistantInterface(ABC):
    """
    Abstract interface for Bruno assistants.

    The assistant is the main orchestrator that:
    - Processes incoming messages
    - Manages conversation context
    - Coordinates LLM, memory, and abilities
    - Returns responses to users

    All assistant implementations must implement this interface.

    Example:
        >>> class MyAssistant(AssistantInterface):
        ...     async def process_message(self, message, context):
        ...         # Implementation
        ...         pass
    """

    @abstractmethod
    async def process_message(
        self,
        message: Message,
        context: Optional[ConversationContext] = None,
    ) -> AssistantResponse:
        """
        Process an incoming message and generate a response.

        This is the main entry point for all user interactions.

        Args:
            message: User message to process
            context: Optional conversation context (created if None)

        Returns:
            Assistant response with text and actions

        Raises:
            BrunoError: If processing fails

        Example:
            >>> message = Message(role="user", content="Set a timer for 5 minutes")
            >>> response = await assistant.process_message(message)
            >>> print(response.text)
            "I've set a timer for 5 minutes."
        """
        pass

    @abstractmethod
    async def register_ability(self, ability: "AbilityInterface") -> None:
        """
        Register a new ability with the assistant.

        Abilities are dynamically discovered and registered at runtime.

        Args:
            ability: Ability instance to register

        Raises:
            RegistryError: If registration fails

        Example:
            >>> from bruno_abilities import TimerAbility
            >>> timer = TimerAbility()
            >>> await assistant.register_ability(timer)
        """
        pass

    @abstractmethod
    async def unregister_ability(self, ability_name: str) -> None:
        """
        Unregister an ability from the assistant.

        Args:
            ability_name: Name of ability to unregister

        Raises:
            RegistryError: If ability not found

        Example:
            >>> await assistant.unregister_ability("timer")
        """
        pass

    @abstractmethod
    async def get_abilities(self) -> List[str]:
        """
        Get list of registered ability names.

        Returns:
            List of ability names

        Example:
            >>> abilities = await assistant.get_abilities()
            >>> print(abilities)
            ['timer', 'music', 'notes']
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the assistant and all its components.

        Called before the assistant can process messages.

        Raises:
            BrunoError: If initialization fails

        Example:
            >>> assistant = MyAssistant(config)
            >>> await assistant.initialize()
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the assistant and cleanup resources.

        Called when the assistant is no longer needed.

        Example:
            >>> await assistant.shutdown()
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health status of assistant and its components.

        Returns:
            Dict with health status information

        Example:
            >>> status = await assistant.health_check()
            >>> print(status)
            {'status': 'healthy', 'llm': 'connected', 'memory': 'ready'}
        """
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get assistant metadata (name, version, etc.).

        Returns:
            Dict with metadata

        Example:
            >>> metadata = assistant.get_metadata()
            >>> print(metadata)
            {'name': 'Bruno', 'version': '1.0.0'}
        """
        pass
