"""Retry utility with exponential backoff (T-077).

Provides a decorator and async helper for retrying external API calls
with configurable exponential backoff, max attempts, and escalation
on persistent failure.

Spec §7.3: max 3 retries, exponential backoff, escalation to coordinator.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_MAX_DELAY = 30.0  # seconds
RETRYABLE_EXCEPTIONS = (OSError, ConnectionError, TimeoutError, RuntimeError)


def with_retry(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    max_delay: float = DEFAULT_MAX_DELAY,
    retryable: tuple[type[BaseException], ...] = RETRYABLE_EXCEPTIONS,
    escalation_callback: Callable[[str, int, Exception], Any] | None = None,
) -> Callable[[F], F]:
    """Decorator: retry a function with exponential backoff.

    Args:
        max_attempts: Maximum total attempts (including the first call).
        base_delay: Initial delay in seconds.
        backoff_factor: Multiplier for each subsequent delay.
        max_delay: Cap on delay between retries.
        retryable: Exception types that trigger a retry.
        escalation_callback: Called on final failure with
            (function_name, attempts, last_exception).

    Returns:
        Decorated function.

    Example:
        @with_retry(max_attempts=3, base_delay=1.0)
        async def call_external_api(url: str) -> dict: ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.error(
                            "Retry exhausted for %s after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            exc,
                        )
                        if escalation_callback:
                            try:
                                escalation_callback(
                                    func.__name__, max_attempts, exc
                                )
                            except Exception as cb_exc:
                                logger.warning(
                                    "Escalation callback failed: %s", cb_exc
                                )
                        raise
                    delay = min(
                        base_delay * (backoff_factor ** (attempt - 1)),
                        max_delay,
                    )
                    logger.warning(
                        "Retry %d/%d for %s after %.1fs: %s",
                        attempt + 1,
                        max_attempts,
                        func.__name__,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
            # Should not reach here; satisfies type checker
            if last_exc:
                raise last_exc
            raise RuntimeError("Retry exhausted with unknown error")

        return wrapper  # type: ignore[return-value]

    return decorator


async def retry_call(
    coro_factory: Callable[[], Any],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    max_delay: float = DEFAULT_MAX_DELAY,
    retryable: tuple[type[BaseException], ...] = RETRYABLE_EXCEPTIONS,
    escalation_callback: Callable[[str, int, Exception], Any] | None = None,
    name: str = "unknown",
) -> Any:
    """Retry an async callable with exponential backoff.

    Args:
        coro_factory: Zero-argument callable that returns a coroutine.
        max_attempts: Maximum total attempts.
        base_delay: Initial delay in seconds.
        backoff_factor: Delay multiplier per attempt.
        max_delay: Maximum delay cap.
        retryable: Exception types to retry on.
        escalation_callback: Called on final failure.
        name: Human-readable name for logging.

    Returns:
        Result of the successful coroutine call.

    Raises:
        The last exception after max_attempts exhausted.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            coro = coro_factory()
            return await coro
        except retryable as exc:
            last_exc = exc
            if attempt == max_attempts:
                logger.error(
                    "Retry exhausted for %s after %d attempts: %s",
                    name,
                    max_attempts,
                    exc,
                )
                if escalation_callback:
                    try:
                        escalation_callback(name, max_attempts, exc)
                    except Exception as cb_exc:
                        logger.warning(
                            "Escalation callback failed: %s", cb_exc
                        )
                raise
            delay = min(
                base_delay * (backoff_factor ** (attempt - 1)),
                max_delay,
            )
            logger.warning(
                "Retry %d/%d for %s after %.1fs: %s",
                attempt + 1,
                max_attempts,
                name,
                delay,
                exc,
            )
            await asyncio.sleep(delay)
    if last_exc:
        raise last_exc
    raise RuntimeError("Retry exhausted with unknown error")
