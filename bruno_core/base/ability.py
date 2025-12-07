"""
Base Ability implementation.

Provides a base class for all abilities with common functionality.
"""

from abc import abstractmethod
from typing import Any, Dict, List

from bruno_core.interfaces.ability import AbilityInterface
from bruno_core.models.ability import (
    AbilityMetadata,
    AbilityParameter,
    AbilityRequest,
    AbilityResponse,
)
from bruno_core.utils.exceptions import AbilityError, ValidationError
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAbility(AbilityInterface):
    """
    Base class for all abilities.

    Provides common functionality like validation, logging, and lifecycle management.
    Subclasses must implement execute_action() and get_metadata().

    Example:
        >>> class TimerAbility(BaseAbility):
        ...     def get_metadata(self):
        ...         return AbilityMetadata(name="timer", description="Manage timers")
        ...     
        ...     async def execute_action(self, request):
        ...         # Implementation
        ...         pass
    """

    def __init__(self):
        """Initialize base ability."""
        self.initialized = False
        self._metadata: AbilityMetadata = self.get_metadata()
        logger.info("ability_created", name=self._metadata.name)

    async def execute(self, request: AbilityRequest) -> AbilityResponse:
        """
        Execute the ability action.

        Handles validation, logging, and error handling.

        Args:
            request: Ability execution request

        Returns:
            Ability response
        """
        if not self.initialized:
            raise AbilityError(
                f"Ability not initialized: {self._metadata.name}",
                details={"ability": self._metadata.name},
            )

        try:
            # Validate request
            if not self.validate_request(request):
                return AbilityResponse(
                    request_id=request.id,
                    ability_name=self._metadata.name,
                    action=request.action,
                    success=False,
                    error="Invalid request parameters",
                )

            logger.info(
                "ability_executing",
                ability=self._metadata.name,
                action=request.action,
            )

            # Execute the actual action
            response = await self.execute_action(request)

            logger.info(
                "ability_executed",
                ability=self._metadata.name,
                success=response.success,
            )

            return response

        except Exception as e:
            logger.error(
                "ability_execution_failed",
                ability=self._metadata.name,
                error=str(e),
            )
            return AbilityResponse(
                request_id=request.id,
                ability_name=self._metadata.name,
                action=request.action,
                success=False,
                error=str(e),
            )

    @abstractmethod
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        """
        Execute the specific ability action.

        Subclasses must implement this method.

        Args:
            request: Ability request

        Returns:
            Ability response
        """
        pass

    @abstractmethod
    def get_metadata(self) -> AbilityMetadata:
        """
        Get ability metadata.

        Subclasses must implement this method.

        Returns:
            Ability metadata
        """
        pass

    def can_handle(self, request: AbilityRequest) -> bool:
        """
        Check if this ability can handle the request.

        Args:
            request: Ability request

        Returns:
            True if can handle
        """
        if request.ability_name != self._metadata.name:
            return False

        if request.action not in self.get_supported_actions():
            return False

        return True

    async def initialize(self) -> None:
        """
        Initialize the ability.

        Override this method to add custom initialization logic.
        """
        if self.initialized:
            logger.warning("ability_already_initialized", name=self._metadata.name)
            return

        logger.info("ability_initializing", name=self._metadata.name)
        self.initialized = True
        logger.info("ability_initialized", name=self._metadata.name)

    async def shutdown(self) -> None:
        """
        Cleanup ability resources.

        Override this method to add custom cleanup logic.
        """
        logger.info("ability_shutting_down", name=self._metadata.name)
        self.initialized = False
        logger.info("ability_shutdown_complete", name=self._metadata.name)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check ability health status.

        Returns:
            Dict with health information
        """
        return {
            "status": "healthy" if self.initialized else "not_initialized",
            "ability": self._metadata.name,
            "version": self._metadata.version,
        }

    def get_supported_actions(self) -> List[str]:
        """
        Get list of supported actions.

        Default implementation returns empty list.
        Override in subclasses.

        Returns:
            List of action names
        """
        return []

    def validate_request(self, request: AbilityRequest) -> bool:
        """
        Validate an ability request.

        Checks parameters against metadata definitions.

        Args:
            request: Request to validate

        Returns:
            True if valid
        """
        try:
            # Check if action is supported
            if request.action not in self.get_supported_actions():
                logger.warning(
                    "unsupported_action",
                    ability=self._metadata.name,
                    action=request.action,
                )
                return False

            # Validate required parameters
            required_params = self._metadata.get_required_parameters()
            for param in required_params:
                if param.name not in request.parameters:
                    logger.warning(
                        "missing_required_parameter",
                        ability=self._metadata.name,
                        parameter=param.name,
                    )
                    return False

                # Validate parameter value
                value = request.parameters[param.name]
                if not param.validate_value(value):
                    logger.warning(
                        "invalid_parameter_value",
                        ability=self._metadata.name,
                        parameter=param.name,
                        value=value,
                    )
                    return False

            return True

        except Exception as e:
            logger.error("validation_failed", error=str(e))
            return False

    def get_examples(self) -> List[str]:
        """
        Get usage examples for this ability.

        Returns:
            List of example usage strings
        """
        return self._metadata.examples

    async def rollback(self, request: AbilityRequest) -> None:
        """
        Rollback a previously executed action.

        Override this method in subclasses that support rollback.

        Args:
            request: Original request to rollback
        """
        logger.warning(
            "rollback_not_implemented",
            ability=self._metadata.name,
            action=request.action,
        )
