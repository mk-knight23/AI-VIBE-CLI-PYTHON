"""Tests for tool registration validation."""

import pytest

from pydantic import BaseModel, Field

from friday_ai.config.config import Config
from friday_ai.tools.base import Tool, ToolKind, ToolInvocation, ToolResult
from friday_ai.tools.registry import ToolRegistry
from friday_ai.tools.validation import ToolValidationError, validate_tool_metadata, validate_tool_schema


class MockToolParams(BaseModel):
    """Mock tool parameters."""
    test_param: str = Field(description="A test parameter")


class MockTool(Tool):
    """Mock tool for testing."""

    name = "mock_tool"
    description = "A mock tool for testing"
    kind = ToolKind.READ
    schema = MockToolParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        return ToolResult.success_result("success")


class MockToolInvalidDescription(Tool):
    """Mock tool with invalid description."""

    name = "mock_tool_invalid"
    description = ""
    kind = ToolKind.READ
    schema = MockToolParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        return ToolResult.success_result("success")


class MockToolNoSchema(Tool):
    """Mock tool without schema."""

    name = "mock_tool_no_schema"
    description = "A tool without schema"
    kind = ToolKind.READ

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        return ToolResult.success_result("success")


def test_validate_tool_metadata_valid_tool():
    """Test that a valid tool passes validation."""
    tool = MockTool(config=Config())

    # Should not raise any exception
    validate_tool_metadata(tool)


def test_validate_tool_metadata_empty_description():
    """Test that tool with empty description fails validation."""
    tool = MockToolInvalidDescription(config=Config())

    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_metadata(tool)

    assert "description" in str(exc_info.value)


def test_validate_tool_metadata_no_schema():
    """Test that tool without schema fails validation."""
    tool = MockToolNoSchema(config=Config())

    with pytest.raises(ToolValidationError) as exc_info:
        validate_tool_metadata(tool)

    assert "schema" in str(exc_info.value)


def test_validate_tool_schema_valid_tool():
    """Test that a valid tool passes schema validation."""
    tool = MockTool(config=Config())

    # Should not raise any exception
    validate_tool_schema(tool)


def test_tool_registry_rejects_invalid_tool():
    """Test that tool registry rejects tools that fail validation."""
    config = Config()
    registry = ToolRegistry(config)

    # Try to register invalid tool
    invalid_tool = MockToolInvalidDescription(config=config)

    with pytest.raises(Exception):
        registry.register(invalid_tool)


def test_tool_registry_accepts_valid_tool():
    """Test that tool registry accepts valid tools."""
    config = Config()
    registry = ToolRegistry(config)

    # Register valid tool
    valid_tool = MockTool(config=config)
    registry.register(valid_tool)

    # Verify tool is registered
    assert registry.get("mock_tool") is not None
    assert registry.get("mock_tool").name == "mock_tool"
