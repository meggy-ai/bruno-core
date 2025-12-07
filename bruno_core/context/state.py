"""
State Manager implementation.

Manages persistent state storage and retrieval for conversations and sessions.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from bruno_core.utils.exceptions import StateError
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class StateManager:
    """
    Manages persistent state storage for conversations and sessions.

    Features:
    - Key-value state storage
    - JSON serialization
    - File-based or in-memory storage
    - Namespace support
    - Atomic writes

    Example:
        >>> manager = StateManager(storage_path="./state")
        >>> await manager.set_state("user_123", "preferences", {"theme": "dark"})
        >>> prefs = await manager.get_state("user_123", "preferences")
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        use_memory: bool = False,
    ):
        """
        Initialize state manager.

        Args:
            storage_path: Path to state storage directory (None for temp)
            use_memory: Use in-memory storage instead of files
        """
        self.use_memory = use_memory
        self._memory_store: Dict[str, Dict[str, Any]] = {}

        if not use_memory:
            self.storage_path = Path(storage_path) if storage_path else Path("./bruno_state")
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.info("state_manager_initialized", storage_path=str(self.storage_path))
        else:
            self.storage_path = None
            logger.info("state_manager_initialized", mode="in-memory")

    async def set_state(
        self,
        namespace: str,
        key: str,
        value: Any,
    ) -> None:
        """
        Set state value.

        Args:
            namespace: State namespace (e.g., user_id, conversation_id)
            key: State key
            value: State value (must be JSON serializable)

        Raises:
            StateError: If storage fails
        """
        try:
            if self.use_memory:
                if namespace not in self._memory_store:
                    self._memory_store[namespace] = {}
                self._memory_store[namespace][key] = value
            else:
                # File-based storage
                namespace_dir = self.storage_path / namespace
                namespace_dir.mkdir(exist_ok=True)

                state_file = namespace_dir / f"{key}.json"
                
                # Write atomically
                temp_file = state_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(value, f, indent=2, ensure_ascii=False)
                
                temp_file.replace(state_file)

            logger.debug("state_set", namespace=namespace, key=key)

        except Exception as e:
            logger.error(
                "state_set_failed",
                namespace=namespace,
                key=key,
                error=str(e),
            )
            raise StateError(
                "Failed to set state",
                details={"namespace": namespace, "key": key},
                cause=e,
            )

    async def get_state(
        self,
        namespace: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Get state value.

        Args:
            namespace: State namespace
            key: State key
            default: Default value if not found

        Returns:
            State value or default
        """
        try:
            if self.use_memory:
                return self._memory_store.get(namespace, {}).get(key, default)
            else:
                state_file = self.storage_path / namespace / f"{key}.json"
                
                if not state_file.exists():
                    return default

                with open(state_file, "r", encoding="utf-8") as f:
                    value = json.load(f)

                logger.debug("state_retrieved", namespace=namespace, key=key)
                return value

        except Exception as e:
            logger.error(
                "state_get_failed",
                namespace=namespace,
                key=key,
                error=str(e),
            )
            return default

    async def delete_state(
        self,
        namespace: str,
        key: str,
    ) -> bool:
        """
        Delete state value.

        Args:
            namespace: State namespace
            key: State key

        Returns:
            True if deleted, False if not found
        """
        try:
            if self.use_memory:
                if namespace in self._memory_store and key in self._memory_store[namespace]:
                    del self._memory_store[namespace][key]
                    logger.debug("state_deleted", namespace=namespace, key=key)
                    return True
                return False
            else:
                state_file = self.storage_path / namespace / f"{key}.json"
                
                if state_file.exists():
                    state_file.unlink()
                    logger.debug("state_deleted", namespace=namespace, key=key)
                    return True
                return False

        except Exception as e:
            logger.error(
                "state_delete_failed",
                namespace=namespace,
                key=key,
                error=str(e),
            )
            return False

    async def list_keys(self, namespace: str) -> list[str]:
        """
        List all keys in a namespace.

        Args:
            namespace: State namespace

        Returns:
            List of keys
        """
        try:
            if self.use_memory:
                return list(self._memory_store.get(namespace, {}).keys())
            else:
                namespace_dir = self.storage_path / namespace
                
                if not namespace_dir.exists():
                    return []

                keys = [
                    f.stem
                    for f in namespace_dir.glob("*.json")
                ]
                return keys

        except Exception as e:
            logger.error("list_keys_failed", namespace=namespace, error=str(e))
            return []

    async def clear_namespace(self, namespace: str) -> int:
        """
        Clear all state in a namespace.

        Args:
            namespace: State namespace

        Returns:
            Number of keys deleted
        """
        try:
            if self.use_memory:
                if namespace in self._memory_store:
                    count = len(self._memory_store[namespace])
                    del self._memory_store[namespace]
                    logger.info("namespace_cleared", namespace=namespace, count=count)
                    return count
                return 0
            else:
                namespace_dir = self.storage_path / namespace
                
                if not namespace_dir.exists():
                    return 0

                count = 0
                for state_file in namespace_dir.glob("*.json"):
                    state_file.unlink()
                    count += 1

                # Remove directory if empty
                if not any(namespace_dir.iterdir()):
                    namespace_dir.rmdir()

                logger.info("namespace_cleared", namespace=namespace, count=count)
                return count

        except Exception as e:
            logger.error("clear_namespace_failed", namespace=namespace, error=str(e))
            return 0

    async def list_namespaces(self) -> list[str]:
        """
        List all namespaces.

        Returns:
            List of namespace names
        """
        try:
            if self.use_memory:
                return list(self._memory_store.keys())
            else:
                if not self.storage_path.exists():
                    return []

                namespaces = [
                    d.name
                    for d in self.storage_path.iterdir()
                    if d.is_dir()
                ]
                return namespaces

        except Exception as e:
            logger.error("list_namespaces_failed", error=str(e))
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get state manager statistics.

        Returns:
            Dict with statistics
        """
        try:
            if self.use_memory:
                total_keys = sum(len(ns) for ns in self._memory_store.values())
                return {
                    "mode": "in-memory",
                    "namespaces": len(self._memory_store),
                    "total_keys": total_keys,
                }
            else:
                namespaces = 0
                total_keys = 0
                
                if self.storage_path.exists():
                    for namespace_dir in self.storage_path.iterdir():
                        if namespace_dir.is_dir():
                            namespaces += 1
                            total_keys += len(list(namespace_dir.glob("*.json")))

                return {
                    "mode": "file-based",
                    "storage_path": str(self.storage_path),
                    "namespaces": namespaces,
                    "total_keys": total_keys,
                }

        except Exception as e:
            logger.error("get_statistics_failed", error=str(e))
            return {"error": str(e)}
