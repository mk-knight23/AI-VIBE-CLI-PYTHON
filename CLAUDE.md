# Friday AI Teammate - Complete Project Guide

## Project Overview

**Friday AI Teammate** is a comprehensive, production-ready AI coding assistant CLI tool that provides intelligent code assistance through an event-driven architecture with extensive tool integration, autonomous development capabilities, and full .claude folder support.

**Version:** 2.1.0
**Status:** Enterprise Grade / Production Ready with v2.0 Features Integrated
**License:** MIT
**Total Codebase:** ~50,000+ LOC across 150+ Python files, 40+ test files, and 25+ documentation files

---

## v2.1.0 Features

### Multi-Provider LLM Support

**Smart Provider Routing** - Automatic provider selection based on task complexity:
```bash
friday
> /provider list                    # List all providers
> /provider anthropic                # Switch to Anthropic
> /provider openai                    # Switch to OpenAI
> /cost                             # Show cost tracking
```

**Task Complexity Levels:**
- `SIMPLE` - Basic Q&A, simple code edits
- `MODERATE` - Multi-step reasoning, code reviews
- `COMPLEX` - Architecture decisions, long code generation
- `EXPERT` - Complex problem solving, research

**Supported Providers:**
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3, Claude 3.5 Sonnet)
- Google Gemini (Gemini Pro)
- Groq (Llama models)
- Ollama (Local models)

### Advanced Autonomous Mode

**Goal Parser & Tracker:**
```bash
> /autonomous "Implement user authentication"
> /goals                             # Show current goals
> /goal status <goal_id>          # Check goal progress
```

**Goal Types:** CODING, REFACTORING, DEBUGGING, TESTING, DOCUMENTATION, RESEARCH, ARCHITECTURE, DEPLOYMENT, ANALYSIS

**Self-Healing:**
- Syntax error detection and auto-fix
- Import error resolution
- Type error handling
- Dependency missing detection

### Agent Swarm Mode

**Multi-Agent Orchestration:**
- Hierarchical agents: Architect → Coder → Tester → Reviewer
- Parallel task execution
- Load-balanced task distribution

### RAG System (Codebase Intelligence)

**Semantic Code Search:**
```bash
> /index ./src                    # Index codebase for RAG
> /search "UserManager class"       # Semantic search
> /ask "What does UserManager do?"  # Codebase Q&A
```

### Voice I/O

**Voice Commands:**
```bash
> /voice on                          # Enable voice input/output
> /voice off                         # Disable voice
> /voice status                       # Check voice status
```

**Supported Engines:**
- Input: Sphinx, Google, Whisper
- Output: pyttsx3, gTTS

### Kubernetes Integration

**Cluster Management:**
```bash
> /k8s pods                         # List all pods
> /k8s logs <pod>                 # Get pod logs
> /k8s exec <pod> -- command       # Execute in pod
> /k8s scale <deployment> <replicas>  # Scale deployment
```

### Enhanced MCP Ecosystem

**15+ Pre-configured Servers:**
- `filesystem` - File operations
- `github` - Repositories, issues, PRs
- `postgres`, `redis` - Databases
- `slack` - Messaging
- `google-maps` - Location services
- `puppeteer` - Browser automation
- `brave-search` - Web search

**Quick Install:**
```bash
> /mcp install filesystem           # One-click install
> /mcp list                         # List all servers
> /mcp search "postgres"           # Search servers
```

### Skills System v2

**Remote Skill Registry:**
- Community skill sharing
- Dependency resolution
- Version management
- Search and discovery

```bash
> /skills list                       # List all skills
> /skills install <name>            # Install skill
> /skills update <name>             # Update skill
```

### Refactored Architecture (v2.1)

**Extracted Components:**
- `ToolOrchestrator` - Tool management, MCP integration
- `SafetyManager` - Approval, validation, sanitization
- `SessionMetrics` - Session statistics and performance
- `SmartCompactor` - Multi-strategy context compaction

**Compaction Strategies:**
- `TOKEN_BASED` - Simple token count (legacy)
- `RELEVANCE` - Score by relevance to current query
- `RECENCY` - Prioritize recent messages
- `IMPORTANCE` - Keep tool calls and important messages
- `SEMANTIC` - Embedding-based similarity (future)
- `HYBRID` - Weighted combination (default)

**Benefits:**
- Reduced coupling (composition over inheritance)
- Clear separation of concerns
- Easier testing with mock components
- Better adherence to SOLID principles

---

## Quick Reference

### Installation
```bash
pip install friday-ai-teammate
```

### Basic Usage
```bash
# Interactive mode
friday

# Single prompt
friday "Your question here"

# With resume
friday --resume
```

### Essential Commands
| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/autonomous [max_loops]` | Start autonomous development loop |
| `/plan "task"` | Use planner agent |
| `/tdd` | Run TDD workflow |
| `/code-review` | Run code review agent |
| `/save` | Save current session |
| `/resume [session_id]` | Resume saved session |
| `/checkpoint` | Create checkpoint |
| `/loop stop` | Stop autonomous loop |
| `/circuit status` | Check circuit breaker state |

---

## Architecture

### Core Components

```
friday_ai/
├── agent/              # Agent orchestration and autonomous mode
│   ├── agent.py       # Main agent loop (184 lines)
│   ├── autonomous_loop.py  # Ralph-inspired autonomous dev (976 lines)
│   ├── session_manager.py  # Session persistence (414 lines)
│   ├── events.py      # Event system (75 lines)
│   ├── session.py     # Session management (88 lines)
│   └── persistence.py # Snapshot management (111 lines)
├── tools/             # Tool system (16 built-in tools)
│   ├── builtin/       # Built-in tools
│   ├── mcp/           # MCP integration
│   ├── base.py        # Tool base classes
│   ├── registry.py    # Tool registry
│   └── discovery.py   # Dynamic tool discovery
├── claude_integration/# .claude folder support (2,032 lines)
│   ├── agent_loader.py      # 13 agents
│   ├── skills_manager.py    # 18 skills
│   ├── command_mapper.py    # 18 commands
│   ├── rules_engine.py      # 7 rules
│   ├── workflow_engine.py   # 4 workflows
│   └── context.py           # Context aggregation
├── client/            # LLM client
│   ├── llm_client.py  # OpenAI-compatible client (243 lines)
│   └── response.py    # Response handling
├── config/            # Configuration
│   ├── config.py      # Pydantic config (150 lines)
│   └── loader.py      # Config loading
├── context/           # Context management
│   ├── manager.py     # Message context (175 lines)
│   ├── compaction.py  # Context compression
│   └── loop_detector.py # Loop detection
├── safety/            # Safety features
│   └── approval.py    # Approval policies
├── hooks/             # Hook system
│   └── hook_system.py # Extensibility (118 lines)
├── ui/                # Terminal UI
│   └── tui.py         # Rich console UI (672 lines)
├── streaming/         # Streaming responses
│   └── response.py    # Event streaming (354 lines)
├── monitoring/        # Performance monitoring
│   └── dashboard.py   # Metrics (456 lines)
├── workflow/          # Workflow execution
│   └── executor.py    # Step execution (375 lines)
├── security/          # Security features (NEW v1.0)
│   ├── audit_logger.py    # Tamper-evident audit logging
│   ├── secret_manager.py  # Secure secret handling
│   └── validators.py      # Input validation
├── resilience/        # Fault tolerance (NEW v1.0)
│   ├── retry.py           # Exponential backoff retry
│   └── health_checks.py   # Health check system
├── observability/     # Monitoring (NEW v1.0)
│   └── metrics.py         # Prometheus-compatible metrics
├── database/          # Database layer (NEW v1.0)
│   └── pool.py            # Connection pooling
├── prompts/           # System prompts
│   └── system.py      # Prompt generation (346 lines)
└── main.py            # CLI entry point (1,179 lines)
```

### Design Patterns

1. **Event-Driven Architecture** - Agent emits events for UI updates
2. **Tool Registry** - Dynamic tool registration and lookup
3. **Async/Await** - All I/O operations are async
4. **Context Managers** - Resource management with async context
5. **Circuit Breaker** - Prevents runaway loops in autonomous mode
6. **Rate Limiting** - API call throttling
7. **Retry with Exponential Backoff** - Automatic retry for transient failures (v1.0)
8. **Health Checks** - Kubernetes-style liveness/readiness probes (v1.0)
9. **Audit Logging** - Tamper-evident security logging (v1.0)
10. **Connection Pooling** - Efficient database connection management (v1.0)

---

## Features

### 1. Autonomous Development Mode (v0.3.0)

Ralph-inspired autonomous development with:

- **Response Analysis** - JSON/text parsing, exit signal detection
- **Circuit Breaker** - Three-state logic (CLOSED/HALF_OPEN/OPEN)
- **Rate Limiting** - 100 calls/hour with auto-reset
- **Session Continuity** - 24-hour session persistence
- **Dual-Condition Exit Gate** - Requires completion indicators AND EXIT_SIGNAL

**Files:**
- `.friday/PROMPT.md` - Development instructions
- `.friday/fix_plan.md` - Task checklist
- `.friday/AGENT.md` - Build instructions
- `.friday/status.json` - Real-time status

**Usage:**
```bash
friday
> /autonomous 50
```

### 2. Tool System (16 Tools)

#### File Operations
- `read_file` - Read with line numbers
- `write_file` - Create/overwrite files
- `edit_file` - Surgical text replacement
- `list_dir` - Directory listing
- `glob` - File pattern matching
- `grep` - Content search

#### System & Network
- `shell` - Safe shell execution
- `git` - Full git operations (status, commit, branch, etc.)
- `http_request` - HTTP client (GET, POST, PUT, DELETE, PATCH)
- `http_download` - File downloads

#### Infrastructure
- `docker` - Container management (ps, logs, exec, build, compose)
- `database` - SQL queries (PostgreSQL, MySQL, SQLite)

#### Web & Search
- `web_search` - DuckDuckGo search
- `web_fetch` - URL content fetching

#### Utilities
- `memory` - Persistent key-value storage
- `todos` - Task management

### 3. .claude Integration

#### Agents (13)
Specialized AI sub-agents for specific tasks:
- `architect` - System design decisions
- `build-error-resolver` - Fix build errors
- `code-reviewer` - Code quality review
- `database-reviewer` - Database optimization
- `doc-updater` - Documentation updates
- `e2e-runner` - End-to-end testing
- `go-build-resolver` - Go build fixes
- `go-reviewer` - Go code review
- `planner` - Implementation planning
- `refactor-cleaner` - Dead code cleanup
- `security-reviewer` - Security analysis
- `tdd-guide` - Test-driven development

**Usage:**
```bash
> /plan "Implement user authentication"
> /code-review
> /tdd
```

#### Skills (18)
Domain-specific knowledge patterns:
- `backend-patterns` - API design, database optimization
- `clickhouse-io` - ClickHouse analytics
- `coding-standards` - TypeScript/JavaScript/React best practices
- `continuous-learning` - Pattern extraction
- `eval-harness` - Evaluation framework
- `frontend-patterns` - React, Next.js, state management
- `golang-patterns` - Go idioms and concurrency
- `golang-testing` - Go test patterns
- `iterative-retrieval` - Context retrieval patterns
- `jpa-patterns` - JPA/Hibernate best practices
- `postgres-patterns` - PostgreSQL optimization
- `security-review` - Security checklist
- `springboot-patterns` - Spring Boot architecture
- `springboot-security` - Spring Security

**Usage:**
```bash
> /skills                    # List skills
> /skills backend-patterns   # Activate skill
```

#### Commands (18)
Slash commands from `.claude/commands/`:
- `/plan` - Use planner agent
- `/tdd` - TDD workflow
- `/code-review` - Code review
- `/go-test` - Go tests with coverage
- `/go-build` - Fix Go builds
- `/go-review` - Go code review
- `/test-coverage` - Check coverage
- `/refactor-clean` - Clean dead code
- `/update-docs` - Update documentation
- `/update-codemaps` - Update codemaps
- `/e2e` - E2E testing
- `/eval` - Evaluation framework
- `/evolve` - Skill evolution
- `/learn` - Extract patterns
- `/instinct-export` - Export instincts
- `/instinct-import` - Import instincts
- `/instinct-status` - Show instincts
- `/orchestrate` - Multi-agent orchestration
- `/checkpoint` - Create checkpoint
- `/setup-pm` - Project setup

#### Rules (7)
Coding standards from `.claude/rules/`:
- `coding-style.md` - Immutability, small files, error handling
- `git-workflow.md` - Commit conventions, PR workflow
- `testing.md` - TDD requirements, 80%+ coverage
- `security.md` - Security checklist, secret management
- `performance.md` - Model selection, context management
- `patterns.md` - API responses, custom hooks, repository pattern
- `agents.md` - Agent orchestration guidelines

#### Workflows (4)
Multi-step processes from `.claude/workflows/`:
- `audit` - Code auditing workflow
- `testing` - Testing workflow
- `deployment` - Deployment workflow
- `upgrade` - Project upgrade workflow

### 4. Session Management

Full session lifecycle:
- **Create** - Automatic on start
- **Save** - Explicit `/save` command
- **Resume** - `/resume [session_id]` or `friday --resume`
- **Expire** - 24-hour timeout
- **Checkpoint** - Named save points

**Storage:** `~/.config/friday/sessions/`

### 5. Safety Features

- **Approval Policies** - yolo, auto, auto-edit, on-request, on-failure, never
- **Dangerous Command Detection** - Safe command whitelist
- **Secret Scrubbing** - Automatic secret detection
- **Path Validation** - File operation safety

---

## v1.0 Enterprise Features

### Error Hierarchy
Comprehensive error taxonomy with 14+ specialized error classes:
- **Base:** `FridayError` with error codes, retryable flags, trace IDs
- **Security:** `AuthenticationError`, `AuthorizationError`, `PathTraversalError`
- **Resilience:** `CircuitOpenError`, `RetryExhaustedError`, `RateLimitError`
- **Database:** `DatabaseError` with query context
- **Tools:** `ToolExecutionError`, `ToolTimeoutError`

### Security Package
- **AuditLogger** - Tamper-evident structured JSON logging
- **SecretManager** - Keyring integration, encrypted storage
- **InputValidator** - Path/command/SQL injection prevention

### Resilience Package
- **RetryPolicy** - Exponential backoff with jitter
- **HealthCheckSystem** - Kubernetes-style liveness/readiness probes
- **@with_retry decorator** - Automatic retry for transient failures

### Observability Package
- **MetricsCollector** - Prometheus-compatible metrics
- Counter, Gauge, Histogram, Timer support
- Export to Prometheus and JSON formats

### Database Package
- **ConnectionPool** - Min/max connection management
- **TransactionContext** - Async transaction support
- **Health checks** - Automatic connection validation

---

## Configuration

### Config File (TOML)
```toml
[model]
name = "GLM-4.7"
temperature = 1.0

[approval]
policy = "on-request"

[mcp_servers.sqlite]
command = "mcp-server-sqlite"
args = ["--db-path", "data.db"]
```

### Environment Variables
```bash
export API_KEY="your-api-key"
export BASE_URL="https://api.example.com"
```

### Config Locations
- `~/.config/ai-agent/config.toml`
- `./.ai-agent/config.toml`

---

## Testing

### Test Suite
- **45+ tests** - All passing
- **Coverage:** ~85%
- **Files:** `tests/`

### Running Tests
```bash
# All tests
python -m pytest tests/

# Specific test
python tests/test_autonomous_mode.py

# Claude integration tests
python -m pytest tests/test_claude_integration/
```

---

## Documentation

### User Documentation
| File | Description |
|------|-------------|
| `docs/README.md` | Main documentation index |
| `docs/USER-GUIDE.md` | Getting started guide |
| `docs/FEATURE-GUIDE.md` | Complete feature reference |
| `docs/COMMANDS.md` | CLI commands reference |
| `docs/AUTONOMOUS-MODE.md` | Autonomous development guide |
| `docs/SESSION-MANAGEMENT.md` | Session management guide |
| `docs/INSTALLATION.md` | Installation instructions |
| `docs/DEVELOPER-GUIDE.md` | Contributing guide |
| `docs/BEST-PRACTICES.md` | Python coding standards |
| `docs/TESTING.md` | Testing guide |
| `docs/SECURITY.md` | Security features |
| `docs/TECH-STACK.md` | Architecture overview |
| `docs/WORKFLOWS.md` | Usage patterns |
| `docs/CICD.md` | CI/CD configuration |

### Upgrade Guides
- `docs/UPGRADE-v0.1.0.md` - v0.1.0 migration
- `docs/UPGRADE-v0.2.0.md` - v0.2.0 migration
- `docs/UPGRADE-v0.3.0.md` - v0.3.0 migration

---

## Development Guidelines

### Adding a Tool

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

Register in `friday_ai/agent/session.py`.

### Code Standards

- **Immutability** - Create new objects, never mutate
- **Small Files** - 200-400 lines typical, 800 max
- **Error Handling** - Comprehensive try/catch with logging
- **Type Hints** - All function signatures
- **Async/Await** - All I/O operations

---

## Key Commands Reference

### Session Management
```
/help              Show all commands
/exit, /quit       Exit the agent
/clear             Clear conversation
/save              Save session
/sessions          List saved sessions
/resume [id]       Resume session
/checkpoint        Create checkpoint
/restore [id]      Restore checkpoint
```

### Configuration
```
/config            Show configuration
/model <name>      Change model
/approval <mode>   Change approval policy
/stats             Show statistics
/tools             List tools
/mcp               Show MCP status
```

### Autonomous Mode
```
/autonomous [n]    Start autonomous loop
/loop stop         Stop loop
/loop status       Show loop status
/monitor           Show metrics
/circuit reset     Reset circuit breaker
/circuit status    Show circuit breaker state
```

### .claude Integration
```
/claude            Show integration status
/agents            List agents
/skills            List skills
/skills <name>     Activate skill
/workflow <name>   Run workflow
/plan "task"       Use planner
/tdd               TDD workflow
/code-review       Code review
```

---

## Troubleshooting

### Common Issues

**Loop Won't Start**
- Check `.friday/PROMPT.md` exists
- Verify rate limit not exceeded
- Check circuit breaker: `/circuit status`

**Session Issues**
- Check `~/.config/friday/sessions/`
- Use `/sessions` to list available
- Sessions expire after 24 hours

**Permission Denied**
- Update approval policy: `/approval auto`
- Reset circuit: `/circuit reset`

### Logs
- Autonomous logs: `.friday/logs/`
- Status file: `.friday/status.json`
- Session file: `.friday/.session_id`

---

## Metrics

| Metric | Value |
|--------|-------|
| Python Files | 78 (+5 new packages) |
| Python LOC | 15,000+ |
| Test LOC | 2,894 |
| Documentation LOC | 11,000+ |
| .claude Resources LOC | 15,651 |
| **Total LOC** | **~45,000+** |
| Tools | 16 |
| Agents | 13 |
| Skills | 18 |
| Commands | 18 |
| Rules | 7 |
| Workflows | 4 |
| Error Classes | 20+ |
| Retry Policies | 3 |
| Health Checks | 3 |
| Metrics Types | 4 |
| Tests | 45+ |
| Test Pass Rate | 100% |

---

## Support

- **Issues:** GitHub Issues
- **Documentation:** `docs/`
- **Examples:** `.claude/`, `examples/`

---

*Friday AI Teammate v1.0.0 - Enterprise Grade AI Coding Assistant*

*Built with industry-standard patterns: comprehensive error handling, audit logging, retry policies, health checks, and database connection pooling.*
