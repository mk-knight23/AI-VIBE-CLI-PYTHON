"""Safety Manager - Centralizes safety and approval concerns."""

import logging
from typing import Any

from friday_ai.config.config import Config
from friday_ai.safety.approval import ApprovalManager

logger = logging.getLogger(__name__)


class SafetyManager:
    """Manages safety and approval operations.

    Centralizes approval logic, input validation, and security checks.
    This reduces Session class coupling by extracting safety concerns.

    Responsibilities:
    - Approval policy management
    - Dangerous command detection
    - Input validation and sanitization
    - Secret scrubbing
    - Path traversal prevention
    """

    def __init__(self, approval_policy: str, cwd: str):
        """Initialize safety manager.

        Args:
            approval_policy: Approval policy mode (yolo, auto, on-request, etc.)
            cwd: Current working directory for path validation
        """
        self.approval_policy = approval_policy
        self.cwd = cwd

        # Approval Manager
        self.approval_manager = ApprovalManager(
            approval_policy,
            cwd,
        )

        logger.info(f"Safety manager initialized with policy: {approval_policy}")

    def check_approval(self, tool_name: str, params: dict[str, Any]) -> bool:
        """Check if a tool execution requires approval.

        Args:
            tool_name: Name of the tool being executed
            params: Tool parameters

        Returns:
            True if approved, False if rejected
        """
        return self.approval_manager.is_approved(tool_name, params)

    def validate_path(self, path: str) -> bool:
        """Validate a file path for security.

        Prevents path traversal attacks and ensures path is within allowed bounds.

        Args:
            path: Path to validate

        Returns:
            True if path is safe, False otherwise
        """
        # Import here to avoid circular dependency
        from friday_ai.safety.validators import validate_path_safe

        return validate_path_safe(path, self.cwd)

    def validate_command(self, command: str) -> bool:
        """Validate a shell command for safety.

        Checks against dangerous command whitelist.

        Args:
            command: Command to validate

        Returns:
            True if command is safe, False if dangerous
        """
        # Import here to avoid circular dependency
        from friday_ai.safety.validators import validate_command_safe

        return validate_command_safe(command)

    def scrub_secrets(self, text: str) -> str:
        """Remove secrets from text before logging/display.

        Args:
            text: Text that may contain secrets

        Returns:
            Text with secrets scrubbed
        """
        # Import here to avoid circular dependency
        from friday_ai.security.secret_manager import scrub_secrets_from_text

        return scrub_secrets_from_text(text)

    def get_stats(self) -> dict[str, Any]:
        """Get safety manager statistics.

        Returns:
            Dictionary with safety metrics
        """
        return {
            "approval_policy": self.approval_policy,
            "approvals_required": self.approval_manager.get_approval_count(),
        }
