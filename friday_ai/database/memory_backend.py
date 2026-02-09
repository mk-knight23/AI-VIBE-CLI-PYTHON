"""In-memory session storage fallback for when Redis is unavailable.

This is a simple in-memory implementation for development and testing.
NOT for production use - data is lost on restart.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from friday_ai.database.redis_backend import SessionData

logger = logging.getLogger(__name__)


class MemorySessionBackend:
    """In-memory session storage for development.

    WARNING: Data is lost when the server restarts.
    Use Redis for production deployments.
    """

    def __init__(self, default_ttl: int = 86400):
        self.default_ttl = default_ttl
        self._sessions: Dict[str, SessionData] = {}
        self._user_sessions: Dict[str, set] = {}
        self._expires: Dict[str, datetime] = {}

    async def connect(self) -> None:
        """No-op for memory backend."""
        logger.info("Using in-memory session backend (data will be lost on restart)")

    async def close(self) -> None:
        """Clear all sessions."""
        self._sessions.clear()
        self._user_sessions.clear()
        self._expires.clear()

    async def ping(self) -> bool:
        """Always returns True."""
        return True

    def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        now = datetime.now(timezone.utc)
        expired = [
            sid for sid, exp in self._expires.items()
            if exp < now
        ]
        for sid in expired:
            self._delete_session(sid)

    def _delete_session(self, session_id: str) -> None:
        """Internal delete without cleanup."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            del self._sessions[session_id]
            del self._expires[session_id]
            if session.user_id in self._user_sessions:
                self._user_sessions[session.user_id].discard(session_id)

    async def save(self, session: SessionData) -> None:
        """Save session to memory."""
        self._cleanup_expired()

        session.updated_at = datetime.now(timezone.utc)
        self._sessions[session.id] = session
        self._expires[session.id] = datetime.now(timezone.utc) + timedelta(seconds=self.default_ttl)

        if session.user_id not in self._user_sessions:
            self._user_sessions[session.user_id] = set()
        self._user_sessions[session.user_id].add(session.id)

    async def load(self, session_id: str) -> Optional[SessionData]:
        """Load session from memory."""
        self._cleanup_expired()

        if session_id not in self._sessions:
            return None

        # Check if expired
        if datetime.now(timezone.utc) > self._expires.get(session_id, datetime.min.replace(tzinfo=timezone.utc)):
            self._delete_session(session_id)
            return None

        return self._sessions.get(session_id)

    async def delete(self, session_id: str) -> bool:
        """Delete session from memory."""
        if session_id in self._sessions:
            self._delete_session(session_id)
            return True
        return False

    async def list_user_sessions(self, user_id: str) -> List[str]:
        """List all session IDs for a user."""
        self._cleanup_expired()
        return list(self._user_sessions.get(user_id, set()))

    async def touch(self, session_id: str) -> bool:
        """Refresh TTL for a session."""
        if session_id in self._sessions:
            self._expires[session_id] = datetime.now(timezone.utc) + timedelta(seconds=self.default_ttl)
            return True
        return False
