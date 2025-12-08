"""
Action Executor implementation.

Executes actions in sequence or parallel with error handling and rollback support.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional

from bruno_core.models.ability import AbilityRequest, AbilityResponse
from bruno_core.models.response import ActionResult, ActionStatus
from bruno_core.utils.exceptions import AbilityError
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class ActionExecutor:
    """
    Executes actions with support for parallel execution, rollback, and auditing.

    Features:
    - Sequential or parallel execution
    - Automatic rollback on failure
    - Action result aggregation
    - Execution logging and auditing

    Example:
        >>> executor = ActionExecutor()
        >>> results = await executor.execute(actions)
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        enable_rollback: bool = True,
    ):
        """
        Initialize action executor.

        Args:
            max_concurrent: Maximum concurrent actions
            enable_rollback: Enable automatic rollback on failure
        """
        self.max_concurrent = max_concurrent
        self.enable_rollback = enable_rollback
        self.execution_history: List[Dict[str, Any]] = []

        logger.info("action_executor_initialized", max_concurrent=max_concurrent)

    async def execute(
        self,
        actions: List[AbilityRequest],
        ability_map: Dict[str, Any],
        parallel: bool = False,
    ) -> List[ActionResult]:
        """
        Execute a list of actions.

        Args:
            actions: List of ability requests
            ability_map: Map of ability name to ability instance
            parallel: Whether to execute in parallel

        Returns:
            List of action results
        """
        if not actions:
            return []

        logger.info("executing_actions", count=len(actions), parallel=parallel)

        if parallel:
            results = await self._execute_parallel(actions, ability_map)
        else:
            results = await self._execute_sequential(actions, ability_map)

        # Log execution
        self._log_execution(actions, results)

        # Check for failures and rollback if enabled
        if self.enable_rollback and any(r.status == ActionStatus.FAILED for r in results):
            await self._rollback(actions, results, ability_map)

        return results

    async def _execute_sequential(
        self,
        actions: List[AbilityRequest],
        ability_map: Dict[str, Any],
    ) -> List[ActionResult]:
        """Execute actions sequentially."""
        results = []

        for action in actions:
            result = await self._execute_single(action, ability_map)
            results.append(result)

            # Stop on first failure if rollback is disabled
            if not self.enable_rollback and result.status == ActionStatus.FAILED:
                break

        return results

    async def _execute_parallel(
        self,
        actions: List[AbilityRequest],
        ability_map: Dict[str, Any],
    ) -> List[ActionResult]:
        """Execute actions in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def execute_with_semaphore(action: AbilityRequest) -> ActionResult:
            async with semaphore:
                return await self._execute_single(action, ability_map)

        tasks = [execute_with_semaphore(action) for action in actions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        processed_results: List[ActionResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ActionResult(
                        action_type=actions[i].ability_name,
                        status=ActionStatus.FAILED,
                        error=str(result),
                    )
                )
            elif isinstance(result, ActionResult):
                processed_results.append(result)

        return processed_results

    async def _execute_single(
        self,
        action: AbilityRequest,
        ability_map: Dict[str, Any],
    ) -> ActionResult:
        """Execute a single action."""
        try:
            ability = ability_map.get(action.ability_name)
            if not ability:
                return ActionResult(
                    action_type=action.ability_name,
                    status=ActionStatus.FAILED,
                    error=f"Ability not found: {action.ability_name}",
                )

            logger.info("executing_action", ability=action.ability_name, action=action.action)

            response: AbilityResponse = await ability.execute(action)

            return ActionResult(
                action_type=action.ability_name,
                status=ActionStatus.SUCCESS if response.success else ActionStatus.FAILED,
                message=response.message,
                data=response.data,
                error=response.error,
            )

        except Exception as e:
            logger.error(
                "action_execution_failed",
                ability=action.ability_name,
                error=str(e),
            )
            return ActionResult(
                action_type=action.ability_name,
                status=ActionStatus.FAILED,
                error=str(e),
            )

    async def _rollback(
        self,
        actions: List[AbilityRequest],
        results: List[ActionResult],
        ability_map: Dict[str, Any],
    ) -> None:
        """
        Rollback successfully executed actions.

        Args:
            actions: Original actions
            results: Execution results
            ability_map: Ability instances
        """
        logger.warning("rolling_back_actions")

        # Find successfully executed actions
        successful_indices = [i for i, r in enumerate(results) if r.status == ActionStatus.SUCCESS]

        # Rollback in reverse order
        for i in reversed(successful_indices):
            action = actions[i]
            ability = ability_map.get(action.ability_name)

            if ability and hasattr(ability, "rollback"):
                try:
                    await ability.rollback(action)
                    logger.info("action_rolled_back", ability=action.ability_name)
                except Exception as e:
                    logger.error(
                        "rollback_failed",
                        ability=action.ability_name,
                        error=str(e),
                    )

    def _log_execution(
        self,
        actions: List[AbilityRequest],
        results: List[ActionResult],
    ) -> None:
        """Log execution to history."""
        execution_record = {
            "actions_count": len(actions),
            "successful": sum(1 for r in results if r.status == ActionStatus.SUCCESS),
            "failed": sum(1 for r in results if r.status == ActionStatus.FAILED),
            "skipped": sum(1 for r in results if r.status == ActionStatus.SKIPPED),
        }

        self.execution_history.append(execution_record)
        logger.info("actions_executed", **execution_record)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dict with statistics
        """
        if not self.execution_history:
            return {"total_executions": 0}

        total_actions = sum(e["actions_count"] for e in self.execution_history)
        total_successful = sum(e["successful"] for e in self.execution_history)
        total_failed = sum(e["failed"] for e in self.execution_history)

        return {
            "total_executions": len(self.execution_history),
            "total_actions": total_actions,
            "successful": total_successful,
            "failed": total_failed,
            "success_rate": (total_successful / total_actions if total_actions > 0 else 0),
        }

    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()
