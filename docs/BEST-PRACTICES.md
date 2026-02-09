# Friday AI - Best Practices
## Python Development Standards

---

## Table of Contents

1. [Code Style](#code-style)
2. [Architecture Patterns](#architecture-patterns)
3. [Error Handling](#error-handling)
4. [Testing](#testing)
5. [Documentation](#documentation)

---

## Code Style

### Python Style Guide

Follow PEP 8 with project-specific conventions:

```python
# Maximum line length: 100 characters
# Use spaces, not tabs (4 spaces per indent)

# Good
class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry."""
        self._tools[tool.name] = tool

# Bad
class tool_registry:
    def __init__(self):
        self.tools={}
    def register(self,tool):
        self.tools[tool.name]=tool
```

### Type Hints

Use type hints for all function signatures:

```python
from typing import Any, Optional

# Good
def process_data(data: dict[str, Any]) -> str:
    return str(data)

# For optional values
def find_tool(name: str) -> Optional[Tool]:
    return self._tools.get(name)

# For async functions
async def execute_tool(tool: Tool, args: dict) -> str:
    return await tool.execute(**args)
```

### String Formatting

Use f-strings for formatting:

```python
# Good
message = f"Tool {name} executed in {duration:.2f}s"

# For complex formatting, use multiline
result = (
    f"File: {path}\n"
    f"Lines: {start}-{end}\n"
    f"Total: {count}"
)
```

---

## Architecture Patterns

### Async/Await

All I/O operations must be async:

```python
# Good - async for I/O
async def fetch_url(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.content

# Bad - blocking I/O
def fetch_url(url: str) -> bytes:
    return requests.get(url).content
```

### Context Managers

Use context managers for resource management:

```python
# Good
async with Agent(config) as agent:
    result = await agent.run(prompt)

# Database connections, files, etc.
async with database.connection() as conn:
    await conn.execute(query)
```

### Event-Driven Design

Use events for loose coupling:

```python
# Events for UI updates
async for event in agent.run(prompt):
    if event.type == AgentEventType.TOOL_CALL_START:
        ui.show_tool_start(event.data)
    elif event.type == AgentEventType.TEXT_DELTA:
        ui.stream_text(event.data["content"])
```

### Registry Pattern

Use registries for tool management:

```python
class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)
```

---

## Error Handling

### Custom Exceptions

Define specific exceptions:

```python
# utils/errors.py
class FridayError(Exception):
    """Base exception for Friday AI."""
    pass

class ConfigError(FridayError):
    """Configuration error."""
    pass

class ToolError(FridayError):
    """Tool execution error."""
    def __init__(self, message: str, tool_name: str):
        super().__init__(message)
        self.tool_name = tool_name
```

### Try/Except Patterns

Be specific with exceptions:

```python
# Good
try:
    result = await tool.execute(**args)
except ToolError as e:
    logger.error(f"Tool {e.tool_name} failed: {e}")
    return f"Error: {e}"
except Exception as e:
    logger.exception("Unexpected error")
    return f"Unexpected error: {e}"

# Bad - catching everything
try:
    result = await tool.execute(**args)
except:
    return "Error"
```

### Error Messages

Provide actionable error messages:

```python
# Good
raise ConfigError(
    f"Config file not found: {path}\n"
    f"Create one at ~/.config/ai-agent/config.toml"
)

# Bad
raise ConfigError("Config error")
```

---

## Testing

### Test Structure

```python
# tests/test_feature.py
import pytest
from friday_ai.feature import Feature


class TestFeature:
    @pytest.fixture
    def feature(self):
        return Feature()

    @pytest.mark.asyncio
    async def test_success_case(self, feature):
        result = await feature.process("input")
        assert result == "expected"

    @pytest.mark.asyncio
    async def test_error_case(self, feature):
        with pytest.raises(ValueError):
            await feature.process(None)
```

### Mocking

Mock external dependencies:

```python
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_with_mock():
    with patch("friday_ai.client.llm_client.AsyncOpenAI") as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        mock_client.chat.completions.create = Mock(
            return_value=mock_response
        )

        result = await client.chat_completion(messages)
        assert result is not None
```

### Fixtures

Use fixtures for common setup:

```python
@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory."""
    return tmp_path

@pytest.fixture
async def agent(config):
    """Provide a configured agent."""
    async with Agent(config) as agent:
        yield agent
```

---

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def execute_tool(
    name: str,
    arguments: dict[str, Any],
    timeout: float = 30.0
) -> str:
    """Execute a tool by name with given arguments.

    Args:
        name: Name of the tool to execute
        arguments: Dictionary of argument names to values
        timeout: Maximum time to wait for execution (seconds)

    Returns:
        Tool execution result as string

    Raises:
        ToolError: If tool execution fails
        ToolNotFoundError: If tool doesn't exist
        TimeoutError: If execution exceeds timeout

    Example:
        >>> result = await execute_tool(
        ...     "read_file",
        ...     {"path": "main.py"}
        ... )
        >>> print(result)
        "Content of main.py..."
    """
```

### Module Documentation

```python
"""Tool registry module.

Provides the ToolRegistry class for managing tool registration
and lookup. Supports built-in tools, MCP tools, and dynamically
discovered tools.

Example:
    >>> registry = ToolRegistry()
    >>> registry.register(MyTool())
    >>> tool = registry.get("my_tool")
"""
```

### Type Documentation

```python
from typing import TypeAlias

# Define type aliases for complex types
ToolResult: TypeAlias = str
ToolArguments: TypeAlias = dict[str, Any]
EventHandler: TypeAlias = Callable[[AgentEvent], None]
```

---

## Code Review Guidelines

### Before Submitting

- [ ] Run `pytest tests/` - all tests pass
- [ ] Run type checker: `mypy friday_ai/`
- [ ] Run linter: `ruff check friday_ai/`
- [ ] Run formatter: `black friday_ai/`

### Checklist

- [ ] Code is readable and well-structured
- [ ] Functions are small and focused
- [ ] Error handling is comprehensive
- [ ] Tests cover success and failure cases
- [ ] Documentation is clear and complete
- [ ] No hardcoded secrets or paths
- [ ] Async/await used correctly

---

*Best Practices v1.0 - Friday AI Teammate*
