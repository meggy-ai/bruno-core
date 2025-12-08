"""
Chain Executor implementation.

Orchestrates sequential execution of abilities with result passing and conditional branching.
"""

from typing import Any, Callable, Dict, List, Optional, Union

from bruno_core.interfaces.ability import AbilityInterface
from bruno_core.models.ability import AbilityRequest, AbilityResponse
from bruno_core.utils.exceptions import AbilityError
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class ChainStep:
    """
    Represents a single step in a chain.

    Attributes:
        ability_name: Name of ability to execute
        action: Action to perform
        parameters: Action parameters (can be callable for dynamic params)
        condition: Optional condition to check before executing
        on_success: Optional callback on success
        on_failure: Optional callback on failure
    """

    def __init__(
        self,
        ability_name: str,
        action: str,
        parameters: Union[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]],
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        on_success: Optional[Callable[[AbilityResponse], None]] = None,
        on_failure: Optional[Callable[[AbilityResponse], None]] = None,
    ):
        """
        Initialize chain step.

        Args:
            ability_name: Ability name
            action: Action to perform
            parameters: Static params or callable that returns params
            condition: Optional condition function
            on_success: Optional success callback
            on_failure: Optional failure callback
        """
        self.ability_name = ability_name
        self.action = action
        self.parameters = parameters
        self.condition = condition
        self.on_success = on_success
        self.on_failure = on_failure


class ChainExecutor:
    """
    Executes abilities in a sequential chain with result passing.

    Features:
    - Sequential execution with result passing
    - Conditional step execution
    - Dynamic parameter resolution
    - Success/failure callbacks
    - Chain visualization

    Example:
        >>> chain = ChainExecutor()
        >>> chain.add_step("timer", "set", {"duration": 300})
        >>> chain.add_step("notify", "send", lambda ctx: {"message": ctx["timer_id"]})
        >>> results = await chain.execute(abilities, user_id="user_123")
    """

    def __init__(self) -> None:
        """Initialize chain executor."""
        self.steps: List[ChainStep] = []
        self.context: Dict[str, Any] = {}
        logger.info("chain_executor_created")

    def add_step(
        self,
        ability_name: str,
        action: str,
        parameters: Union[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]],
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        on_success: Optional[Callable[[AbilityResponse], None]] = None,
        on_failure: Optional[Callable[[AbilityResponse], None]] = None,
    ) -> "ChainExecutor":
        """
        Add a step to the chain.

        Args:
            ability_name: Ability name
            action: Action to perform
            parameters: Static params or callable
            condition: Optional condition to check
            on_success: Optional success callback
            on_failure: Optional failure callback

        Returns:
            Self for chaining

        Example:
            >>> chain.add_step("timer", "set", {"duration": 300})
            ...      .add_step("notify", "send", lambda ctx: {"timer": ctx["timer_id"]})
        """
        step = ChainStep(
            ability_name=ability_name,
            action=action,
            parameters=parameters,
            condition=condition,
            on_success=on_success,
            on_failure=on_failure,
        )
        self.steps.append(step)
        logger.info("chain_step_added", ability=ability_name, action=action)
        return self

    async def execute(
        self,
        abilities: Dict[str, AbilityInterface],
        user_id: str,
        conversation_id: Optional[str] = None,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> List[AbilityResponse]:
        """
        Execute the chain.

        Args:
            abilities: Map of ability name to ability instance
            user_id: User ID
            conversation_id: Optional conversation ID
            initial_context: Optional initial context values

        Returns:
            List of ability responses

        Raises:
            AbilityError: If chain execution fails
        """
        if not self.steps:
            logger.warning("empty_chain_execution")
            return []

        logger.info("executing_chain", steps=len(self.steps))

        # Initialize context
        self.context = initial_context or {}
        self.context["user_id"] = user_id
        if conversation_id:
            self.context["conversation_id"] = conversation_id

        responses: List[AbilityResponse] = []

        for i, step in enumerate(self.steps):
            logger.info(
                "executing_chain_step",
                step=i + 1,
                ability=step.ability_name,
                action=step.action,
            )

            # Check condition
            if step.condition and not step.condition(self.context):
                logger.info(
                    "step_skipped_by_condition",
                    step=i + 1,
                    ability=step.ability_name,
                )
                continue

            # Resolve parameters
            if callable(step.parameters):
                parameters = step.parameters(self.context)
            else:
                parameters = step.parameters

            # Get ability
            ability = abilities.get(step.ability_name)
            if not ability:
                error_msg = f"Ability not found: {step.ability_name}"
                logger.error("chain_step_failed", step=i + 1, error=error_msg)
                raise AbilityError(error_msg)

            # Create request
            request = AbilityRequest(
                ability_name=step.ability_name,
                action=step.action,
                parameters=parameters,
                user_id=user_id,
                conversation_id=conversation_id,
            )

            # Execute
            try:
                response = await ability.execute(request)
                responses.append(response)

                # Update context with response data
                self.context[f"{step.ability_name}_response"] = response.data
                self.context[f"{step.ability_name}_success"] = response.success

                # Call callbacks
                if response.success and step.on_success:
                    step.on_success(response)
                elif not response.success and step.on_failure:
                    step.on_failure(response)

                # Stop on failure if no failure handler
                if not response.success and not step.on_failure:
                    logger.warning(
                        "chain_stopped_on_failure",
                        step=i + 1,
                        ability=step.ability_name,
                    )
                    break

            except Exception as e:
                logger.error(
                    "chain_step_exception",
                    step=i + 1,
                    ability=step.ability_name,
                    error=str(e),
                )
                raise AbilityError(
                    f"Chain execution failed at step {i + 1}",
                    details={"step": i + 1, "ability": step.ability_name},
                    cause=e,
                )

        logger.info("chain_execution_complete", total_steps=len(responses))
        return responses

    def clear(self) -> None:
        """Clear all steps from the chain."""
        self.steps.clear()
        self.context.clear()
        logger.info("chain_cleared")

    def get_context(self) -> Dict[str, Any]:
        """
        Get current chain context.

        Returns:
            Context dictionary
        """
        return self.context.copy()

    def visualize(self) -> str:
        """
        Get a text visualization of the chain.

        Returns:
            Text representation of the chain

        Example:
            >>> print(chain.visualize())
            Step 1: timer.set
            Step 2: notify.send (conditional)
            Step 3: log.record
        """
        if not self.steps:
            return "Empty chain"

        lines = ["Chain:"]
        for i, step in enumerate(self.steps):
            conditional = " (conditional)" if step.condition else ""
            lines.append(f"  Step {i + 1}: {step.ability_name}.{step.action}{conditional}")

        return "\n".join(lines)
