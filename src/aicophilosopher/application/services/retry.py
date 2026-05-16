"""Retry utility with exponential backoff (T-077).

Provides a decorator and async helper for retrying external API calls
with configurable exponential backoff, max attempts, and escalation
on persistent failure.

Spec §7.3: max 3 retries, exponential backoff, escalation to coordinator.

Note: This module is ready for integration into LLM/search adapters.
Wire at call sites by wrapping API calls with retry_call() or @with_retry.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")

# max_attempts=4 means first attempt + 3 retries after failure
DEFAULT_MAX_ATTEMPTS = 4
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_MAX_DELAY = 30.0  # seconds
RETRYABLE_EXCEPTIONS = (OSError, ConnectionError, TimeoutError, RuntimeError)

EscalationCallback = (
    Callable[[str, int, BaseException], Any]
    | Callable[[str, int, BaseException], Awaitable[Any]]
)


def _validate_max_attempts(max_attempts: int) -> None:
    if max_attempts < 1:
        raise ValueError(
            f"max_attempts must be >= 1, got {max_attempts}"
        )


async def _retry_loop(
    *,
    attempt_fn: Callable[[], Awaitable[T]],
    max_attempts: int,
    base_delay: float,
    backoff_factor: float,
    max_delay: float,
    retryable: tuple[type[BaseException], ...],
    escalation_callback: EscalationCallback | None,
    name: str,
) -> T:
    """Shared retry loop used by both retry_call and @with_retry."""
    _validate_max_attempts(max_attempts)
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await attempt_fn()
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
                        result = escalation_callback(name, max_attempts, exc)
                        if inspect.isawaitable(result):
                            await result
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


def with_retry(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    max_delay: float = DEFAULT_MAX_DELAY,
    retryable: tuple[type[BaseException], ...] = RETRYABLE_EXCEPTIONS,
    escalation_callback: EscalationCallback | None = None,
) -> Callable[[F], F]:
    """Decorator: retry an async function with exponential backoff.

    Args:
        max_attempts: Maximum total attempts (first call + retries).
            Default 4 = first attempt + 3 retries.
        base_delay: Initial delay in seconds.
        backoff_factor: Multiplier for each subsequent delay.
        max_delay: Cap on delay between retries.
        retryable: Exception types that trigger a retry.
        escalation_callback: Called on final failure with
            (function_name, attempts, last_exception). May be async.

    Returns:
        Decorated function.

    Example:
        @with_retry(max_attempts=4, base_delay=1.0)
        async def call_api(url: str) -> dict: ...
    """
    _validate_max_attempts(max_attempts)

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async def attempt() -> Any:
                return await func(*args, **kwargs)

            return await _retry_loop(
                attempt_fn=attempt,
                max_attempts=max_attempts,
                base_delay=base_delay,
                backoff_factor=backoff_factor,
                max_delay=max_delay,
                retryable=retryable,
                escalation_callback=escalation_callback,
                name=func.__name__,
            )

        return wrapper  # type: ignore[return-value]

    return decorator


async def retry_call(
    coro_factory: Callable[[], Awaitable[T]],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    max_delay: float = DEFAULT_MAX_DELAY,
    retryable: tuple[type[BaseException], ...] = RETRYABLE_EXCEPTIONS,
    escalation_callback: EscalationCallback | None = None,
    name: str = "unknown",
) -> T:
    """Retry an async callable with exponential backoff.

    Args:
        coro_factory: Zero-argument callable returning a coroutine.
        max_attempts: Maximum total attempts (first + retries).
            Default 4 = first attempt + 3 retries.
        base_delay: Initial delay in seconds.
        backoff_factor: Delay multiplier per attempt.
        max_delay: Maximum delay cap.
        retryable: Exception types to retry on.
        escalation_callback: Called on final failure. May be async.
        name: Human-readable name for logging.

    Returns:
        Result of the successful coroutine call (type-preserving).

    Raises:
        ValueError: If max_attempts < 1.
        The last exception after max_attempts exhausted.
    """
    _validate_max_attempts(max_attempts)

    return await _retry_loop(
        attempt_fn=coro_factory,
        max_attempts=max_attempts,
        base_delay=base_delay,
        backoff_factor=backoff_factor,
        max_delay=max_delay,
        retryable=retryable,
        escalation_callback=escalation_callback,
        name=name,
    )
