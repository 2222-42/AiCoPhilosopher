"""Unit tests for retry utility (T-077)."""

from __future__ import annotations

import asyncio

import pytest

from aicophilosopher.application.services.retry import (
    DEFAULT_MAX_ATTEMPTS,
    retry_call,
    with_retry,
)


class TestRetryCall:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self) -> None:
        call_count = 0

        async def succeed() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_call(lambda: succeed(), max_attempts=4)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self) -> None:
        call_count = 0

        async def fail_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("transient")
            return "recovered"

        result = await retry_call(
            lambda: fail_then_succeed(), max_attempts=4, base_delay=0.01
        )
        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exhausts_retries_and_raises(self) -> None:
        """Default max_attempts=4 means first attempt + 3 retries."""
        call_count = 0

        async def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("persistent")

        with pytest.raises(ConnectionError, match="persistent"):
            await retry_call(
                lambda: always_fail(), max_attempts=4, base_delay=0.01
            )
        assert call_count == 4  # 1 first + 3 retries

    @pytest.mark.asyncio
    async def test_custom_max_attempts(self) -> None:
        call_count = 0

        async def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        with pytest.raises(ConnectionError):
            await retry_call(
                lambda: always_fail(), max_attempts=2, base_delay=0.01
            )
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_exception_raised_immediately(self) -> None:
        call_count = 0

        async def value_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError, match="not retryable"):
            await retry_call(lambda: value_error(), max_attempts=4, base_delay=0.01)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_delay_capped_at_max(self) -> None:
        call_count = 0

        async def fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("fail")
            return "ok"

        result = await retry_call(
            lambda: fail_twice(),
            max_attempts=4,
            base_delay=0.01,
            backoff_factor=10.0,
            max_delay=0.02,
        )
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_escalation_callback_called_on_exhaustion(self) -> None:
        escalation_log: list[tuple[str, int, BaseException]] = []

        def on_escalation(name: str, attempts: int, exc: BaseException) -> None:
            escalation_log.append((name, attempts, exc))

        async def always_fail() -> str:
            raise ConnectionError("dead")

        with pytest.raises(ConnectionError):
            await retry_call(
                lambda: always_fail(),
                max_attempts=2,
                base_delay=0.01,
                escalation_callback=on_escalation,
                name="test_op",
            )
        assert len(escalation_log) == 1
        assert escalation_log[0][0] == "test_op"
        assert escalation_log[0][1] == 2

    @pytest.mark.asyncio
    async def test_async_escalation_callback(self) -> None:
        """Async escalation callbacks are awaited (Copilot review fix)."""
        escalation_log: list[tuple[str, int, BaseException]] = []

        async def async_escalation(name: str, attempts: int, exc: BaseException) -> None:
            await asyncio.sleep(0.001)
            escalation_log.append((name, attempts, exc))

        async def always_fail() -> str:
            raise ConnectionError("dead")

        with pytest.raises(ConnectionError):
            await retry_call(
                lambda: always_fail(),
                max_attempts=2,
                base_delay=0.01,
                escalation_callback=async_escalation,
                name="async_test",
            )
        assert len(escalation_log) == 1
        assert escalation_log[0][0] == "async_test"

    @pytest.mark.asyncio
    async def test_invalid_max_attempts_raises(self) -> None:
        """max_attempts < 1 should raise ValueError (Copilot review fix)."""
        async def dummy() -> str:
            return "ok"

        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            await retry_call(lambda: dummy(), max_attempts=0)

        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            await retry_call(lambda: dummy(), max_attempts=-1)

    @pytest.mark.asyncio
    async def test_default_is_four_attempts(self) -> None:
        """DEFAULT_MAX_ATTEMPTS = 4 (first attempt + 3 retries)."""
        assert DEFAULT_MAX_ATTEMPTS == 4


class TestWithRetryDecorator:
    @pytest.mark.asyncio
    async def test_decorator_retries(self) -> None:
        call_count = 0

        @with_retry(max_attempts=4, base_delay=0.01)
        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("flaky")
            return "decorated"

        result = await flaky()
        assert result == "decorated"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_exhausts(self) -> None:
        @with_retry(max_attempts=2, base_delay=0.01)
        async def dead() -> str:
            raise ConnectionError("dead")

        with pytest.raises(ConnectionError):
            await dead()

    @pytest.mark.asyncio
    async def test_decorator_three_retries(self) -> None:
        """Default max_attempts=4 means first call + 3 retries."""
        call_count = 0

        @with_retry(base_delay=0.01)
        async def flaky_three() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ConnectionError(f"fail {call_count}")
            return "finally"

        result = await flaky_three()
        assert result == "finally"
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_decorator_invalid_max_attempts(self) -> None:
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):

            @with_retry(max_attempts=0)
            async def bad() -> str:
                return "ok"  # pragma: no cover
