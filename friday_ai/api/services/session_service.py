"""Session service for API."""

import uuid
from datetime import datetime
from typing import List, Optional

from friday_ai.database.redis_backend import RedisSessionBackend, SessionData


class SessionService:
    """High-level session management service."""

    def __init__(self, redis: RedisSessionBackend):
        self.redis = redis

    async def create_session(
        self,
        user_id: str,
        name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> SessionData:
        """Create a new session."""
        session = SessionData(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name or f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            metadata=metadata or {},
        )

        await self.redis.save(session)
        return session

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID."""
        return await self.redis.load(session_id)

    async def list_user_sessions(self, user_id: str) -> List[SessionData]:
        """List all sessions for a user."""
        session_ids = await self.redis.list_user_sessions(user_id)

        sessions = []
        for sid in session_ids:
            session = await self.redis.load(sid)
            if session:
                sessions.append(session)

        return sessions

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return await self.redis.delete(session_id)

    async def update_session(
        self,
        session_id: str,
        name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[SessionData]:
        """Update session metadata."""
        session = await self.redis.load(session_id)
        if not session:
            return None

        if name is not None:
            session.name = name

        if metadata is not None:
            session.metadata.update(metadata)

        session.updated_at = datetime.utcnow()
        await self.redis.save(session)

        return session
