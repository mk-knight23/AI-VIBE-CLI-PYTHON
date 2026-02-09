"""Tamper-evident audit logging for Friday AI.

Provides comprehensive audit trail with structured JSON format,
checksum verification, and log rotation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    TOOL_EXECUTION = "tool_execution"
    FILE_OPERATION = "file_operation"
    AUTH_EVENT = "auth_event"
    CONFIG_CHANGE = "config_change"
    SESSION_EVENT = "session_event"
    SECURITY_EVENT = "security_event"
    API_CALL = "api_call"
    ERROR = "error"


@dataclass
class AuditRecord:
    """A single audit record.

    Attributes:
        timestamp: ISO8601 timestamp
        event_type: Type of event
        user: User identifier (or system)
        action: Action performed
        resource: Resource affected
        result: success or failure
        details: Additional context
        trace_id: Trace ID for correlation
        checksum: SHA256 checksum for tamper detection
    """

    timestamp: str
    event_type: str
    user: str
    action: str
    resource: str
    result: str
    details: dict[str, Any]
    trace_id: str
    checksum: str

    @classmethod
    def create(
        cls,
        event_type: AuditEventType | str,
        action: str,
        resource: str,
        result: str = "success",
        user: str = "system",
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> AuditRecord:
        """Create a new audit record."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        event_type_str = event_type.value if isinstance(event_type, AuditEventType) else event_type

        # Create record without checksum first
        record_data = {
            "timestamp": timestamp,
            "event_type": event_type_str,
            "user": user,
            "action": action,
            "resource": resource,
            "result": result,
            "details": details or {},
            "trace_id": trace_id or "",
            "checksum": "",  # Placeholder
        }

        # Calculate checksum
        checksum = AuditLogger._calculate_checksum(record_data)
        record_data["checksum"] = checksum

        return cls(**record_data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def verify(self) -> bool:
        """Verify record integrity."""
        data = self.to_dict()
        stored_checksum = data["checksum"]
        data["checksum"] = ""  # Exclude checksum from verification
        calculated = AuditLogger._calculate_checksum(data)
        return stored_checksum == calculated


class AuditLogger:
    """Tamper-evident audit logging system.

    Features:
    - Structured JSON format
    - SHA256 checksums for tamper detection
    - Automatic log rotation
    - Async logging support
    - Log retention policies

    Example:
        audit = AuditLogger()
        await audit.log_tool_execution(
            tool="shell",
            args={"command": "[REDACTED]"},
            result="success",
            user="admin"
        )
    """

    def __init__(
        self,
        log_dir: str | Path = "~/.config/friday/audit",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        max_files: int = 10,
        retention_days: int = 90,
    ):
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.retention_days = retention_days
        self._current_file: Path | None = None
        self._buffer: list[AuditRecord] = []
        self._buffer_size = 10

    @staticmethod
    def _calculate_checksum(data: dict[str, Any]) -> str:
        """Calculate SHA256 checksum for record."""
        # Create canonical JSON representation
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:32]

    def _get_current_log_file(self) -> Path:
        """Get current log file, rotating if necessary."""
        if self._current_file and self._current_file.exists():
            size = self._current_file.stat().st_size
            if size < self.max_file_size:
                return self._current_file

        # Rotate logs
        self._rotate_logs()

        # Create new log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._current_file = self.log_dir / f"audit_{timestamp}.log"
        return self._current_file

    def _rotate_logs(self) -> None:
        """Rotate log files, keeping only max_files."""
        log_files = sorted(self.log_dir.glob("audit_*.log"), key=lambda p: p.stat().st_mtime)

        # Remove old files
        while len(log_files) >= self.max_files:
            oldest = log_files.pop(0)
            try:
                oldest.unlink()
                logger.debug(f"Rotated audit log: {oldest}")
            except OSError as e:
                logger.warning(f"Failed to remove old audit log: {e}")

    def _cleanup_old_logs(self) -> None:
        """Remove logs older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for log_file in self.log_dir.glob("audit_*.log"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    log_file.unlink()
                    logger.debug(f"Removed old audit log: {log_file}")
            except OSError as e:
                logger.warning(f"Failed to remove old audit log: {e}")

    async def log(
        self,
        event_type: AuditEventType | str,
        action: str,
        resource: str,
        result: str = "success",
        user: str = "system",
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> AuditRecord:
        """Log an audit event.

        Args:
            event_type: Type of event
            action: Action performed
            resource: Resource affected
            result: success or failure
            user: User identifier
            details: Additional context
            trace_id: Trace ID for correlation

        Returns:
            The created audit record
        """
        record = AuditRecord.create(
            event_type=event_type,
            action=action,
            resource=resource,
            result=result,
            user=user,
            details=details,
            trace_id=trace_id,
        )

        self._buffer.append(record)

        # Flush buffer if full
        if len(self._buffer) >= self._buffer_size:
            await self.flush()

        return record

    async def flush(self) -> None:
        """Flush buffered records to disk."""
        if not self._buffer:
            return

        log_file = self._get_current_log_file()

        try:
            with open(log_file, "a") as f:
                for record in self._buffer:
                    f.write(json.dumps(record.to_dict()) + "\n")

            self._buffer.clear()
            logger.debug(f"Flushed {len(self._buffer)} audit records to {log_file}")

        except OSError as e:
            logger.error(f"Failed to write audit log: {e}")
            # Don't clear buffer on failure - will retry

    async def log_tool_execution(
        self,
        tool: str,
        args: dict[str, Any],
        result: str,
        user: str = "system",
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Log a tool execution event."""
        # Redact sensitive args
        safe_args = self._redact_sensitive_data(args)

        details = {
            "tool": tool,
            "args": safe_args,
        }
        if metadata:
            details["metadata"] = metadata

        return await self.log(
            event_type=AuditEventType.TOOL_EXECUTION,
            action=f"execute_{tool}",
            resource=tool,
            result=result,
            user=user,
            details=details,
            trace_id=trace_id,
        )

    async def log_file_operation(
        self,
        operation: str,
        path: str,
        result: str = "success",
        user: str = "system",
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Log a file operation event."""
        details = {"path": path}
        if metadata:
            details.update(metadata)

        return await self.log(
            event_type=AuditEventType.FILE_OPERATION,
            action=operation,
            resource=path,
            result=result,
            user=user,
            details=details,
            trace_id=trace_id,
        )

    async def log_auth_event(
        self,
        event: str,
        user: str,
        success: bool,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Log an authentication/authorization event."""
        details = {"event": event}
        if metadata:
            details.update(metadata)

        return await self.log(
            event_type=AuditEventType.AUTH_EVENT,
            action=event,
            resource=user,
            result="success" if success else "failure",
            user=user,
            details=details,
            trace_id=trace_id,
        )

    async def log_security_event(
        self,
        event: str,
        severity: str,
        details: dict[str, Any],
        user: str = "system",
        trace_id: str | None = None,
    ) -> AuditRecord:
        """Log a security-related event."""
        event_details = {
            "severity": severity,
            **details,
        }

        # Log to standard logger as well for immediate visibility
        log_method = getattr(logger, severity.lower() if severity.lower() in ["debug", "info", "warning", "error", "critical"] else "warning")
        log_method(f"Security event: {event} - {details}")

        return await self.log(
            event_type=AuditEventType.SECURITY_EVENT,
            action=event,
            resource="security",
            result="detected",
            user=user,
            details=event_details,
            trace_id=trace_id,
        )

    async def log_config_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        user: str = "system",
        trace_id: str | None = None,
    ) -> AuditRecord:
        """Log a configuration change."""
        return await self.log(
            event_type=AuditEventType.CONFIG_CHANGE,
            action="config_change",
            resource=config_key,
            result="success",
            user=user,
            details={
                "config_key": config_key,
                "old_value": str(old_value)[:100] if old_value else None,
                "new_value": str(new_value)[:100] if new_value else None,
            },
            trace_id=trace_id,
        )

    async def log_error(
        self,
        error: Exception,
        context: dict[str, Any] | None = None,
        user: str = "system",
        trace_id: str | None = None,
    ) -> AuditRecord:
        """Log an error event."""
        details = {
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],
        }
        if context:
            details["context"] = context

        return await self.log(
            event_type=AuditEventType.ERROR,
            action="error",
            resource="system",
            result="failure",
            user=user,
            details=details,
            trace_id=trace_id,
        )

    def _redact_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive data from log entries."""
        sensitive_keys = {
            "password", "secret", "token", "key", "auth",
            "credential", "private_key", "api_key", "passwd",
        }

        redacted = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive_data(value)
            elif isinstance(value, str) and len(value) > 64:
                # Truncate long strings
                redacted[key] = value[:64] + "..."
            else:
                redacted[key] = value

        return redacted

    def get_recent_events(
        self,
        event_type: AuditEventType | str | None = None,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[AuditRecord]:
        """Get recent audit events.

        Args:
            event_type: Filter by event type
            limit: Maximum number of events
            since: Only return events since this time

        Returns:
            List of audit records
        """
        records = []
        event_type_str = event_type.value if isinstance(event_type, AuditEventType) else event_type

        # Read from all log files, newest first
        log_files = sorted(self.log_dir.glob("audit_*.log"), reverse=True)

        for log_file in log_files:
            try:
                with open(log_file) as f:
                    for line in reversed(f.readlines()):
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                            record = AuditRecord(**data)

                            # Verify integrity
                            if not record.verify():
                                logger.warning(f"Tampered audit record detected: {record}")
                                continue

                            # Filter by type
                            if event_type_str and record.event_type != event_type_str:
                                continue

                            # Filter by time
                            if since:
                                record_time = datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))
                                if record_time < since:
                                    continue

                            records.append(record)

                            if len(records) >= limit:
                                return records

                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse audit record: {e}")
                            continue

            except OSError as e:
                logger.warning(f"Failed to read audit log: {e}")
                continue

        return records

    def verify_log_integrity(self, log_file: Path | None = None) -> tuple[bool, list[str]]:
        """Verify integrity of audit logs.

        Args:
            log_file: Specific file to verify, or all files if None

        Returns:
            Tuple of (all_valid, list of tampered files)
        """
        tampered = []
        files_to_check = [log_file] if log_file else list(self.log_dir.glob("audit_*.log"))

        for file_path in files_to_check:
            if file_path is None:
                continue

            try:
                with open(file_path) as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                            record = AuditRecord(**data)

                            if not record.verify():
                                tampered.append(f"{file_path}:{line_num}")

                        except (json.JSONDecodeError, TypeError):
                            tampered.append(f"{file_path}:{line_num} (parse error)")

            except OSError as e:
                tampered.append(f"{file_path} (read error: {e})")

        return len(tampered) == 0, tampered
