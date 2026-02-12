# Contributing to Friday AI Teammate

Thank you for your interest in contributing to Friday AI Teammate! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Assume good intentions

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- GitHub account
- Familiarity with AI/LLM concepts

### Development Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/your-username/friday.git
cd friday

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies with dev extras
pip install -e ".[dev]"

# 4. Create a branch for your feature
git checkout -b feature/my-feature
```

## Development Workflow

### 1. Code Style

We follow strict code style guidelines to maintain consistency:

#### File Organization
- **Small files**: 200-400 lines typical, 800 lines maximum
- **High cohesion**: Each file has a single, well-defined purpose
- **Low coupling**: Minimize dependencies between modules
- **Domain-driven**: Group by feature/domain, not by type

#### Naming Conventions
```python
# Classes: PascalCase
class ToolOrchestrator:
class SafetyManager:

# Functions and methods: snake_case
def get_tool_info():
def calculate_score():

# Constants: UPPER_SNAKE_CASE
MAX_TOKENS = 4000
DEFAULT_TIMEOUT = 30

# Private: _leading_snake_case
def _internal_helper():
```

#### Type Hints
```python
# All functions must have type hints
def process_message(message: dict[str, Any]) -> str:
    pass

async def execute_tool(name: str, params: dict[str, Any]) -> ToolResult:
    pass
```

#### Documentation Strings
```python
def complex_function(param1: str, param2: int) -> str:
    """
    One-line summary of what this function does.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value
    """
    pass
```

### 2. Code Quality Standards

#### Immutability
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

#### Error Handling
```python
# Always handle errors comprehensively
try:
    result = await risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise UserFacingError(f"Could not complete operation: {e}") from e
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise
```

#### Input Validation
```python
from pydantic import BaseModel, Field, validator

class ToolParams(BaseModel):
    path: str = Field(..., min_length=1)
    count: int = Field(..., gt=0, le=100)

    @validator('path')
    def validate_path(v):
        return validate_path_safe(v, cwd)
```

### 3. Testing Standards

We require comprehensive tests for all contributions:

#### Test Coverage
- **Minimum 80% coverage** for new code
- **Unit tests** for all functions and classes
- **Integration tests** for component interactions
- **E2E tests** for critical user workflows

#### Test Structure
```python
# tests/test_agent_refactor.py
class TestToolOrchestrator:
    def test_initialization(self):
        # Test setup
        pass

    def test_error_cases(self):
        # Test error handling
        pass

# Use pytest fixtures
@pytest.fixture
def config():
    return Mock(spec=Config)

# Use pytest markers
@pytest.mark.slow
def test_slow_operation():
    pass

@pytest.mark.integration
def test_integration():
    pass
```

#### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=friday_ai --cov-report=html

# Run specific test file
pytest tests/test_agent_refactor.py -v

# Run only fast tests (skip slow)
pytest -m "not slow"
```

### 4. Commit Guidelines

We use conventional commits with detailed messages:

#### Commit Message Format
```
<type>: <short description>

<optional detailed body>

<optional footer>
```

#### Types
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring (no functional changes)
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `chore`: Maintenance tasks (dependencies, config)
- `perf`: Performance improvement

#### Examples
```
feat(agent): Add multi-provider LLM support

Implement smart routing with support for OpenAI, Anthropic,
Google Gemini, Groq, and Ollama providers. Includes cost tracking,
quality scoring, and fallback chains.

Phase 1 of v2.1 upgrade plan.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
fix(context): Handle edge case in relevance scoring

Fix case where keyword matching fails on exact match with different
capitalization. Now uses case-insensitive matching.

Fixes #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### 5. Pull Request Guidelines

#### Before Creating PR
1. **Update tests** - Ensure all tests pass
2. **Run linting** - `black --check`, `ruff check`, `mypy`
3. **Update docs** - Document new features
4. **Check coverage** - Verify 80%+ coverage

#### PR Description
```markdown
## Summary
Brief description of changes (2-3 sentences)

## Changes
- [ ] Breaking change with migration guide
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Test Plan
- [ ] All tests pass
- [ ] 80%+ coverage maintained
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guide
- [ ] No new warnings generated
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] CLAUDE.md updated if needed
```

### 6. Code Review Process

All contributions go through code review:

1. **Self-review** - Review your own code first
2. **Automated checks** - CI/CD pipeline runs
3. **Peer review** - Request review from maintainer
4. **Address feedback** - Make requested changes

#### Review Criteria
- **Correctness**: Does it work as intended?
- **Style**: Follows code style guide
- **Testing**: Adequate test coverage?
- **Documentation**: Is it documented?
- **Performance**: No obvious performance issues
- **Security**: No security vulnerabilities?

## Feature Development

### Adding New Tools

```python
# friday_ai/tools/builtin/my_tool.py
from friday_ai.tools.base import Tool, ToolParameter

class MyTool(Tool):
    name = "my_tool"
    description = "What this tool does"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="param",
                type="string",
                required=True,
                description="Parameter description"
            )
        ]

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        try:
            # Implementation here
            result = await self._do_work(invocation.params)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
```

### Adding LLM Providers

```python
# friday_ai/client/providers/my_provider.py
from friday_ai.client.providers.base import BaseProvider

class MyProvider(BaseProvider):
    provider_type = ProviderType.MY_PROVIDER

    async def complete(self, messages, stream=True):
        # Implementation
        pass
```

## Documentation Updates

When adding features, update:

1. **CLAUDE.md** - Add to appropriate section
2. **docs/ARCHITECTURE.md** - Update if architectural change
3. **docs/USER-GUIDE.md** - Add usage examples
4. **README.md** - Update feature list

## Questions?

- Check [existing issues](https://github.com/mk-knight23/Friday/issues)
- Read [documentation](../docs/)
- Ask in [discussions](https://github.com/mk-knight23/Friday/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

*Thank you for contributing to Friday AI Teammate!*
