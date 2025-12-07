"""
Async utilities for bruno-core.

Provides helpers for async/await operations.
"""

import asyncio
from typing import Any, Callable, Coroutine, List, Optional, TypeVar

T = TypeVar("T")


async def run_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    default: Optional[T] = None,
) -> Optional[T]:
    """
    Run a coroutine with a timeout.

    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        default: Default value to return on timeout

    Returns:
        Coroutine result or default value

    Example:
        >>> result = await run_with_timeout(some_async_function(), timeout=5.0)
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return default


async def gather_with_concurrency(
    n: int,
    *tasks: Coroutine[Any, Any, T],
) -> List[T]:
    """
    Run multiple coroutines with limited concurrency.

    Args:
        n: Maximum number of concurrent tasks
        *tasks: Coroutines to run

    Returns:
        List of results

    Example:
        >>> results = await gather_with_concurrency(3, task1(), task2(), task3())
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task: Coroutine[Any, Any, T]) -> T:
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def retry_async(
    func: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    **kwargs: Any,
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Function arguments
        max_retries: Maximum number of retries
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail

    Example:
        >>> result = await retry_async(fetch_data, url="https://api.example.com")
    """
    last_exception = None
    current_delay = delay

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                break

    if last_exception:
        raise last_exception

    raise RuntimeError("Retry failed with no exception")


async def run_in_executor(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Run a synchronous function in an executor.

    Useful for running blocking operations without blocking the event loop.

    Args:
        func: Synchronous function to run
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Example:
        >>> result = await run_in_executor(blocking_function, arg1, arg2)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def cancel_tasks(*tasks: asyncio.Task[Any]) -> None:
    """
    Cancel multiple tasks gracefully.

    Args:
        *tasks: Tasks to cancel

    Example:
        >>> await cancel_tasks(task1, task2, task3)
    """
    for task in tasks:
        if not task.done():
            task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


class AsyncContextManager:
    """
    Base class for async context managers.

    Example:
        >>> class MyResource(AsyncContextManager):
        ...     async def __aenter__(self):
        ...         # Setup code
        ...         return self
        ...     async def __aexit__(self, exc_type, exc, tb):
        ...         # Cleanup code
        ...         pass
    """

    async def __aenter__(self) -> "AsyncContextManager":
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Exit async context."""
        pass
