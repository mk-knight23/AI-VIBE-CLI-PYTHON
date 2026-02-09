# Friday AI - Developer Guide
## Contributing to Friday AI Teammate

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Coding Standards](#coding-standards)
4. [Adding New Tools](#adding-new-tools)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Release Process](#release-process)

---

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv)

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/mk-knight23/Friday.git
cd Friday

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Check friday is installed
friday --help

# Run tests
pytest tests/ -v
```

---

## Project Structure

```
friday_ai/
├── agent/          # Core agent logic
├── client/         # LLM client
├── config/         # Configuration
├── context/        # Context management
├── hooks/          # Hook system
├── prompts/        # System prompts
├── safety/         # Safety features
├── tools/          # Tool system
│   ├── builtin/    # Built-in tools
│   └── mcp/        # MCP integration
├── ui/             # Terminal UI
└── utils/          # Utilities
```

---

## Coding Standards

### Python Style

Follow PEP 8 with these specifics:

```python
# Use type hints
def process_data(data: dict[str, Any]) -> str:
    return str(data)

# Async/await for I/O
async def fetch_data(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.content

# Docstrings for public functions
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers.

    Args:
        a: First integer
        b: Second integer

    Returns:
        Sum of a and b
    """
    return a + b
```

### Import Ordering

```python
# 1. Standard library
import asyncio
from pathlib import Path

# 2. Third-party
import click
from rich.console import Console

# 3. Local
from friday_ai.tools.base import Tool
from friday_ai.utils.errors import ConfigError
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `ToolRegistry`, `AgentConfig` |
| Functions | snake_case | `execute_tool()`, `load_config()` |
| Variables | snake_case | `tool_name`, `max_retries` |
| Constants | UPPER_CASE | `DEFAULT_TIMEOUT`, `MAX_TURNS` |
| Private | _prefix | `_internal_helper()` |

---

## Adding New Tools

### Built-in Tool Template

Create a new file in `friday_ai/tools/builtin/`:

```python
# friday_ai/tools/builtin/my_tool.py
from typing import Any
from friday_ai.tools.base import Tool, ToolParameter


class MyTool(Tool):
    """Description of what this tool does."""

    name = "my_tool"
    description = "Clear description for the AI"
    parameters = [
        ToolParameter(
            name="param1",
            type="string",
            description="What this parameter does",
            required=True
        ),
        ToolParameter(
            name="param2",
            type="integer",
            description="Optional parameter",
            required=False
        )
    ]

    async def execute(self, param1: str, param2: int = 10) -> str:
        """Execute the tool.

        Args:
            param1: First parameter
            param2: Second parameter with default

        Returns:
            Result as string
        """
        try:
            # Your implementation here
            result = f"Processed: {param1} with value {param2}"
            return result
        except Exception as e:
            return f"Error: {e}"
```

### Register the Tool

Add to `friday_ai/tools/builtin/__init__.py`:

```python
from .my_tool import MyTool

__all__ = [
    # ... existing tools ...
    "MyTool",
]
```

Add to `friday_ai/agent/session.py`:

```python
from friday_ai.tools.builtin import MyTool

# In initialize() method:
self.tool_registry.register(MyTool())
```

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_all_tools.py -v

# With coverage
pytest tests/ --cov=friday_ai --cov-report=html
```

### Writing Tests

Create tests in `tests/`:

```python
# tests/test_my_feature.py
import pytest
from friday_ai.tools.builtin.my_tool import MyTool


@pytest.fixture
async def my_tool():
    return MyTool()


@pytest.mark.asyncio
async def test_my_tool_success(my_tool):
    result = await my_tool.execute(param1="test", param2=5)
    assert "Processed: test" in result
    assert "5" in result


@pytest.mark.asyncio
async def test_my_tool_default_param(my_tool):
    result = await my_tool.execute(param1="test")
    assert "10" in result  # Default value
```

### Test Categories

| File | Purpose |
|------|---------|
| `test_all_tools.py` | Tool functionality tests |
| `test_security.py` | Security and safety tests |
| `test_real_world.py` | Integration tests |

---

## Debugging

### Enable Debug Logging

```bash
export FRIDAY_DEBUG=1
friday "Test command"
```

### Add Debug Prints

```python
import logging

logger = logging.getLogger(__name__)

# In your code:
logger.debug(f"Processing: {data}")
```

### Using pdb

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or in async code:
await asyncio.sleep(0)  # Set breakpoint here
```

### Common Issues

**Issue: Tool not found**
- Check tool is registered in `session.py`
- Verify `name` attribute matches

**Issue: Config not loading**
- Check file path: `./.ai-agent/config.toml`
- Validate TOML syntax

**Issue: API errors**
- Verify `API_KEY` and `BASE_URL`
- Check API provider status

---

## Release Process

### Version Bump

Update in `pyproject.toml`:

```toml
[project]
version = "0.0.3"
```

### Build and Test

```bash
# Clean build
rm -rf dist/ build/

# Build
python -m build

# Test install
pip install dist/friday_ai_teammate-0.0.3-py3-none-any.whl
```

### Upload to PyPI

```bash
# Upload
python -m twine upload dist/*
```

### Git Tag

```bash
git add -A
git commit -m "v0.0.3: Description of changes"
git tag v0.0.3
git push origin main --tags
```

---

## Code Review Checklist

Before submitting PR:

- [ ] Code follows style guide
- [ ] Type hints added
- [ ] Docstrings added
- [ ] Tests added
- [ ] Tests pass
- [ ] No debug prints left
- [ ] Error handling implemented
- [ ] Async/await used correctly

---

*Developer Guide v1.0 - Friday AI Teammate*
