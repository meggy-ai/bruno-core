"""Tests for ActionExecutor."""

import pytest

from bruno_core.base.executor import ActionExecutor
from bruno_core.models.ability import AbilityRequest
from bruno_core.models.response import ActionStatus
from tests.conftest import MockAbility


@pytest.mark.asyncio
class TestActionExecutor:
    """Tests for ActionExecutor class."""

    async def test_execute_single_action(self):
        """Test executing a single action."""
        executor = ActionExecutor()
        ability = MockAbility()
        await ability.initialize()

        actions = [
            AbilityRequest(
                ability_name="mock",
                action="test",
                parameters={},
                user_id="test-user",
            )
        ]

        ability_map = {"mock": ability}
        results = await executor.execute(actions, ability_map)

        assert len(results) == 1
        assert results[0].status == ActionStatus.SUCCESS

    async def test_execute_sequential(self):
        """Test sequential execution."""
        executor = ActionExecutor()
        ability = MockAbility()
        await ability.initialize()

        actions = [
            AbilityRequest(
                ability_name="mock",
                action="test1",
                parameters={},
                user_id="test-user",
            ),
            AbilityRequest(
                ability_name="mock",
                action="test2",
                parameters={},
                user_id="test-user",
            ),
        ]

        ability_map = {"mock": ability}
        results = await executor.execute(actions, ability_map, parallel=False)

        assert len(results) == 2
        assert all(r.status == ActionStatus.SUCCESS for r in results)

    async def test_execute_parallel(self):
        """Test parallel execution."""
        executor = ActionExecutor(max_concurrent=2)
        ability = MockAbility()
        await ability.initialize()

        actions = [
            AbilityRequest(
                ability_name="mock",
                action=f"test{i}",
                parameters={},
                user_id="test-user",
            )
            for i in range(5)
        ]

        ability_map = {"mock": ability}
        results = await executor.execute(actions, ability_map, parallel=True)

        assert len(results) == 5
        assert all(r.status == ActionStatus.SUCCESS for r in results)

    async def test_ability_not_found(self):
        """Test handling missing ability."""
        executor = ActionExecutor()

        actions = [
            AbilityRequest(
                ability_name="nonexistent",
                action="test",
                parameters={},
                user_id="test-user",
            )
        ]

        ability_map = {}
        results = await executor.execute(actions, ability_map)

        assert len(results) == 1
        assert results[0].status == ActionStatus.FAILED
        assert "not found" in results[0].error.lower()

    async def test_get_statistics(self):
        """Test execution statistics."""
        executor = ActionExecutor()
        ability = MockAbility()
        await ability.initialize()

        actions = [
            AbilityRequest(
                ability_name="mock",
                action="test",
                parameters={},
                user_id="test-user",
            )
        ]

        ability_map = {"mock": ability}
        await executor.execute(actions, ability_map)

        stats = executor.get_statistics()
        assert stats["total_executions"] == 1
        assert stats["successful"] == 1
        assert stats["failed"] == 0

    async def test_clear_history(self):
        """Test clearing execution history."""
        executor = ActionExecutor()
        ability = MockAbility()
        await ability.initialize()

        actions = [
            AbilityRequest(
                ability_name="mock",
                action="test",
                parameters={},
                user_id="test-user",
            )
        ]

        ability_map = {"mock": ability}
        await executor.execute(actions, ability_map)

        executor.clear_history()
        stats = executor.get_statistics()
        assert stats["total_executions"] == 0
