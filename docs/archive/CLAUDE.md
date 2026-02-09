# Friday AI - Claude Instructions
## AI Assistant Context

---

## Project Overview

This is **Friday AI Teammate**, a Python-based AI assistant CLI tool for terminal-based coding workflows.

**Key Facts:**
- **Language:** Python 3.10+
- **Package Name:** friday-ai-teammate
- **CLI Command:** `friday`
- **Architecture:** Agent-based with tool system
- **License:** MIT
- **Version:** 1.0.0

---

## Architecture

### Core Components

```
friday_ai/
├── agent/          # Agent orchestration, events, session management
├── client/         # LLM client (OpenAI-compatible)
├── config/         # Configuration loading and validation
├── context/        # Context management, loop detection
├── hooks/          # Hook system for extensibility
├── prompts/        # System prompts
├── safety/         # Approval policies and dangerous command detection
├── tools/          # Tool system
│   ├── builtin/    # 11 built-in tools
│   ├── mcp/        # MCP (Model Context Protocol) integration
│   ├── discovery.py  # Dynamic tool discovery
│   ├── registry.py   # Tool registry
│   └── subagents.py  # Subagent implementations
├── ui/             # Rich-based terminal UI
└── utils/          # Utilities
```

### Key Design Patterns

1. **Event-Driven:** Agent emits events for UI updates
2. **Tool Registry:** Tools are registered and looked up by name
3. **Async/Await:** All I/O is async
4. **Context Managers:** Resources managed with async context managers

---

## Development Guidelines

### When Working on This Codebase

1. **Follow Python Best Practices:**
   - Use type hints for all function signatures
   - Follow PEP 8 style guide
   - Use async/await for I/O operations

2. **Adding Tools:**
   - Create tool class in `friday_ai/tools/builtin/`
   - Inherit from `Tool` base class
   - Define `name`, `description`, and `parameters`
   - Implement `execute()` method
   - Register in `friday_ai/agent/session.py`

3. **Error Handling:**
   - Use specific exceptions from `friday_ai.utils.errors`
   - Return error messages as strings from tools (don't raise)
   - Log errors appropriately

4. **Testing:**
   - Add tests in `tests/` directory
   - Use pytest with async support
   - Mock external APIs in tests

### Common Tasks

#### Adding a New Tool

```python
# friday_ai/tools/builtin/my_tool.py
from friday_ai.tools.base import Tool, ToolParameter

class MyTool(Tool):
    name = "my_tool"
    description = "What this tool does"
    parameters = [
        ToolParameter(name="arg", type="string", required=True)
    ]

    async def execute(self, arg: str) -> str:
        try:
            # Implementation
            return result
        except Exception as e:
            return f"Error: {e}"
```

#### Adding Configuration Options

```python
# friday_ai/config/config.py
class Config(BaseModel):
    # Add new field
    my_setting: str = Field(default="default_value")
```

---

## Documentation Structure

All documentation is in `docs/`:

| File | Purpose |
|------|---------|
| `README.md` | Documentation index |
| `USER-GUIDE.md` | Getting started guide |
| `FEATURE-GUIDE.md` | Complete feature reference |
| `COMMANDS.md` | CLI commands reference |
| `DEVELOPER-GUIDE.md` | Contributing guide |
| `BEST-PRACTICES.md` | Python coding standards |
| `TESTING.md` | Testing guide |
| `SECURITY.md` | Security features |
| `TECH-STACK.md` | Architecture overview |
| `WORKFLOWS.md` | Usage patterns |
| `CICD.md` | CI/CD configuration |
| `CLAUDE.md` | This file - AI assistant context |
| `IMPLEMENTATION-PLAN.md` | Architecture decisions |
| `AUTONOMOUS-MODE.md` | Autonomous development guide |
| `SESSION-MANAGEMENT.md` | Session management guide |
| `UPGRADE-v0.3.0.md` | v0.3.0 upgrade notes |

---

## Important Notes

### Configuration System

- Config files: TOML format
- Locations: `~/.config/ai-agent/config.toml` or `./.ai-agent/config.toml`
- Environment variables override config files
- Required env vars: `API_KEY`, `BASE_URL`

### Safety Features

- Approval policies control tool execution
- Dangerous command detection for shell commands
- Secret scrubbing in output
- Path validation for file operations

### MCP Support

- Model Context Protocol for external tools
- Configure in `config.toml` under `[mcp_servers]`
- Supports stdio and HTTP/SSE transports

### Autonomous Mode

Ralph-inspired autonomous development loop:
- `/autonomous [max_loops]` - Start continuous development
- Dual-condition exit gate (completion indicators + EXIT_SIGNAL)
- Circuit breaker prevents runaway loops
- Rate limiting (100 calls/hour)
- Session continuity across iterations
- Real-time status updates in `.friday/status.json`

### .claude Integration

Full support for `.claude/` folder structure:
- **Agents** (`/agents`) - Load from `.claude/agents/`
- **Skills** (`/skills`) - Load from `.claude/skills/`
- **Commands** (`/command`) - Load from `.claude/commands/`
- **Workflows** (`/workflow`) - Load from `.claude/workflows/`
- **Rules** - Auto-loaded from `.claude/rules/`

---

*Claude Instructions v1.1 - Friday AI Teammate v0.3.0*
