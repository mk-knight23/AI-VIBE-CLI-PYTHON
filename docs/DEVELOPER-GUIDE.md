# Friday AI - Developer Guide

Complete developer documentation for contributing to Friday AI Teammate.

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Coding Standards](#coding-standards)
4. [Adding New Tools](#adding-new-tools)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Architecture](#architecture)
8. [Best Practices](#best-practices)
9. [Security Considerations](#security-considerations)
10. [Release Process](#release-process)

---

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv)

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/mk-knight23/AI-VIBE-CLI-PYTHON.git
cd AI-VIBE-CLI-PYTHON

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

# Check test coverage
pytest --cov=friday_ai tests/
```

---

## Project Structure

```
friday_ai/
├── agent/              # Core agent logic
│   ├── agent.py       # Main agent loop
│   ├── autonomous_loop.py  # Ralph-inspired autonomous mode
│   ├── session_manager.py  # Session persistence
│   ├── events.py      # Event system
│   └── persistence.py # Snapshot management
├── api/                # REST API server (NEW v1.0)
│   ├── routers/       # API endpoints
│   ├── models/        # Request/response models
│   └── services/      # Business logic
├── auth/               # Authentication (NEW v1.0)
│   └── api_keys.py    # API key management
├── client/             # LLM client
│   ├── llm_client.py  # OpenAI-compatible client
│   └── response.py    # Response handling
├── config/             # Configuration
│   ├── config.py      # Pydantic config
│   └── loader.py      # Config loading
├── context/            # Context management
│   ├── manager.py     # Message context
│   ├── compaction.py  # Context compression
│   └── loop_detector.py # Loop detection
├── database/           # Database layer (NEW v1.0)
│   ├── pool.py        # Connection pooling
│   ├── memory_backend.py
│   └── redis_backend.py
├── mcp/                # MCP integration (NEW v1.0)
│   └── server.py      # MCP server
├── monitoring/         # Performance monitoring (NEW v1.0)
│   └── dashboard.py   # Metrics dashboard
├── observability/      # Monitoring (NEW v1.0)
│   └── metrics.py     # Prometheus metrics
├── ratelimit/          # Rate limiting (NEW v1.0)
│   └── middleware.py  # Rate limit middleware
├── resilience/         # Fault tolerance (NEW v1.0)
│   ├── retry.py       # Exponential backoff
│   └── health_checks.py # Health checks
├── safety/             # Safety features
│   └── approval.py    # Approval policies
├── security/           # Security (NEW v1.0)
│   ├── audit_logger.py    # Audit logging
│   ├── secret_manager.py  # Secret management
│   └── validators.py      # Input validation
├── streaming/          # Streaming responses (NEW v1.0)
│   └── response.py    # Event streaming
├── workflow/           # Workflow execution (NEW v1.0)
│   └── executor.py    # Step execution
├── tools/              # Tool system
│   ├── builtin/       # Built-in tools
│   ├── mcp/           # MCP integration
│   ├── base.py        # Tool base classes
│   ├── registry.py    # Tool registry
│   └── discovery.py   # Dynamic tool discovery
├── ui/                 # Terminal UI
│   └── tui.py         # Rich console UI
├── utils/              # Utilities
│   └── errors.py      # Error hierarchy
├── prompts/            # System prompts
│   └── system.py      # Prompt generation
└── main.py             # CLI entry point
```

---

## Coding Standards

### Python Style

Follow PEP 8 with these specifics:

```python
# Use type hints
def process_file(file_path: str) -> dict[str, Any]:
    """Process a file and return results.

    Args:
        file_path: Path to the file to process.

    Returns:
        Dictionary with processing results.
    """
    pass

# Use async/await for I/O
async def fetch_data(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

# Context managers for resources
async with async_open(file_path) as f:
    content = await f.read()
```

### File Organization

**MANY SMALL FILES > FEW LARGE FILES:**
- High cohesion, low coupling
- 200-400 lines typical, 800 max
- Extract utilities from large components
- Organize by feature/domain

### Error Handling

```python
try:
    result = await risky_operation()
    return result
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise FridayError(
        message="Detailed user-friendly message",
        code="OPERATION_FAILED",
        details={"context": "value"},
        retryable=True
    )
```

### Immutability

```python
# WRONG: Mutation
def update_user(user, name):
    user.name = name  # MUTATION!
    return user

# CORRECT: Immutability
def update_user(user, name):
    return {
        **user,
        "name": name
    }
```

---

## Adding New Tools

### Tool Template

```python
# friday_ai/tools/builtin/my_tool.py
from typing import Any
from pydantic import BaseModel, Field

from friday_ai.tools.base import Tool, ToolParameter, ToolResult

class MyToolParams(BaseModel):
    """Parameters for my_tool."""
    
    argument: str = Field(..., description="Description of argument")
    optional_param: int = Field(default=42, description="Optional parameter")

class MyTool(Tool):
    """Description of what this tool does."""
    
    name = "my_tool"
    description = "A brief description for the AI"
    parameters = [
        ToolParameter(
            name="argument",
            type="string",
            required=True,
            description="Description of argument"
        ),
        ToolParameter(
            name="optional_param",
            type="integer",
            required=False,
            description="Optional parameter"
        )
    ]
    
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute the tool.
        
        Args:
            invocation: Tool invocation with parameters.
            
        Returns:
            Tool result with output or error.
        """
        try:
            params = MyToolParams(**invocation.params)
            
            # Your implementation here
            result = f"Processed: {params.argument}"
            
            return ToolResult.success_result(result)
            
        except Exception as e:
            return ToolResult.error_result(f"Error: {e}")
```

### Register Your Tool

Add to `friday_ai/agent/session.py`:

```python
from friday_ai.tools.builtin.my_tool import MyTool

# In _init_tools()
self.tools.register(MyTool())
```

---

## Testing

### Test Structure

```
tests/
├── test_tools/          # Tool tests
├── test_integration/    # Integration tests
├── test_api/            # API tests (NEW v1.0)
└── test_claude_integration/  # Claude integration tests
```

### Writing Tests

```python
# tests/test_tools/test_my_tool.py
import pytest
from friday_ai.tools.builtin.my_tool import MyTool
from friday_ai.tools.base import ToolInvocation

@pytest.mark.asyncio
async def test_my_tool_success():
    """Test my_tool with valid input."""
    tool = MyTool()
    invocation = ToolInvocation(
        id="test-1",
        name="my_tool",
        params={"argument": "test"}
    )
    
    result = await tool.execute(invocation)
    
    assert result.success
    assert "Processed: test" in result.output

@pytest.mark.asyncio
async def test_my_tool_error():
    """Test my_tool with invalid input."""
    tool = MyTool()
    invocation = ToolInvocation(
        id="test-2",
        name="my_tool",
        params={}  # Missing required param
    )
    
    result = await tool.execute(invocation)
    
    assert not result.success
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific file
pytest tests/test_tools/test_my_tool.py -v

# With coverage
pytest --cov=friday_ai --cov-report=html tests/

# Specific marker
pytest -m "not slow" -v
```

### Test Coverage

**Minimum: 80% coverage required**

```bash
# Check coverage
pytest --cov=friday_ai --cov-report=term-missing tests/

# Generate HTML report
pytest --cov=friday_ai --cov-report=html tests/
open htmlcov/index.html
```

---

## Architecture

### Core Components

1. **Agent Loop** (`agent.py`)
   - Main execution loop
   - Tool orchestration
   - Response streaming

2. **Context Manager** (`context/manager.py`)
   - Message history
   - Context window management
   - Compaction

3. **Tool System** (`tools/`)
   - Base classes
   - Registry
   - Discovery
   - MCP integration

4. **LLM Client** (`client/llm_client.py`)
   - OpenAI-compatible API
   - Async streaming
   - Error handling

### Design Patterns

- **Event-Driven** - Agent emits events for UI updates
- **Tool Registry** - Dynamic tool registration
- **Async/Await** - All I/O operations
- **Context Managers** - Resource management
- **Circuit Breaker** - Prevents runaway loops
- **Retry with Backoff** - Resilient operations (v1.0)

---

## Best Practices

### 1. Type Hints

Always use type hints:

```python
def process(data: list[str]) -> dict[str, int]:
    return {"count": len(data)}
```

### 2. Docstrings

Use Google-style docstrings:

```python
def complex_function(arg1: str, arg2: int) -> bool:
    """One-line summary.

    Longer description with details.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: If arg1 is invalid
    """
    pass
```

### 3. Error Handling

```python
# Always handle errors
try:
    result = await operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise

# Use custom error classes
from friday_ai.utils.errors import FridayError

raise FridayError(
    message="User-friendly message",
    code="ERROR_CODE",
    details={"key": "value"},
    retryable=False
)
```

### 4. Async Best Practices

```python
# Use async for I/O
async def fetch_all(urls: list[str]) -> list[str]:
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.text for r in responses]
```

### 5. Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed debug info")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

---

## Security Considerations

### Input Validation

Always validate user input:

```python
from friday_ai.security.validators import InputValidator

validator = InputValidator()
validator.validate_path(file_path)  # Raises if invalid
validator.validate_command(command)  # Checks for injection
```

### Secret Management

Never hardcode secrets:

```python
# WRONG
api_key = "sk-proj-xxxxx"

# CORRECT
import os
api_key = os.environ.get("API_KEY")
if not api_key:
    raise ConfigError("API_KEY not configured")
```

Use the secret manager:

```python
from friday_ai.security.secret_manager import SecretManager

secrets = SecretManager()
api_key = await secrets.get("my_api_key")
```

### Path Traversal Prevention

```python
from pathlib import Path

def safe_read(file_path: str) -> str:
    """Safely read a file, preventing path traversal."""
    path = Path(file_path).resolve()
    
    # Ensure path is within allowed directory
    allowed_dir = Path("/allowed/dir").resolve()
    if not str(path).startswith(str(allowed_dir)):
        raise PathTraversalError(path)
    
    return path.read_text()
```

---

## Release Process

### Version Bump

1. Update version in `pyproject.toml`
2. Update version in `friday_ai/main.py`
3. Update CHANGELOG.md
4. Commit changes

### Build & Publish

```bash
# Build
python -m build

# Test with TestPyPI
twine upload --repository testpypi dist/*

# Publish to PyPI
twine upload dist/*
```

### Git Tag

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## Contributing

### Before Contributing

1. Check existing issues
2. Discuss large changes first
3. Write tests first (TDD)
4. Follow coding standards
5. Update documentation

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Write tests
4. Implement feature
5. Run tests: `pytest tests/ -v`
6. Update documentation
7. Submit PR with clear description

### Code Review Checklist

- [ ] Tests pass (100% pass rate)
- [ ] Coverage ≥ 80%
- [ ] Type hints on all functions
- [ ] Docstrings on public APIs
- [ ] No hardcoded secrets
- [ ] Error handling comprehensive
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

---

*Friday AI Teammate v1.0.0 - Developer Guide*
