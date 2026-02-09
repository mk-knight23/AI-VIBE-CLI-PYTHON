# Friday AI - Testing Guide
## Testing Strategy and Patterns

---

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Running Tests](#running-tests)
3. [Test Structure](#test-structure)
4. [Writing Tests](#writing-tests)
5. [Test Fixtures](#test-fixtures)
6. [Mocking](#mocking)
7. [Coverage](#coverage)

---

## Testing Overview

Friday AI uses **pytest** as the testing framework with async support.

### Test Categories

| Category | File | Purpose |
|----------|------|---------|
| Unit Tests | `test_all_tools.py` | Individual tool tests |
| Security Tests | `test_security.py` | Safety and security tests |
| Integration Tests | `test_real_world.py` | End-to-end workflows |

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_all_tools.py -v

# Run specific test
pytest tests/test_all_tools.py::TestReadFile -v

# Run with debug output
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -x
```

### With Coverage

```bash
# Generate coverage report
pytest tests/ --cov=friday_ai

# HTML report
pytest tests/ --cov=friday_ai --cov-report=html

# Open HTML report
open htmlcov/index.html
```

---

## Test Structure

### File Organization

```
tests/
├── __init__.py
├── test_all_tools.py      # Tool unit tests
├── test_security.py       # Security tests
└── test_real_world.py     # Integration tests
```

### Test Class Structure

```python
# tests/test_feature.py
import pytest
from friday_ai.tools.builtin.read_file import ReadFileTool


class TestReadFile:
    """Tests for the read_file tool."""

    @pytest.fixture
    def tool(self):
        """Provide a read_file tool instance."""
        return ReadFileTool()

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary file with content."""
        file = tmp_path / "test.txt"
        file.write_text("Hello, World!")
        return file

    @pytest.mark.asyncio
    async def test_read_existing_file(self, tool, temp_file):
        """Test reading an existing file."""
        result = await tool.execute(path=str(temp_file))
        assert "Hello, World!" in result

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, tool):
        """Test reading a file that doesn't exist."""
        result = await tool.execute(path="/nonexistent/file.txt")
        assert "Error" in result
```

---

## Writing Tests

### Async Test Pattern

```python
import pytest


@pytest.mark.asyncio
async def test_async_function():
    """Test async functions with pytest-asyncio."""
    result = await some_async_function()
    assert result == "expected"
```

### Tool Test Template

```python
# tests/test_my_tool.py
import pytest
from friday_ai.tools.builtin.my_tool import MyTool


class TestMyTool:
    @pytest.fixture
    def tool(self):
        return MyTool()

    @pytest.mark.asyncio
    async def test_success(self, tool):
        """Test successful execution."""
        result = await tool.execute(param="value")
        assert "success" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_input(self, tool):
        """Test with invalid input."""
        result = await tool.execute(param="")
        assert "error" in result.lower() or "invalid" in result.lower()

    @pytest.mark.asyncio
    async def test_required_parameter(self, tool):
        """Test that required parameters are enforced."""
        # Should either raise or return error
        try:
            result = await tool.execute()
            assert "error" in result.lower()
        except TypeError:
            pass  # Also acceptable
```

### Security Test Pattern

```python
# tests/test_security.py
import pytest
from friday_ai.safety.approval import is_dangerous_command


class TestSafety:
    def test_detects_rm_rf(self):
        """Test detection of rm -rf command."""
        assert is_dangerous_command("rm -rf /") is True

    def test_detects_sudo(self):
        """Test detection of sudo commands."""
        assert is_dangerous_command("sudo rm -rf /") is True

    def test_allows_safe_command(self):
        """Test that safe commands pass."""
        assert is_dangerous_command("ls -la") is False
```

---

## Test Fixtures

### Built-in Fixtures

```python
# tmp_path - Temporary directory
@pytest.fixture
def config_file(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("[model]\nname = 'test-model'\n")
    return config

# monkeypatch - Modify environment
@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("BASE_URL", "https://test.com")

# caplog - Capture log output
def test_logging(caplog):
    with caplog.at_level("INFO"):
        do_something()
    assert "Expected message" in caplog.text
```

### Custom Fixtures

```python
# conftest.py or in test file
import pytest
from friday_ai.config.config import Config


@pytest.fixture
def test_config(tmp_path):
    """Provide a test configuration."""
    return Config(
        model={"name": "test-model", "temperature": 0.5},
        cwd=tmp_path,
        approval="yolo"
    )


@pytest.fixture
async def agent(test_config):
    """Provide a configured agent."""
    from friday_ai.agent.agent import Agent
    async with Agent(test_config) as agent:
        yield agent


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "README.md").write_text("# Test Project")
    return tmp_path
```

---

## Mocking

### Mock External APIs

```python
from unittest.mock import Mock, patch, AsyncMock


@pytest.mark.asyncio
async def test_llm_client():
    """Test LLM client with mocked API."""
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Hello"))]

    with patch(
        "friday_ai.client.llm_client.AsyncOpenAI"
    ) as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        from friday_ai.client.llm_client import LLMClient
        client = LLMClient(config)

        result = await client.chat_completion(messages=[])
        assert result is not None
```

### Mock Tool Execution

```python
@pytest.mark.asyncio
async def test_agent_with_mock_tool():
    """Test agent with mocked tool."""
    mock_tool = Mock()
    mock_tool.execute = AsyncMock(return_value="Tool result")

    with patch.object(
        agent.session.tool_registry,
        "get",
        return_value=mock_tool
    ):
        result = await agent.run("Use the tool")
        mock_tool.execute.assert_called_once()
```

### Patch Configuration

```python
def test_with_patched_config(monkeypatch):
    """Test with modified configuration."""
    monkeypatch.setattr(
        "friday_ai.config.config.Config.max_turns",
        10
    )

    config = Config()
    assert config.max_turns == 10
```

---

## Coverage

### Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| Tools | 90% |
| Safety | 95% |
| Config | 80% |
| Agent Core | 85% |

### Viewing Coverage

```bash
# Terminal report
pytest tests/ --cov=friday_ai --cov-report=term-missing

# HTML report with line-by-line
pytest tests/ --cov=friday_ai --cov-report=html
open htmlcov/index.html

# Generate coverage for specific module
pytest tests/test_all_tools.py --cov=friday_ai.tools
```

### Excluding Code from Coverage

```python
# pragma: no cover - for debug-only code
if DEBUG:  # pragma: no cover
    print_debug_info()

# pragma: no cover - for platform-specific
if sys.platform == "win32":  # pragma: no cover
    handle_windows()
```

---

## Integration Testing

### Real-World Scenarios

```python
# tests/test_real_world.py
import pytest


@pytest.mark.asyncio
async def test_codebase_analysis(agent, temp_project):
    """Test analyzing a real codebase."""
    # Create some files
    (temp_project / "main.py").write_text(
        "def main():\n    print('Hello')\n"
    )

    result = await agent.run(
        f"Analyze the codebase at {temp_project}"
    )

    # Should find main.py and analyze it
    assert "main.py" in result or "Hello" in result


@pytest.mark.asyncio
async def test_multi_step_task(agent):
    """Test a multi-step workflow."""
    steps = []

    async for event in agent.run(
        "Create a file, then read it back"
    ):
        if event.type == AgentEventType.TOOL_CALL_COMPLETE:
            steps.append(event.data.get("name"))

    # Should have write_file then read_file
    assert "write_file" in steps
    assert "read_file" in steps
```

---

## Debugging Tests

### Verbose Output

```bash
# Show print statements
pytest tests/ -v -s

# Show local variables on failure
pytest tests/ -v --showlocals

# Enter pdb on failure
pytest tests/ -v --pdb

# Stop at first failure
pytest tests/ -x
```

### Test Debugging

```python
import pytest


def test_with_debugging():
    """Test with debugging output."""
    result = do_something()

    # Add breakpoint for debugging
    import pdb; pdb.set_trace()

    assert result is True
```

---

*Testing Guide v1.0 - Friday AI Teammate*
