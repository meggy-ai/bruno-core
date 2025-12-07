"""Tests for registry system."""

import pytest

from bruno_core.registry.ability_registry import AbilityRegistry
from bruno_core.registry.llm_registry import LLMProviderRegistry
from bruno_core.registry.memory_registry import MemoryBackendRegistry
from tests.conftest import MockAbility, MockLLM, MockMemory


class TestAbilityRegistry:
    """Tests for AbilityRegistry."""

    def test_register_ability(self):
        """Test registering an ability."""
        registry = AbilityRegistry()

        registry.register(
            name="test-ability",
            plugin_class=MockAbility,
            version="1.0.0",
        )

        assert registry.has_plugin("test-ability")
        assert "test-ability" in registry.list_plugins()

    def test_get_ability_instance(self):
        """Test getting ability instance."""
        registry = AbilityRegistry()
        registry.register("test", MockAbility)

        instance = registry.get_instance("test")
        assert isinstance(instance, MockAbility)
        assert instance.name == "mock"  # Default name

    def test_unregister_ability(self):
        """Test unregistering ability."""
        registry = AbilityRegistry()
        registry.register("test", MockAbility)

        registry.unregister("test")
        assert not registry.has_plugin("test")

    def test_validate_plugin(self):
        """Test plugin validation."""
        registry = AbilityRegistry()

        assert registry.validate_plugin(MockAbility) is True
        assert registry.validate_plugin(str) is False

    def test_list_plugins(self):
        """Test listing plugins."""
        registry = AbilityRegistry()
        registry.register("ability1", MockAbility)
        registry.register("ability2", MockAbility)

        plugins = registry.list_plugins()
        assert len(plugins) == 2
        assert "ability1" in plugins
        assert "ability2" in plugins

    def test_clear_registry(self):
        """Test clearing registry."""
        registry = AbilityRegistry()
        registry.register("test", MockAbility)

        registry.clear()
        assert len(registry.list_plugins()) == 0


class TestLLMProviderRegistry:
    """Tests for LLMProviderRegistry."""

    def test_register_llm_provider(self):
        """Test registering LLM provider."""
        registry = LLMProviderRegistry()

        registry.register(
            name="mock-llm",
            plugin_class=MockLLM,
        )

        assert registry.has_plugin("mock-llm")

    def test_get_llm_instance(self):
        """Test getting LLM instance."""
        registry = LLMProviderRegistry()
        registry.register("mock", MockLLM)

        instance = registry.get_instance("mock")
        assert isinstance(instance, MockLLM)

    def test_validate_llm_plugin(self):
        """Test LLM plugin validation."""
        registry = LLMProviderRegistry()

        assert registry.validate_plugin(MockLLM) is True
        assert registry.validate_plugin(MockAbility) is False


class TestMemoryBackendRegistry:
    """Tests for MemoryBackendRegistry."""

    def test_register_memory_backend(self):
        """Test registering memory backend."""
        registry = MemoryBackendRegistry()

        registry.register(
            name="mock-memory",
            plugin_class=MockMemory,
        )

        assert registry.has_plugin("mock-memory")

    def test_get_memory_instance(self):
        """Test getting memory instance."""
        registry = MemoryBackendRegistry()
        registry.register("mock", MockMemory)

        instance = registry.get_instance("mock")
        assert isinstance(instance, MockMemory)

    def test_validate_memory_plugin(self):
        """Test memory plugin validation."""
        registry = MemoryBackendRegistry()

        assert registry.validate_plugin(MockMemory) is True
        assert registry.validate_plugin(MockLLM) is False

    def test_get_all_plugins(self):
        """Test getting all plugins."""
        registry = MemoryBackendRegistry()
        registry.register("mem1", MockMemory)
        registry.register("mem2", MockMemory)

        all_plugins = registry.get_all_plugins()
        assert len(all_plugins) == 2
        assert "mem1" in all_plugins
        assert "mem2" in all_plugins
