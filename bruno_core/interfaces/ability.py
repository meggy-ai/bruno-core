"""
Ability Interface - Executable action contract.

Defines the contract for abilities (timer, music, notes, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from bruno_core.models.ability import AbilityMetadata, AbilityRequest, AbilityResponse


class AbilityInterface(ABC):
    """
    Abstract interface for abilities.

    Abilities are executable actions that extend the assistant's capabilities.
    Examples: timers, alarms, music playback, note-taking, web search, etc.

    All ability implementations must implement this interface.

    Example:
        >>> class TimerAbility(AbilityInterface):
        ...     async def execute(self, request):
        ...         # Implementation
        ...         pass
        ...     def get_metadata(self):
        ...         return AbilityMetadata(name="timer", description="Manage timers")
    """

    @abstractmethod
    async def execute(self, request: AbilityRequest) -> AbilityResponse:
        """
        Execute the ability action.

        This is the main entry point for ability execution.

        Args:
            request: Ability execution request

        Returns:
            Ability response with results

        Raises:
            AbilityError: If execution fails

        Example:
            >>> request = AbilityRequest(
            ...     ability_name="timer",
            ...     action="set",
            ...     parameters={"duration_seconds": 300},
            ...     user_id="user_123"
            ... )
            >>> response = await ability.execute(request)
        """
        pass

    @abstractmethod
    def get_metadata(self) -> AbilityMetadata:
        """
        Get ability metadata.

        Returns metadata describing the ability's name, description,
        parameters, etc.

        Returns:
            Ability metadata

        Example:
            >>> metadata = ability.get_metadata()
            >>> print(metadata.name)
            'timer'
        """
        pass

    @abstractmethod
    def can_handle(self, request: AbilityRequest) -> bool:
        """
        Check if this ability can handle the request.

        Args:
            request: Ability request to check

        Returns:
            True if this ability can handle the request

        Example:
            >>> request = AbilityRequest(ability_name="timer", action="set", ...)
            >>> can_handle = timer_ability.can_handle(request)
            >>> print(can_handle)
            True
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the ability.

        Called once when the ability is registered.
        Use this to set up any required resources.

        Raises:
            AbilityError: If initialization fails

        Example:
            >>> await ability.initialize()
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Cleanup ability resources.

        Called when the ability is unregistered or assistant shuts down.

        Example:
            >>> await ability.shutdown()
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check ability health status.

        Returns:
            Dict with health information

        Example:
            >>> status = await ability.health_check()
            >>> print(status)
            {'status': 'healthy', 'active_timers': 3}
        """
        pass

    @abstractmethod
    def get_supported_actions(self) -> List[str]:
        """
        Get list of supported actions.

        Returns:
            List of action names this ability supports

        Example:
            >>> actions = timer_ability.get_supported_actions()
            >>> print(actions)
            ['set', 'cancel', 'status', 'list']
        """
        pass

    @abstractmethod
    def validate_request(self, request: AbilityRequest) -> bool:
        """
        Validate an ability request.

        Checks if the request has valid parameters, action, etc.

        Args:
            request: Request to validate

        Returns:
            True if request is valid

        Example:
            >>> is_valid = ability.validate_request(request)
        """
        pass

    def get_examples(self) -> List[str]:
        """
        Get usage examples for this ability.

        Returns:
            List of example usage strings

        Example:
            >>> examples = ability.get_examples()
            >>> print(examples)
            ['Set a timer for 5 minutes', 'Cancel all timers']
        """
        return []
