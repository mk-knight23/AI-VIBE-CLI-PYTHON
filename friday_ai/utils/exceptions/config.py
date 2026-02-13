from typing import Any
from .base import FridayError


class ConfigError(FridayError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_file: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            details=details,
            retryable=False,
            **kwargs,
        )
        self.config_key = config_key
        self.config_file = config_file


class ValidationError(FridayError):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details,
            retryable=False,
            **kwargs,
        )
        self.field = field
        self.value = value
