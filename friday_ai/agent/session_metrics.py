"""Session Metrics - Tracks session statistics and performance metrics."""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class SessionMetrics:
    """Tracks session-level metrics and statistics.

    Centralizes session stats collection and reporting.
    This reduces Session class coupling by extracting metrics concerns.

    Responsibilities:
    - Turn counting
    - Message and token tracking
    - Tool usage statistics
    - Session timing information
    - Performance metrics
    """

    def __init__(self, session_id: str):
        """Initialize session metrics.

        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # Counters
        self.turn_count = 0
        self.message_count = 0
        self.tool_call_count = 0

        # Token usage (will be updated by context manager)
        self.total_tokens_used = 0
        self.total_tokens_cached = 0

        # Tool usage tracking
        self.tools_used = set()

        logger.info(f"Session metrics initialized for session: {session_id}")

    def increment_turn(self) -> int:
        """Increment turn counter.

        Returns:
            New turn count
        """
        self.turn_count += 1
        self.updated_at = datetime.now()
        logger.debug(f"Turn incremented to {self.turn_count}")
        return self.turn_count

    def record_tool_usage(self, tool_name: str) -> None:
        """Record that a tool was used.

        Args:
            tool_name: Name of the tool used
        """
        self.tools_used.add(tool_name)
        self.tool_call_count += 1
        self.updated_at = datetime.now()
        logger.debug(f"Tool usage recorded: {tool_name}")

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive session statistics.

        Returns:
            Dictionary with all session metrics
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "turn_count": self.turn_count,
            "message_count": self.message_count,
            "tool_call_count": self.tool_call_count,
            "unique_tools_used": len(self.tools_used),
            "tools_used": list(self.tools_used),
            "total_tokens_used": self.total_tokens_used,
            "total_tokens_cached": self.total_tokens_cached,
            "session_duration_seconds": (
                datetime.now() - self.created_at
            ).total_seconds(),
        }

    def get_summary(self) -> str:
        """Get a human-readable summary of session metrics.

        Returns:
            Formatted summary string
        """
        duration = datetime.now() - self.created_at
        minutes = int(duration.total_seconds() / 60)

        return (
            f"Session: {self.session_id[:8]}... | "
            f"Turns: {self.turn_count} | "
            f"Tools: {len(self.tools_used)} | "
            f"Duration: {minutes}m"
        )
