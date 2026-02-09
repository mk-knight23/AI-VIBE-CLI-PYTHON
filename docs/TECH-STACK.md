# Friday AI - Technology Stack
## Architecture and Technology Overview

---

## Table of Contents

1. [Core Technologies](#core-technologies)
2. [Project Structure](#project-structure)
3. [Key Dependencies](#key-dependencies)
4. [Architecture Overview](#architecture-overview)
5. [Data Flow](#data-flow)
6. [Extensibility Points](#extensibility-points)

---

## Core Technologies

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Python | 3.10+ | Core runtime |
| **CLI Framework** | Click | 8.0+ | Command-line interface |
| **Data Validation** | Pydantic | 2.0+ | Configuration and data models |
| **Terminal UI** | Rich | 13.0+ | Terminal formatting and UI |
| **HTTP Client** | HTTPX | 0.25+ | Async HTTP requests |
| **LLM Client** | OpenAI SDK | 1.0+ | OpenAI-compatible API |
| **Web Search** | DDGS | 6.0+ | DuckDuckGo search |
| **MCP Client** | FastMCP | 0.4+ | Model Context Protocol |

---

## Project Structure

```
friday_ai/
├── __init__.py              # Package initialization
├── __main__.py              # Entry point for python -m friday_ai
├── main.py                  # CLI definition and main loop
│
├── agent/                   # Core agent logic
│   ├── __init__.py
│   ├── agent.py            # Main agent orchestration
│   ├── events.py           # Event types and streaming
│   ├── persistence.py      # Session save/load
│   └── session.py          # Session management
│
├── client/                  # LLM client
│   ├── __init__.py
│   ├── llm_client.py       # OpenAI-compatible client
│   └── response.py         # Response parsing
│
├── config/                  # Configuration management
│   ├── __init__.py
│   ├── config.py           # Configuration models
│   └── loader.py           # Config file loading
│
├── context/                 # Context management
│   ├── __init__.py
│   ├── compaction.py       # Token management
│   ├── loop_detector.py    # Infinite loop prevention
│   └── manager.py          # Message context management
│
├── hooks/                   # Hook system
│   ├── __init__.py
│   └── hook_system.py      # Hook execution
│
├── prompts/                 # System prompts
│   ├── __init__.py
│   └── system.py           # Default system prompts
│
├── safety/                  # Safety features
│   ├── __init__.py
│   └── approval.py         # Approval policy handling
│
├── tools/                   # Tool system
│   ├── __init__.py
│   ├── base.py             # Tool base class
│   ├── discovery.py        # Dynamic tool discovery
│   ├── registry.py         # Tool registry
│   ├── subagents.py        # Subagent implementations
│   ├── builtin/            # Built-in tools
│   │   ├── __init__.py
│   │   ├── edit_file.py
│   │   ├── glob.py
│   │   ├── grep.py
│   │   ├── list_dir.py
│   │   ├── memory.py
│   │   ├── read_file.py
│   │   ├── shell.py
│   │   ├── todos.py
│   │   ├── web_fetch.py
│   │   ├── web_search.py
│   │   └── write_file.py
│   └── mcp/                # MCP integration
│       ├── __init__.py
│       ├── client.py
│       ├── mcp_manager.py
│       └── mcp_tool.py
│
├── ui/                      # User interface
│   ├── __init__.py
│   └── tui.py              # Terminal UI (Rich-based)
│
└── utils/                   # Utilities
    ├── __init__.py
    ├── errors.py           # Error types
    ├── paths.py            # Path utilities
    └── text.py             # Text processing
```

---

## Key Dependencies

### Core Framework

```python
# pydantic - Data validation and settings management
from pydantic import BaseModel, Field

# click - CLI framework
import click

# rich - Terminal UI
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
```

### LLM Integration

```python
# openai - OpenAI-compatible API client
from openai import AsyncOpenAI

# tiktoken - Token counting (optional)
import tiktoken
```

### Async HTTP

```python
# httpx - Async HTTP client
import httpx

# ddgs - DuckDuckGo search
from ddgs import DDGS
```

### MCP (Model Context Protocol)

```python
# fastmcp - MCP client implementation
from fastmcp import Client
```

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│                    (click, main.py)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer                             │
│              (Agent, Session, Events)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────────────┐
│                      Tool System                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Built-in     │  │ MCP Tools    │  │ Dynamic Tools   │   │
│  │ (11 tools)   │  │ (external)   │  │ (user-defined)  │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────────────┐
│                     LLM Client Layer                         │
│              (OpenAI-compatible API)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────────────┐
│                   AI Provider                                │
│     (GLM, MiniMax, OpenAI, Anthropic, etc.)                │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

#### 1. Event-Driven Architecture

```python
# events.py
class AgentEventType(Enum):
    TEXT_DELTA = "text_delta"
    TEXT_COMPLETE = "text_complete"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    AGENT_ERROR = "agent_error"

@dataclass
class AgentEvent:
    type: AgentEventType
    data: dict[str, Any]
```

#### 2. Tool Registry Pattern

```python
# tools/registry.py
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_tools(self) -> list[Tool]:
        return list(self._tools.values())
```

#### 3. Async Context Managers

```python
# agent/agent.py
class Agent:
    async def __aenter__(self) -> "Agent":
        await self.initialize()
        return self

    async def __aexit__(self, *args) -> None:
        await self.cleanup()
```

---

## Data Flow

### Request Flow

```
1. User Input
   ↓
2. CLI parses input (click)
   ↓
3. Config is loaded (loader.py)
   ↓
4. Agent is initialized (agent.py)
   ↓
5. Context is built (context/manager.py)
   ↓
6. LLM is called (client/llm_client.py)
   ↓
7. Response is streamed (events)
   ↓
8. Tool calls are executed (tools/)
   ↓
9. Results are returned to LLM
   ↓
10. Final response to user (ui/tui.py)
```

### Tool Execution Flow

```
Tool Call Detected
   ↓
Parse tool name and arguments
   ↓
Lookup tool in registry
   ↓
Check approval policy
   ↓
Execute tool
   ↓
Stream result to UI
   ↓
Add result to context
   ↓
Continue LLM conversation
```

---

## Extensibility Points

### 1. Custom Tools

Create tools in `.ai-agent/tools/`:

```python
from friday_ai.tools.base import Tool, ToolParameter

class MyTool(Tool):
    name = "my_tool"
    description = "Does something"
    parameters = [...]

    async def execute(self, **kwargs) -> str:
        return "result"
```

### 2. MCP Servers

Add external tools via MCP:

```toml
[mcp_servers.my-server]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-name"]
enabled = true
```

### 3. Hooks

Add custom logic at execution points:

```toml
[[hooks]]
name = "my-hook"
trigger = "after_tool"
command = "python3 /path/to/script.py"
enabled = true
```

### 4. Custom Subagents

Extend subagents for specialized tasks:

```python
from friday_ai.tools.subagents import SubAgent

class MySubAgent(SubAgent):
    name = "my_subagent"

    async def run(self, task: str) -> str:
        # Custom implementation
        pass
```

---

## Performance Considerations

### Async Architecture

- All I/O operations are async
- Concurrent tool execution support
- Streaming responses for low latency

### Context Management

- Automatic token counting
- Context compaction when approaching limits
- Loop detection to prevent infinite loops

### Caching

- Session persistence for resumability
- Memory tool for cross-session storage

---

## Security Architecture

### Approval System

- Configurable approval policies
- Dangerous command detection
- Path validation for file operations

### Secret Handling

- Environment variable filtering
- Secret pattern detection in output
- Configurable exclusion patterns

### Sandboxing

- Working directory restrictions
- Shell command allowlisting (configurable)
- MCP server isolation

---

*Technology Stack v1.0 - Friday AI Teammate*
