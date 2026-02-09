"""Session management for Friday AI.

Provides session persistence, continuity, and history tracking
similar to Ralph's session management system.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SessionEventType(Enum):
    """Types of session events."""
    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class SessionEvent:
    """An event in a session's history."""

    event_type: SessionEventType
    timestamp: datetime
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """A Friday AI session."""

    session_id: str
    created_at: datetime
    last_activity: datetime
    events: list[SessionEvent] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self, timeout_hours: int = 24) -> bool:
        """Check if session has expired."""
        return (datetime.now() - self.last_activity) >= timedelta(hours=timeout_hours)

    @property
    def duration(self) -> timedelta:
        """Get session duration."""
        return self.last_activity - self.created_at

    def add_event(self, event_type: SessionEventType, reason: str | None = None, **metadata: Any) -> None:
        """Add an event to the session."""
        event = SessionEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            reason=reason,
            metadata=metadata,
        )
        self.events.append(event)
        self.last_activity = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "events": [
                {
                    "type": e.event_type.value,
                    "timestamp": e.timestamp.isoformat(),
                    "reason": e.reason,
                    "metadata": e.metadata,
                }
                for e in self.events
            ],
            "context": self.context,
            "metadata": self.metadata,
        }


class SessionManager:
    """Manages Friday AI sessions."""

    def __init__(
        self,
        storage_dir: str = ".friday/sessions",
        current_session_file: str = ".friday/.current_session",
        history_file: str = ".friday/.session_history",
    ):
        """Initialize the session manager.

        Args:
            storage_dir: Directory to store session files.
            current_session_file: File storing the current session ID.
            history_file: File storing session history.
        """
        self.storage_dir = Path(storage_dir)
        self.current_session_file = Path(current_session_file)
        self.history_file = Path(history_file)

        # Ensure directories exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_file.parent.mkdir(parents=True, exist_ok=True)

        self._current_session: Session | None = None

    def create_session(self, session_id: str | None = None, **metadata: Any) -> Session:
        """Create a new session.

        Args:
            session_id: Optional session ID. If None, generates one.
            **metadata: Additional session metadata.

        Returns:
            The created session.
        """
        if session_id is None:
            session_id = self._generate_session_id()

        session = Session(
            session_id=session_id,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            metadata=metadata,
        )

        session.add_event(SessionEventType.STARTED, **metadata)

        # Save as current session
        self._current_session = session
        self._save_current_session(session_id)

        # Save session to file
        self._save_session(session)

        # Log to history
        self._log_to_history(session, "created")

        logger.info(f"Created session: {session_id}")
        return session

    def get_current_session(self) -> Session | None:
        """Get the current session.

        Returns:
            The current session or None if no active session.
        """
        if self._current_session:
            # Check if expired
            if not self._current_session.is_expired():
                return self._current_session
            else:
                # Session expired
                logger.info(f"Session {self._current_session.session_id} expired")
                self._current_session = None
                self._clear_current_session()
                return None

        # Try to load from file
        session_id = self._load_current_session()
        if session_id:
            session = self._load_session(session_id)
            if session and not session.is_expired():
                self._current_session = session
                session.add_event(SessionEventType.RESUMUED, reason="Loaded from storage")
                return session
            else:
                # Session expired or invalid
                self._clear_current_session()

        return None

    def resume_session(self, session_id: str) -> Session | None:
        """Resume a specific session.

        Args:
            session_id: The session ID to resume.

        Returns:
            The resumed session or None if not found.
        """
        session = self._load_session(session_id)
        if session:
            if session.is_expired():
                logger.warning(f"Session {session_id} has expired")
                return None

            session.add_event(SessionEventType.RESUMUED, reason="Manual resume")
            self._current_session = session
            self._save_current_session(session_id)
            self._log_to_history(session, "resumed")

            logger.info(f"Resumed session: {session_id}")
            return session

        logger.warning(f"Session {session_id} not found")
        return None

    def pause_session(self) -> None:
        """Pause the current session."""
        if self._current_session:
            self._current_session.add_event(SessionEventType.PAUSED, reason="Manual pause")
            self._save_session(self._current_session)
            self._log_to_history(self._current_session, "paused")
            logger.info(f"Paused session: {self._current_session.session_id}")

    def stop_session(self, reason: str = "User stopped") -> None:
        """Stop the current session.

        Args:
            reason: Reason for stopping the session.
        """
        if self._current_session:
            self._current_session.add_event(SessionEventType.STOPPED, reason=reason)
            self._save_session(self._current_session)
            self._log_to_history(self._current_session, "stopped", reason=reason)
            logger.info(f"Stopped session: {self._current_session.session_id} - {reason}")

            self._current_session = None
            self._clear_current_session()

    def list_sessions(self) -> list[Session]:
        """List all available sessions.

        Returns:
            List of sessions, most recent first.
        """
        sessions = []

        for session_file in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(session_file.read_text())
                session = self._dict_to_session(data)
                sessions.append(session)
            except Exception as e:
                logger.warning(f"Failed to load session {session_file}: {e}")

        # Sort by created_at, most recent first
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions

    def get_session(self, session_id: str) -> Session | None:
        """Get a specific session by ID.

        Args:
            session_id: The session ID.

        Returns:
            The session or None if not found.
        """
        return self._load_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        session_file = self.storage_dir / f"{session_id}.json"

        if session_file.exists():
            session_file.unlink()
            logger.info(f"Deleted session: {session_id}")

            # Clear current session if it was the one deleted
            if self._current_session and self._current_session.session_id == session_id:
                self._current_session = None
                self._clear_current_session()

            return True

        return False

    def _generate_session_id(self) -> str:
        """Generate a unique session ID.

        Returns:
            A unique session ID.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import random
        suffix = random.randint(1000, 9999)
        return f"session_{timestamp}_{suffix}"

    def _save_session(self, session: Session) -> None:
        """Save a session to file.

        Args:
            session: The session to save.
        """
        session_file = self.storage_dir / f"{session.session_id}.json"
        session_file.write_text(json.dumps(session.to_dict(), indent=2))

    def _load_session(self, session_id: str) -> Session | None:
        """Load a session from file.

        Args:
            session_id: The session ID to load.

        Returns:
            The loaded session or None if not found.
        """
        session_file = self.storage_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            data = json.loads(session_file.read_text())
            return self._dict_to_session(data)
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def _dict_to_session(self, data: dict[str, Any]) -> Session:
        """Convert a dictionary to a Session object.

        Args:
            data: The session data.

        Returns:
            A Session object.
        """
        events = []
        for event_data in data.get("events", []):
            events.append(
                SessionEvent(
                    event_type=SessionEventType(event_data["type"]),
                    timestamp=datetime.fromisoformat(event_data["timestamp"]),
                    reason=event_data.get("reason"),
                    metadata=event_data.get("metadata", {}),
                )
            )

        return Session(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            events=events,
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
        )

    def _save_current_session(self, session_id: str) -> None:
        """Save the current session ID.

        Args:
            session_id: The current session ID.
        """
        self.current_session_file.write_text(session_id)

    def _load_current_session(self) -> str | None:
        """Load the current session ID.

        Returns:
            The current session ID or None.
        """
        if self.current_session_file.exists():
            return self.current_session_file.read_text().strip()
        return None

    def _clear_current_session(self) -> None:
        """Clear the current session."""
        if self.current_session_file.exists():
            self.current_session_file.unlink()

    def _log_to_history(self, session: Session, action: str, **details: Any) -> None:
        """Log a session action to history.

        Args:
            session: The session.
            action: The action performed.
            **details: Additional details.
        """
        entry = {
            "session_id": session.session_id,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        }

        # Append to history file (keep last 100 entries)
        history = []
        if self.history_file.exists():
            try:
                history = json.loads(self.history_file.read_text())
            except Exception:
                pass

        history.append(entry)

        # Keep only last 100 entries
        if len(history) > 100:
            history = history[-100:]

        self.history_file.write_text(json.dumps(history, indent=2))
