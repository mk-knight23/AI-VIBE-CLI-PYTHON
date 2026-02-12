"""Security audit log viewer tool.

Provides visibility into security-related events like
blocked operations, validation failures, and suspicious activity.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from friday_ai.tools.base import Tool, ToolInvocation, ToolKind, ToolResult

logger = logging.getLogger(__name__)


class SecurityAuditLogTool(Tool):
    """Tool for viewing security-related audit logs."""

    name = "security_audit"
    description = "View security audit logs for debugging and monitoring"
    kind = ToolKind.READ

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute security audit log retrieval."""
        limit = invocation.params.get("limit", 50)
        level = invocation.params.get("level", "all").lower()

        try:
            limit = int(limit)
        except (ValueError, TypeError):
            return ToolResult.error_result(
                f"Invalid limit value: {limit}",
                metadata={"limit": str(limit)}
            )

        # Collect security events
        events = self._collect_security_events(invocation.cwd, limit, level)

        # Format output
        output_lines = []
        output_lines.append(f"Security Audit Log (last {limit} events, level: {level})")
        output_lines.append("=" * 60)

        if not events:
            output_lines.append("No security events found")
        else:
            for event in events:
                timestamp = event.get("timestamp", "unknown")
                event_type = event.get("type", "unknown")
                message = event.get("message", "")
                details = event.get("details", {})

                output_lines.append(f"\n[{timestamp}] {event_type}")
                output_lines.append(f"  {message}")

                if details:
                    for key, value in details.items():
                        output_lines.append(f"    {key}: {value}")

        return ToolResult.success_result(
            "\n".join(output_lines),
            metadata={
                "events_count": len(events),
                "level": level,
                "limit": limit,
            },
        )

    def _collect_security_events(
        self, cwd: Path, limit: int, level: str
    ) -> list[dict[str, Any]]:
        """Collect security events from log files.

        Args:
            cwd: Current working directory
            limit: Maximum events to return
            level: Filter by security level

        Returns:
            List of security event dictionaries
        """
        events = []

        # Check for .friday directory
        friday_dir = cwd / ".friday"
        if not friday_dir.exists():
            return events

        # Look for security log file
        security_log = friday_dir / "security_audit.log"
        if not security_log.exists():
            return events

        try:
            with open(security_log, "r") as f:
                lines = f.readlines()[-limit:]  # Last N lines
        except Exception as e:
            logger.warning(f"Failed to read security log: {e}")
            return events

        # Parse log lines
        for line in lines:
            event = self._parse_log_line(line)
            if event:
                # Filter by level
                if level == "all" or event.get("level", "info") == level:
                    events.append(event)

        return events[:limit]

    def _parse_log_line(self, line: str) -> dict[str, Any] | None:
        """Parse a log line into structured event data.

        Args:
            line: Raw log line

        Returns:
            Event dictionary or None if not a security event
        """
        import json
        import re

        # Format: [TIMESTAMP] LEVEL: Message (details)
        pattern = r"^\[([\d\-\:T]+)\] (\w+): (.+?)(?:\s*\((.+)\))?$"

        match = re.match(pattern, line.strip())
        if not match:
            return None

        timestamp, level, message, details_str = match.groups()

        event = {
            "timestamp": timestamp,
            "level": level.lower(),
            "type": self._classify_event(level, message),
            "message": message.strip(),
        }

        # Parse details if present
        if details_str:
            try:
                event["details"] = json.loads(details_str)
            except json.JSONDecodeError:
                event["details"] = {"raw": details_str}

        return event

    def _classify_event(self, level: str, message: str) -> str:
        """Classify security event by type.

        Args:
            level: Log level
            message: Event message

        Returns:
            Event type string
        """
        message_lower = message.lower()

        if level == "error":
            if "injection" in message_lower or "sql" in message_lower:
                return "SQL_INJECTION_ATTEMPT"
            if "validation" in message_lower:
                return "VALIDATION_ERROR"
            if "blocked" in message_lower:
                return "BLOCKED_OPERATION"
            return "ERROR"

        if level == "warning":
            if "suspicious" in message_lower:
                return "SUSPICIOUS_ACTIVITY"
            if "unusual" in message_lower:
                return "UNUSUAL_ACTIVITY"
            return "WARNING"

        return "INFO"
