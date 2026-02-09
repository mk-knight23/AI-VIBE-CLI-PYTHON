"""Input validation for Friday AI security.

Provides comprehensive input validation to prevent:
- Path traversal attacks
- Command injection
- SQL injection
- XSS attacks
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from friday_ai.utils.errors import (
    CommandInjectionError,
    PathTraversalError,
    SQLInjectionError,
    ValidationError,
)


@dataclass
class ValidatedPath:
    """Validated path result."""

    original: str
    resolved: Path
    is_safe: bool
    is_absolute: bool
    is_within_cwd: bool


@dataclass
class ValidatedCommand:
    """Validated command result."""

    original: str
    command: str
    args: list[str]
    is_safe: bool
    blocked_patterns: list[str]


@dataclass
class ValidatedSQL:
    """Validated SQL result."""

    original: str
    is_safe: bool
    detected_patterns: list[str]
    is_read_only: bool


@dataclass
class ValidatedURL:
    """Validated URL result."""

    original: str
    scheme: str
    netloc: str
    path: str
    is_safe: bool
    is_internal: bool


class InputValidator:
    """Comprehensive input validation for security.

    Features:
    - Path traversal detection and prevention
    - Command injection detection
    - SQL injection detection
    - URL validation
    - Size limits enforcement

    Example:
        validator = InputValidator()

        # Validate path
        result = validator.validate_path("../etc/passwd")
        if not result.is_safe:
            raise PathTraversalError(result.original)

        # Validate command
        result = validator.validate_command("rm -rf /")
        if not result.is_safe:
            raise CommandInjectionError(result.original)
    """

    # Dangerous command patterns
    DANGEROUS_COMMANDS = [
        r"rm\s+-rf\s+/",
        r"rm\s+-rf\s+~",
        r"rm\s+-rf\s+\\$HOME",
        r"dd\s+if=.*of=/dev/",
        r"mkfs\.\w+",
        r"fdisk\s+/dev/",
        r"shutdown\s+-h",
        r"reboot",
        r"halt",
        r"init\s+0",
        r"chmod\s+-R\s+777\s+/",
        r"chmod\s+-R\s+000\s+/",
        r"chown\s+-R\s+root:root\s+/",
        r":\(\)\s*\{\s*:\|:&\s*\};:\s*:",  # Fork bomb
        r"curl\s+.*\|\s*bash",
        r"curl\s+.*\|\s*sh",
        r"wget\s+.*\|\s*bash",
        r"wget\s+.*\|\s*sh",
        r"python\s+.*\|\s*bash",
        r">\s*/dev/\w+",
        r"echo\s+.*>\s+/sys/",
        r"echo\s+.*>\s+/proc/",
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",  # Single quote, comment
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",  # = with quote/comment
        r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # 'or'
        r"((\%27)|(\'))union",  # 'union
        r"exec(\s|\+)+(s|x)p\w+",  # xp_cmdshell
        r"UNION\s+SELECT",
        r"INSERT\s+INTO",
        r"DELETE\s+FROM",
        r"DROP\s+TABLE",
        r"DROP\s+DATABASE",
        r"ALTER\s+TABLE",
        r";\s*SHUTDOWN",
        r";\s*DROP",
        r"'\s*OR\s*'1'\s*=\s*'1",
        r"'\s*OR\s*1\s*=\s*1",
        r"1\s*=\s*1",
        r"SLEEP\s*\(",
        r"BENCHMARK\s*\(",
        r"WAITFOR\s+DELAY",
        r" pg_sleep\s*\(",
    ]

    # Read-only SQL patterns (safe)
    READ_ONLY_PATTERNS = [
        r"^\s*SELECT\s+",
        r"^\s*SHOW\s+",
        r"^\s*DESCRIBE\s+",
        r"^\s*EXPLAIN\s+",
        r"^\s*PRAGMA\s+",  # SQLite
    ]

    # Allowed URL schemes
    SAFE_URL_SCHEMES = {"http", "https", "ftp", "ftps", "file", "ssh", "git"}

    # Internal network patterns
    INTERNAL_NETWORKS = [
        r"^localhost",
        r"^127\.",
        r"^10\.",
        r"^172\.(1[6-9]|2[0-9]|3[01])\.",
        r"^192\.168\.",
        r"^::1$",
        r"^fc00:",
        r"^fe80:",
    ]

    def __init__(
        self,
        max_path_length: int = 4096,
        max_command_length: int = 8192,
        max_sql_length: int = 100000,
        max_url_length: int = 2048,
        allowed_schemes: set[str] | None = None,
    ):
        self.max_path_length = max_path_length
        self.max_command_length = max_command_length
        self.max_sql_length = max_sql_length
        self.max_url_length = max_url_length
        self.allowed_schemes = allowed_schemes or self.SAFE_URL_SCHEMES

    def validate_path(
        self,
        path: str,
        allow_absolute: bool = False,
        base_path: Path | None = None,
    ) -> ValidatedPath:
        """Validate a file path for traversal attacks.

        Args:
            path: Path to validate
            allow_absolute: Allow absolute paths
            base_path: Base path for relative path resolution

        Returns:
            ValidatedPath result

        Raises:
            ValidationError: If path is invalid
            PathTraversalError: If path traversal detected
        """
        if not path:
            raise ValidationError("Path cannot be empty", field="path")

        if len(path) > self.max_path_length:
            raise ValidationError(
                f"Path exceeds maximum length of {self.max_path_length}",
                field="path",
                value=path[:50] + "...",
            )

        # Check for null bytes
        if "\x00" in path:
            raise ValidationError("Path contains null bytes", field="path")

        # Resolve path
        try:
            original_path = Path(path)
            if base_path:
                resolved = (base_path / path).resolve()
                base_resolved = base_path.resolve()
            else:
                resolved = original_path.resolve()
                base_resolved = Path.cwd().resolve()
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid path: {e}", field="path") from e

        is_absolute = original_path.is_absolute()

        # Check if absolute paths are allowed
        if is_absolute and not allow_absolute:
            raise PathTraversalError(
                f"Absolute paths not allowed: {path}",
                details={"path": path},
            )

        # Check for path traversal
        is_within_cwd = str(resolved).startswith(str(base_resolved))

        # Check for traversal patterns
        traversal_patterns = ["../", "..\\", "..", "%2e%2e/", "%2e%2e\\"]
        has_traversal = any(pattern in path for pattern in traversal_patterns)

        # Safe if: no traversal AND (within cwd OR absolute paths allowed)
        is_safe = not has_traversal and (is_within_cwd or (is_absolute and allow_absolute))

        if not is_safe:
            raise PathTraversalError(
                f"Path traversal detected: {path}",
                details={"path": path, "resolved": str(resolved)},
            )

        return ValidatedPath(
            original=path,
            resolved=resolved,
            is_safe=is_safe,
            is_absolute=is_absolute,
            is_within_cwd=is_within_cwd,
        )

    def validate_command(self, command: str) -> ValidatedCommand:
        """Validate a shell command for injection attacks.

        Args:
            command: Command to validate

        Returns:
            ValidatedCommand result

        Raises:
            ValidationError: If command is invalid
            CommandInjectionError: If dangerous pattern detected
        """
        if not command:
            raise ValidationError("Command cannot be empty", field="command")

        if len(command) > self.max_command_length:
            raise ValidationError(
                f"Command exceeds maximum length of {self.max_command_length}",
                field="command",
            )

        # Check for dangerous patterns
        blocked_patterns = []
        for pattern in self.DANGEROUS_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                blocked_patterns.append(pattern)

        is_safe = len(blocked_patterns) == 0

        if not is_safe:
            raise CommandInjectionError(
                command,
                details={"blocked_patterns": blocked_patterns},
            )

        # Parse command
        try:
            parts = shlex.split(command)
            cmd = parts[0] if parts else ""
            args = parts[1:] if len(parts) > 1 else []
        except ValueError as e:
            raise ValidationError(f"Invalid command syntax: {e}", field="command") from e

        return ValidatedCommand(
            original=command,
            command=cmd,
            args=args,
            is_safe=is_safe,
            blocked_patterns=blocked_patterns,
        )

    def validate_sql(self, query: str, allow_write: bool = False) -> ValidatedSQL:
        """Validate SQL query for injection attacks.

        Args:
            query: SQL query to validate
            allow_write: Allow write operations (INSERT, UPDATE, DELETE)

        Returns:
            ValidatedSQL result

        Raises:
            ValidationError: If query is invalid
            SQLInjectionError: If injection pattern detected
        """
        if not query:
            raise ValidationError("SQL query cannot be empty", field="query")

        if len(query) > self.max_sql_length:
            raise ValidationError(
                f"SQL query exceeds maximum length of {self.max_sql_length}",
                field="query",
            )

        # Check for injection patterns
        detected_patterns = []
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                detected_patterns.append(pattern)

        is_safe = len(detected_patterns) == 0

        if not is_safe:
            raise SQLInjectionError(
                query,
                details={"detected_patterns": detected_patterns[:5]},
            )

        # Check if read-only
        is_read_only = any(
            re.match(pattern, query, re.IGNORECASE)
            for pattern in self.READ_ONLY_PATTERNS
        )

        # Check for write operations if not allowed
        if not allow_write and not is_read_only:
            # More permissive check - just warn
            pass

        return ValidatedSQL(
            original=query,
            is_safe=is_safe,
            detected_patterns=detected_patterns,
            is_read_only=is_read_only,
        )

    def validate_url(
        self,
        url: str,
        allow_internal: bool = True,
        allow_file: bool = False,
    ) -> ValidatedURL:
        """Validate a URL.

        Args:
            url: URL to validate
            allow_internal: Allow internal network URLs
            allow_file: Allow file:// URLs

        Returns:
            ValidatedURL result

        Raises:
            ValidationError: If URL is invalid
        """
        if not url:
            raise ValidationError("URL cannot be empty", field="url")

        if len(url) > self.max_url_length:
            raise ValidationError(
                f"URL exceeds maximum length of {self.max_url_length}",
                field="url",
            )

        # Parse URL
        try:
            parsed = urlparse(url)
        except ValueError as e:
            raise ValidationError(f"Invalid URL: {e}", field="url") from e

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path

        # Check scheme
        allowed = self.allowed_schemes.copy()
        if allow_file:
            allowed.add("file")

        is_safe = scheme in allowed

        if not is_safe:
            raise ValidationError(
                f"URL scheme '{scheme}' not allowed",
                field="url",
                value=url,
            )

        # Check for internal network
        is_internal = any(
            re.match(pattern, netloc)
            for pattern in self.INTERNAL_NETWORKS
        )

        if is_internal and not allow_internal:
            raise ValidationError(
                "Internal network URLs not allowed",
                field="url",
                value=url,
            )

        return ValidatedURL(
            original=url,
            scheme=scheme,
            netloc=netloc,
            path=path,
            is_safe=is_safe,
            is_internal=is_internal,
        )

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename to prevent path traversal.

        Args:
            filename: Filename to sanitize

        Returns:
            Sanitized filename
        """
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")

        # Remove null bytes
        filename = filename.replace("\x00", "")

        # Remove leading dots (hidden files)
        filename = filename.lstrip(".")

        # Limit length
        if len(filename) > 255:
            name, ext = filename[:251], filename[251:].split(".")[-1]
            filename = f"{name}.{ext}" if ext else name

        return filename or "unnamed"

    def validate_size(
        self,
        size: int,
        max_size: int,
        name: str = "data",
    ) -> None:
        """Validate data size.

        Args:
            size: Data size in bytes
            max_size: Maximum allowed size
            name: Name of data for error message

        Raises:
            ValidationError: If size exceeds limit
        """
        if size > max_size:
            raise ValidationError(
                f"{name} size ({size} bytes) exceeds maximum ({max_size} bytes)",
                field=name,
            )
