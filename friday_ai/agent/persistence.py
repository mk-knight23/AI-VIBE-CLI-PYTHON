"""Session persistence with async I/O for high performance under load."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles
import orjson

from friday_ai.client.response import TokenUsage
from friday_ai.config.loader import get_data_dir

logger = logging.getLogger(__name__)


@dataclass
class SessionSnapshot:
    session_id: str
    created_at: datetime
    updated_at: datetime
    turn_count: int
    messages: list[dict[str, Any]]
    total_usage: TokenUsage

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "turn_count": self.turn_count,
            "messages": self.messages,
            "total_usage": self.total_usage.__dict__,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionSnapshot:
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            turn_count=data["turn_count"],
            messages=data["messages"],
            total_usage=TokenUsage(**data["total_usage"]),
        )


class PersistenceManager:
    """Async persistence manager for sessions and checkpoints.

    Uses aiofiles for non-blocking I/O and orjson for fast JSON serialization.
    """

    def __init__(self):
        self.data_dir = get_data_dir()
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir = self.data_dir / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.sessions_dir, 0o700)
        os.chmod(self.checkpoints_dir, 0o700)
        self._lock = asyncio.Lock()

    async def save_session(self, snapshot: SessionSnapshot) -> None:
        """Save session snapshot using async I/O."""
        async with self._lock:
            file_path = self.sessions_dir / f"{snapshot.session_id}.json"

            # Use orjson for fast serialization
            content = orjson.dumps(snapshot.to_dict(), option=orjson.OPT_INDENT_2)

            async with aiofiles.open(file_path, "wb") as fp:
                await fp.write(content)

            os.chmod(file_path, 0o600)

    async def load_session(self, session_id: str) -> SessionSnapshot | None:
        """Load session snapshot using async I/O."""
        file_path = self.sessions_dir / f"{session_id}.json"

        if not file_path.exists():
            return None

        async with aiofiles.open(file_path, "rb") as fp:
            content = await fp.read()
            data = orjson.loads(content)

        return SessionSnapshot.from_dict(data)

    async def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions using async I/O."""
        sessions = []

        # Read all session files concurrently
        tasks = []
        for file_path in self.sessions_dir.glob("*.json"):
            tasks.append(self._read_session_metadata(file_path))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Failed to read session metadata: {result}")
            elif result is not None:
                sessions.append(result)

        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions

    async def _read_session_metadata(self, file_path: Path) -> dict[str, Any] | None:
        """Read session metadata using async I/O."""
        try:
            async with aiofiles.open(file_path, "rb") as fp:
                content = await fp.read()
                data = orjson.loads(content)

            return {
                "session_id": data["session_id"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "turn_count": data["turn_count"],
            }
        except Exception as e:
            logger.warning(f"Failed to read session metadata from {file_path}: {e}")
            return None

    async def save_checkpoint(self, snapshot: SessionSnapshot) -> str:
        """Save checkpoint using async I/O."""
        async with self._lock:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            checkpoint_id = f"{snapshot.session_id}_{timestamp}"
            file_path = self.checkpoints_dir / f"{checkpoint_id}.json"

            # Use orjson for fast serialization
            content = orjson.dumps(snapshot.to_dict(), option=orjson.OPT_INDENT_2)

            async with aiofiles.open(file_path, "wb") as fp:
                await fp.write(content)

            os.chmod(file_path, 0o600)
            return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> SessionSnapshot | None:
        """Load checkpoint using async I/O."""
        file_path = self.checkpoints_dir / f"{checkpoint_id}.json"

        if not file_path.exists():
            return None

        async with aiofiles.open(file_path, "rb") as fp:
            content = await fp.read()
            data = orjson.loads(content)

        return SessionSnapshot.from_dict(data)
