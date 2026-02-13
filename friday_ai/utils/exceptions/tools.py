from typing import Any
from .base import FridayError


class ToolExecutionError(FridayError):
    """Tool execution failures."""

    def __init__(
        self,
        message: str,
        tool: str | None = None,
        exit_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if tool:
            details["tool"] = tool
        if exit_code is not None:
            details["exit_code"] = exit_code
        retryable = kwargs.pop("retryable", False)
        super().__init__(
            message=message,
            code="TOOL_EXECUTION_FAILED",
            details=details,
            retryable=retryable,
            **kwargs,
        )
        self.tool = tool
        self.exit_code = exit_code


class ToolNotFoundError(FridayError):
    """Requested tool not found."""

    def __init__(self, tool: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Tool not found: {tool}",
            code="TOOL_NOT_FOUND",
            details={"tool": tool},
            retryable=False,
            **kwargs,
        )
        self.tool = tool


class ToolTimeoutError(FridayError):
    """Tool execution timed out."""

    def __init__(
        self,
        message: str,
        tool: str | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if tool:
            details["tool"] = tool
        if timeout is not None:
            details["timeout_seconds"] = timeout
        super().__init__(
            message=message,
            code="TOOL_TIMEOUT",
            details=details,
            retryable=True,
            **kwargs,
        )
        self.tool = tool
        self.timeout = timeout
