# Friday AI Teammate - System Architecture

## Overview

Friday AI Teammate uses an **event-driven architecture** with clean separation of concerns through composition and modular design.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI Layer (main.py)                 │
│  Argument parsing, command routing, session management        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    Agent Layer (agent/)                       │
│  Session orchestration, autonomous mode, metrics           │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Session │ ToolOrchestrator │ SafetyManager   │    │
│  │          │                  │               │    │
│  │ Tool      │  Metrics          │               │    │
│  # Registry  │  # Tracking       │               │    │
│  └──────────┴──────────────────┘               │    │
└─────────────────────────────────────────────────────────┘    │
                       │                                │
┌──────────────────────▼──────────────────────────────────────────┐
│                    Context Layer (context/)                    │
│  Message management, compaction, loop detection           │
│  ┌────────────────────────────────────────────────────┐   │
│  │ ContextManager │ SmartCompactor │ LoopDetector  │   │
│  │                │                │             │   │
│  │ Messages       │ 5 Strategies    │ Recency     │   │
│  └────────────────┴──────────────────────┘       │   │
└─────────────────────────────────────────────────────────┘    │
                       │                                │
┌──────────────────────▼──────────────────────────────────────────┐
│                    Tool Layer (tools/)                       │
│  Built-in tools, MCP integration, tool registry            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ ToolRegistry │ MCPManager │ ToolDiscovery  │   │
│  │              │           │             │   │
│  │ 16 Built-in │ 15+ MCP   │ Dynamic      │   │
│  │    Tools     │  Servers    │ Discovery     │   │
│  └────────────────┴──────────────────────┘       │   │
└─────────────────────────────────────────────────────────┘    │
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    Client Layer (client/)                     │
│  Multi-provider LLM client with smart routing             │
│  ┌────────────────────────────────────────────────────┐   │
│  │ ProviderManager │ 5 Providers │ ProviderRouter  │   │
│  │                │           │            │   │
│  │ Single Point  │ OpenAI     │ Intelligent  │   │
│  │    of       │ Anthropic  │ Routing by  │   │
│  │ Truth     │ Google     │ Complexity   │   │
│  │           │ Groq       │             │   │
│  │           │ Ollama     │ Cost Track  │   │
│  └────────────────┴──────────────────────┘       │   │
└─────────────────────────────────────────────────────────┘    │
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    Safety & Security (safety/, security/)      │
│  Approval, validation, audit logging, secrets             │
│  ┌────────────────────────────────────────────────────┐   │
│  │ SafetyManager │ AuditLogger │ SecretManager │   │
│  │              │           │            │   │   │
│  │ Approval     │ Tamper-    │ Enterprise  │   │
│  │ Policies     │ Evident    │ Managers   │   │
│  │              │ Logs       │            │   │   │
│  └────────────────┴──────────────────────┘       │   │
└─────────────────────────────────────────────────────────┘    │
```

## Data Flow

### 1. User Input Flow

```
User Input (CLI/Voice)
        │
        ▼
┌─────────────────┐
│  main.py      │
│  Parse Command│
└──────┬────────┘
       │
       ▼
┌─────────────────────┐
│  Session        │
│  Get/Create     │
└──────┬──────────┘
       │
       ▼
┌─────────────────────────────────┐
│  ToolOrchestrator.init()     │
│  - Load tool registry          │
│  - Initialize MCP servers      │
│  - Discover tools             │
└──────────┬────────────────────┘
           │
           ▼
┌──────────────────────┐
│  ContextManager    │
│  - Load memory    │
│  - Init context  │
└──────┬───────────┘
       │
       ▼
┌─────────────────────────┐
│  Agent Run Loop      │
│  - Process messages │
│  - Call tools      │
│  - Emit events     │
└──────────────────────┘
```

### 2. LLM Request Flow

```
Agent Request
        │
        ▼
┌─────────────────────┐
│  ProviderManager    │
│  Select Provider    │
└──────┬───────────┘
       │
       ▼
┌───────────────────────────┐
│  ProviderRouter      │
│  - Route by        │
│    Complexity      │
│  - Check Cost      │
│  - Fallback        │
└──────┬──────────────┘
       │
       ▼
┌───────────────────────────┐
│  LLMProvider        │
│  - API Call        │
└──────┬───────────────┘
       │
       ▼
  Streaming Response
```

### 3. Event Flow

```
Component Event        Emitted By               │
────────────────────────────────────────────│
Agent Start        Session                  │
Tool Call Start   ToolOrchestrator        │
Tool Complete     ToolOrchestrator        │
Text Delta       LLMClient                │
Message Complete LLMClient                │
Agent End        Session                  │
Error           Any component            │

        ▼
┌─────────────────────────┐
│  HookSystem       │
│  - PreToolUse      │
│  - PostToolUse     │
│  - Stop            │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────────┐
│  Registered Hooks │
│  - Format/Check    │
│  - Auto-save       │
└──────────────────────┘
```

## Component Interaction

### Session Lifecycle

1. **Initialization**
   ```
   main.py
       │
       ▼
   Session.__init__()
       │
       ├─► ToolOrchestrator (tool registry, MCP)
       ├─► SafetyManager (approval, validation)
       ├─► SessionMetrics (stats tracking)
       ├─► ChatCompactor (context compression)
       ├─► LoopDetector (infinite loop prevention)
       └─► HookSystem (extensibility)
   ```

2. **Tool Execution**
   ```
   Agent.run_tool()
       │
       ▼
   ToolOrchestrator
       │
       ├─► Check approval (SafetyManager)
       ├─► Validate input (SafetyManager)
       ├─► Execute tool
       └─► Record usage (SessionMetrics)
   ```

3. **Context Management**
   ```
   Agent.process_message()
       │
       ▼
   ContextManager
       │
       ├─► Add message to history
       ├─► Check token count
       ├─► Trigger compaction if needed (SmartCompactor)
       └─► Detect loops (LoopDetector)
   ```

## Design Patterns

### 1. Event-Driven Architecture

**Purpose:** Loose coupling between components

**Implementation:**
```python
# friday_ai/agent/events.py
class AgentEventType(str, Enum):
    AGENT_START = "agent_start"
    TOOL_CALL_START = "tool_call_start"
    TEXT_DELTA = "text_delta"

# Usage
agent.emit_event(AgentEventType.TOOL_CALL_START, tool_data)
```

**Benefits:**
- UI components can subscribe to events
- Easy to add new event types
- No direct dependencies between emitter and receiver

### 2. Tool Registry Pattern

**Purpose:** Dynamic tool registration and discovery

**Implementation:**
```python
# friday_ai/tools/registry.py
class ToolRegistry:
    def register_tool(self, tool: Tool) -> None
    def get_tool(self, name: str) -> Tool | None
    def get_tools(self) -> list[Tool]

# Tool discovery
discovery_manager.discover_all()  # Load from .friday/tools/
mcp_manager.register_tools()          # Register MCP tools
```

**Benefits:**
- Tools can be added at runtime
- MCP servers can expose new tools
- No code changes needed for new tools

### 3. Composition Over Inheritance

**Purpose:** Flexible component assembly

**Implementation:**
```python
# friday_ai/agent/session.py (v2.1)
class Session:
    def __init__(self, config: Config):
        # Compose specialized components
        self.tool_orchestrator = ToolOrchestrator(config, tool_registry)
        self.safety_manager = SafetyManager(approval, cwd)
        self.metrics = SessionMetrics(session_id)

# vs (v1.0)
class Session:
    def __init__(self, config: Config):
        # Direct management of 8+ concerns
        self.tool_registry = create_default_registry(config)
        self.mcp_manager = MCPManager(config)
        self.approval_manager = ApprovalManager(config.approval, config.cwd)
        # ... (92 lines of mixed responsibilities)
```

**Benefits:**
- Each component has single responsibility
- Components can be tested independently
- Easy to swap implementations
- Better adherence to SOLID principles

### 4. Strategy Pattern

**Purpose:** Encapsulate algorithms

**Implementation:**
```python
# friday_ai/context/strategies.py
class CompactionStrategy(Enum):
    TOKEN_BASED = "token"
    RELEVANCE = "relevance"
    HYBRID = "hybrid"

class SmartCompactor:
    def compact(self, messages, strategy: CompactionStrategy):
        # Strategy-based compaction algorithm
```

**Benefits:**
- Algorithms can be changed at runtime
- Multiple strategies can coexist
- Easy to add new strategies
- Strategy selection is configurable

## Technology Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** Asyncio (async/await)
- **Validation:** Pydantic v2.0+
- **CLI:** Click 8.0+
- **UI:** Rich 13.0+

### LLM Providers
- OpenAI SDK (openai>=1.0.0)
- Anthropic SDK (anthropic>=0.18.0)
- Google AI (google-generativeai>=0.3.0)
- Groq (groq>=0.4.0)
- Ollama (ollama>=0.1.0)

### Infrastructure
- **MCP:** fastmcp>=0.4.0
- **Databases:** asyncpg>=0.29.0, aiomysql>=0.2.0, redis>=5.0.0
- **Search:** DuckDuckGo (ddgs>=6.0.0)
- **HTTP:** httpx>=0.25.0

### Development Tools
- **Testing:** pytest>=8.0, pytest-asyncio>=0.23, pytest-cov>=4.1
- **Code Quality:** black>=24.1, ruff>=0.2, mypy>=1.8
- **Hooks:** pre-commit>=3.6

## Security Architecture

### Layers
1. **Approval Manager** - User confirmation for dangerous operations
2. **Input Validation** - Path traversal prevention, command validation
3. **Secret Scrubbing** - Remove secrets from logs/output
4. **Audit Logging** - Tamper-evident security logs
5. **Circuit Breaker** - Prevent runaway autonomous loops

### Safety Features
- Configurable approval policies (yolo, auto, on-request, never)
- Dangerous command whitelist
- File operation restrictions (cwd bounds)
- SQL injection prevention
- XSS prevention in web outputs

## Performance Optimization

### Caching Strategies
- Tool registry cache (avoid repeated lookups)
- Provider info cache (latency, costs)
- Compiled regex patterns
- Lazy loading of non-critical components

### Async Operations
- All I/O operations are async
- Parallel MCP server initialization
- Concurrent tool execution where possible

### Resource Management
- Connection pooling for databases
- Context compaction (prevent token overflow)
- Session cleanup on exit
- Proper resource disposal

## Extensibility Points

### 1. Tool System
```python
# Built-in tool
class CustomTool(Tool):
    name = "custom_tool"
    async def execute(self, invocation):
        # Implementation

# Register
tool_registry.register_tool(CustomTool())
```

### 2. MCP Servers
```python
# Add to config.toml
[mcp_servers.my_server]
command = "npx"
args = ["-y", "@myorg/mcp-server"]

# Automatically discovered and initialized
```

### 3. Hooks
```python
# Register hook
@hook_system.register("PreToolUse")
async def my_hook(context: ToolContext):
    # Validate or modify
    pass
```

### 4. Skills
```python
# Create skill in .claude/skills/
# ---
name: "My Skill"
description: "Does something cool"
requirements:
  - some-package
# ---
# Automatically loaded and available
```

## Deployment Architecture

### Development
```
pip install -e ".[dev]"
pytest --cov=friday_ai --cov-report=html
black --check friday_ai tests
ruff check friday_ai tests
mypy friday_ai
```

### Production
```
pip install friday-ai-teammate
friday
```

### Docker (Future)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install .
CMD ["friday"]
```

## Monitoring

### Metrics Collection
- Turn count (SessionMetrics)
- Tool usage statistics
- Token usage tracking
- Provider performance
- Cost tracking by provider

### Observability
- Structured JSON logging
- Distributed tracing (future)
- Health check endpoints
- Performance profiling

---

*Architecture documentation for Friday AI Teammate v2.1.0*
