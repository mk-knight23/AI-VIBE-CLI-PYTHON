"""Redis-backed session storage for Friday AI.

Provides production-grade session persistence with:
- JSON serialization (secure, no pickle)
- Compression for large sessions
- TTL-based expiration
- Connection pooling
"""

import json
import zlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class SessionData(BaseModel):
    """Session data model."""

    id: str
    user_id: str
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    messages: List[Dict[str, Any]] = Field(default_factory=list)


class RedisSessionBackend:
    """Production-grade Redis session storage.

    Features:
    - Connection pooling via redis.asyncio
    - Automatic compression for large sessions (>1KB)
    - Configurable TTL with automatic refresh
    - Atomic operations where possible
    """

    # Compression flag bytes
    COMPRESSED_FLAG = b"\x01"
    UNCOMPRESSED_FLAG = b"\x00"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 86400,  # 24 hours
        compression_threshold: int = 1024,  # 1KB
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.compression_threshold = compression_threshold
        self.key_prefix = "friday:session:"
        self._redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection."""
        self._redis = redis.from_url(
            self.redis_url,
            decode_responses=False,  # We handle encoding manually
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        if not self._redis:
            raise RuntimeError("Redis not connected")
        return await self._redis.ping()

    def _make_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.key_prefix}{session_id}"

    def _serialize(self, data: SessionData) -> bytes:
        """Serialize session data with optional compression using JSON."""
        # Convert to dict, then JSON
        json_bytes = data.model_dump_json().encode("utf-8")

        # Compress if exceeds threshold
        if len(json_bytes) > self.compression_threshold:
            compressed = zlib.compress(json_bytes, level=6)
            return self.COMPRESSED_FLAG + compressed

        return self.UNCOMPRESSED_FLAG + json_bytes

    def _deserialize(self, data: bytes) -> SessionData:
        """Deserialize session data, handling compression."""
        if not data:
            raise ValueError("Empty data")

        flag = data[:1]
        payload = data[1:]

        if flag == self.COMPRESSED_FLAG:
            payload = zlib.decompress(payload)

        # Parse JSON and create SessionData
        return SessionData.model_validate_json(payload)

    async def save(self, session: SessionData) -> None:
        """Save session to Redis.

        Args:
            session: Session data to save
        """
        if not self._redis:
            raise RuntimeError("Redis not connected")

        key = self._make_key(session.id)
        user_sessions_key = f"friday:user:{session.user_id}:sessions"

        # Update timestamp
        session.updated_at = datetime.now(timezone.utc)

        # Serialize and store
        data = self._serialize(session)

        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.setex(key, self.default_ttl, data)
            pipe.sadd(user_sessions_key, session.id)
            await pipe.execute()

    async def load(self, session_id: str) -> Optional[SessionData]:
        """Load session from Redis.

        Args:
            session_id: Session ID to load

        Returns:
            Session data or None if not found
        """
        if not self._redis:
            raise RuntimeError("Redis not connected")

        key = self._make_key(session_id)
        data = await self._redis.get(key)

        if not data:
            return None

        try:
            return self._deserialize(data)
        except Exception:
            # Log error and return None for corrupted data
            return None

    async def delete(self, session_id: str) -> bool:
        """Delete session from Redis.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        if not self._redis:
            raise RuntimeError("Redis not connected")

        # Get session first to remove from user index
        session = await self.load(session_id)
        if session:
            await self._redis.srem(f"friday:user:{session.user_id}:sessions", session_id)

        key = self._make_key(session_id)
        result = await self._redis.delete(key)
        return result > 0

    async def list_user_sessions(self, user_id: str) -> List[str]:
        """List all session IDs for a user.

        Args:
            user_id: User ID

        Returns:
            List of session IDs
        """
        if not self._redis:
            raise RuntimeError("Redis not connected")

        sessions = await self._redis.smembers(f"friday:user:{user_id}:sessions")
        return [s.decode() if isinstance(s, bytes) else s for s in sessions]

    async def touch(self, session_id: str) -> bool:
        """Refresh TTL for a session.

        Args:
            session_id: Session ID to refresh

        Returns:
            True if refreshed, False if not found
        """
        if not self._redis:
            raise RuntimeError("Redis not connected")

        key = self._make_key(session_id)
        return await self._redis.expire(key, self.default_ttl)
