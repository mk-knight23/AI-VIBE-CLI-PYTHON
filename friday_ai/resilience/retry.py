"""Retry policies with exponential backoff for Friday AI.

Provides configurable retry logic with circuit breaker integration,
jitter, and budget-based retry limits.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, TypeVar

from friday_ai.utils.errors import (
    ConnectionError,
    FridayError,
    RateLimitError,
    RetryExhaustedError,
    TimeoutError,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Exponential backoff multiplier
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Exception types that trigger retry
        on_retry: Optional callback on each retry attempt
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_max: float = 0.1  # Max jitter as fraction of delay
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (
            ConnectionError,
            TimeoutError,
            RateLimitError,
            OSError,
            TimeoutError,
        )
    )
    on_retry: Callable[[int, Exception, float], None] | None = None


@dataclass
class RetryStats:
    """Statistics for retry operations."""

    attempts: int = 0
    failures: int = 0
    total_delay: float = 0.0
    success: bool = False
    last_error: Exception | None = None


@dataclass
class RetryContext:
    """Context for a retry operation."""

    attempt: int = 0
    start_time: float = field(default_factory=time.time)
    config: RetryConfig = field(default_factory=RetryConfig)
    stats: RetryStats = field(default_factory=RetryStats)

    def calculate_delay(self) -> float:
        """Calculate delay for next retry attempt."""
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** self.attempt),
            self.config.max_delay,
        )

        if self.config.jitter:
            # Add random jitter (±10% by default)
            jitter_amount = delay * self.config.jitter_max
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)


class RetryBudget:
    """Budget-based retry limiting to prevent retry storms.

    Maintains a token bucket for retry attempts. Each retry consumes
tokens; when depleted, retries are rejected.

    Attributes:
        max_tokens: Maximum tokens in bucket
        refill_rate: Tokens added per second
        min_threshold: Minimum tokens required for retry
    """

    def __init__(
        self,
        max_tokens: float = 100.0,
        refill_rate: float = 10.0,
        min_threshold: float = 1.0,
    ):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.min_threshold = min_threshold
        self._tokens = max_tokens
        self._last_refill = time.time()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_tokens, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        """Attempt to consume tokens from budget.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient budget
        """
        self._refill()

        if self._tokens - tokens >= self.min_threshold:
            self._tokens -= tokens
            return True
        return False

    def get_balance(self) -> float:
        """Get current token balance."""
        self._refill()
        return self._tokens


class RetryPolicy:
    """Retry policy with exponential backoff.

    Example:
        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay=1.0))

        @policy.retry
        async def fetch_data():
            return await http_client.get("https://api.example.com/data")

        # Or use as context manager
        async with policy.context() as ctx:
            return await fetch_data()
    """

    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()
        self._budget = RetryBudget()
        self._stats: list[RetryStats] = []

    def is_retryable(self, error: Exception) -> bool:
        """Check if an exception should trigger a retry."""
        # Check for retryable error types
        if isinstance(error, self.config.retryable_exceptions):
            return True

        # Check for FridayError with retryable flag
        if isinstance(error, FridayError) and error.retryable:
            return True

        return False

    async def execute(
        self,
        fn: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function with retry logic.

        Args:
            fn: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RetryExhaustedError: If all retries exhausted
            Exception: Original exception if not retryable
        """
        ctx = RetryContext(config=self.config)
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            ctx.attempt = attempt
            ctx.stats.attempts += 1

            try:
                result = await fn(*args, **kwargs)
                ctx.stats.success = True
                self._stats.append(ctx.stats)
                return result

            except Exception as e:
                last_error = e
                ctx.stats.last_error = e
                ctx.stats.failures += 1

                # Check if we should retry
                if attempt >= self.config.max_retries:
                    logger.debug(f"Max retries ({self.config.max_retries}) exceeded")
                    break

                if not self.is_retryable(e):
                    logger.debug(f"Exception not retryable: {type(e).__name__}")
                    raise

                # Check retry budget
                if not self._budget.consume():
                    logger.warning("Retry budget depleted")
                    break

                # Calculate and apply delay
                delay = ctx.calculate_delay()
                ctx.stats.total_delay += delay

                logger.info(
                    f"Retry {attempt + 1}/{self.config.max_retries} after "
                    f"{delay:.2f}s delay: {type(e).__name__}: {e}"
                )

                # Call retry callback if provided
                if self.config.on_retry:
                    try:
                        self.config.on_retry(attempt, e, delay)
                    except Exception as cb_error:
                        logger.warning(f"Retry callback failed: {cb_error}")

                await asyncio.sleep(delay)

        # All retries exhausted
        self._stats.append(ctx.stats)
        raise RetryExhaustedError(
            message=f"All {self.config.max_retries} retry attempts exhausted",
            attempts=ctx.stats.attempts,
            last_error=last_error,
        ) from last_error

    def retry(
        self,
        fn: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        """Decorator to add retry logic to an async function.

        Args:
            fn: Async function to wrap

        Returns:
            Wrapped function with retry logic
        """
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.execute(fn, *args, **kwargs)

        return wrapper

    def get_stats(self) -> list[RetryStats]:
        """Get statistics for all retry operations."""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats.clear()


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
    jitter: bool = True,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """Decorator factory for simple retry configuration.

    Example:
        @with_retry(max_retries=3, base_delay=2.0)
        async def fetch_data():
            return await http.get(url)
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        jitter=jitter,
    )
    if retryable_exceptions:
        config.retryable_exceptions = retryable_exceptions

    policy = RetryPolicy(config)
    return policy.retry


def retry(
    max_retries: int = 3,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    delay: float = 1.0,
    backoff: float = 2.0,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """Simple retry decorator (legacy API).

    Args:
        max_retries: Maximum retry attempts
        exceptions: Exception types to catch
        delay: Initial delay between retries
        backoff: Backoff multiplier

    Returns:
        Decorator function
    """
    def decorator(fn: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_error: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt >= max_retries:
                        raise

                    logger.info(f"Retry {attempt + 1}/{max_retries} after {current_delay}s: {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            raise last_error or Exception("Retry failed")

        return wrapper
    return decorator
