"""Rate limiting middleware using token bucket algorithm.

Provides Redis-backed rate limiting with configurable limits per user tier.
"""

import time
from typing import Optional, Tuple

import redis.asyncio as redis


class RateLimiter:
    """Token bucket rate limiter using Redis.

    Features:
    - Distributed rate limiting across multiple API instances
    - Sliding window for fair limiting
    - Configurable per-key limits
    - Atomic operations for consistency
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "friday:ratelimit:",
    ):
        self.redis_url = redis_url
        self.prefix = prefix
        self._redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection."""
        self._redis = redis.from_url(
            self.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()

    def _make_key(self, identifier: str) -> str:
        """Generate Redis key for rate limit."""
        return f"{self.prefix}{identifier}"

    async def is_allowed(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """Check if request is allowed under rate limit.

        Uses sliding window counter algorithm for accuracy.

        Args:
            identifier: Unique identifier (e.g., user_id:endpoint)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if not self._redis:
            # Fail open if Redis unavailable
            return True, 0

        key = self._make_key(identifier)
        now = time.time()
        window_start = now - window_seconds

        # Use Redis pipeline for atomic operations
        pipe = self._redis.pipeline()

        # Remove old entries outside window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiry on the key
        pipe.expire(key, window_seconds)

        results = await pipe.execute()
        current_count = results[1]

        if current_count <= max_requests:
            return True, 0

        # Rate limit exceeded, calculate retry after
        # Get oldest request in window
        oldest = await self._redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            retry_after = int(oldest[0][1] + window_seconds - now)
            retry_after = max(1, retry_after)
        else:
            retry_after = window_seconds

        # Remove the request we just added (it exceeded limit)
        await self._redis.zrem(key, str(now))

        return False, retry_after

    async def get_current_count(self, identifier: str) -> int:
        """Get current request count for an identifier."""
        if not self._redis:
            return 0

        key = self._make_key(identifier)
        return await self._redis.zcard(key)

    async def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        if not self._redis:
            return

        key = self._make_key(identifier)
        await self._redis.delete(key)
