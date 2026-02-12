"""Tool registration validation utilities.

Provides validation functions for tool registration to catch
configuration errors early and provide clear error messages.
"""

import logging
from typing import Any

from friday_ai.tools.base import Tool

logger = logging.getLogger(__name__)


class ToolValidationError(Exception):
    """Raised when tool validation fails."""

    def __init__(self, tool_name: str, reason: str, details: dict[str, Any] | None = None):
        self.tool_name = tool_name
        self.reason = reason
        self.details = details or {}
        super().__init__(f"Tool '{tool_name}' validation failed: {reason}")


def validate_tool_metadata(tool: Tool) -> None:
    """Validate tool metadata structure.

    Args:
        tool: Tool instance to validate

    Raises:
        ToolValidationError: If metadata is invalid
    """
    # Check if tool has a name
    if not hasattr(tool, "name") or not tool.name:
        raise ToolValidationError(
            getattr(tool, "name", "unknown"),
            "Tool missing 'name' attribute",
            {"tool": str(tool)}
        )

    # Check if tool has a description
    if not hasattr(tool, "description") or not tool.description or not tool.description.strip():
        raise ToolValidationError(
            tool.name,
            "Missing or empty description",
            {"field": "description", "value": getattr(tool, "description", None)}
        )

    # Check if tool has a schema
    if not hasattr(tool, "schema") or tool.schema is None:
        raise ToolValidationError(
            tool.name,
            "Tool missing 'schema' attribute",
            {"field": "schema"}
        )


def validate_tool_schema(tool: Tool) -> None:
    """Validate tool's OpenAI schema generation.

    Args:
        tool: Tool instance to validate

    Raises:
        ToolValidationError: If schema generation would fail
    """
    try:
        schema = tool.to_openai_schema()
    except Exception as e:
        raise ToolValidationError(
            tool.name,
            f"Schema generation failed: {str(e)}",
            {"exception": str(e)}
        )

    # Validate schema structure
    required_fields = ["type", "name"]
    for field in required_fields:
        if field not in schema:
            raise ToolValidationError(
                tool.name,
                f"Schema missing required field: {field}",
                {"schema": schema, "missing_field": field}
            )
