# Friday AI - Project Documentation

Complete project documentation including architecture, audits, and implementation details.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Design Decisions](#design-decisions)
3. [Component Documentation](#component-documentation)
4. [Project Audits](#project-audits)
5. [Implementation History](#implementation-history)
6. [Technical Specifications](#technical-specifications)
7. [Roadmap](#roadmap)

---

## Architecture Overview

### System Architecture

Friday AI Teammate is an event-driven AI assistant with the following layers:

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                            │
│  (friday_ai/main.py - Argument parsing, command routing)    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      Agent Layer                            │
│  (friday_ai/agent/ - Orchestration, event emission)        │
│  ┌──────────────┬──────────────┬──────────────────────┐    │
│  │ Agent Loop   │ Autonomous   │ Session Manager      │    │
│  │              │ Loop         │                      │    │
│  └──────────────┴──────────────┴──────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     Tool Layer                              │
│  (friday_ai/tools/ - Tool execution, MCP integration)       │
│  ┌──────────────┬──────────────┬──────────────────────┐    │
│  │ Built-in     │ MCP Server   │ Discovery & Registry │    │
│  │ Tools        │             │                      │    │
│  └──────────────┴──────────────┴──────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Context & Safety Layer                     │
│  (context/, safety/, security/ - State management)          │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Client Layer                             │
│  (friday_ai/client/ - LLM API integration)                  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Event-Driven Architecture** - Agent emits events for UI updates
2. **Async/Await** - All I/O operations are asynchronous
3. **Tool Registry** - Dynamic tool registration and discovery
4. **Context Managers** - Proper resource management
5. **Circuit Breaker** - Prevents runaway loops
6. **Retry with Backoff** - Resilient operations

---

## Design Decisions

### Why Event-Driven Architecture?

**Decision:** Use event-driven architecture for agent operations

**Rationale:**
- Loose coupling between agent and UI
- Easy to extend with new event types
- Supports streaming responses naturally
- Clean separation of concerns

**Implementation:** `friday_ai/agent/events.py`

### Why MCP Integration?

**Decision:** Support Model Context Protocol (MCP)

**Rationale:**
- Industry standard for tool integration
- Extensible without code changes
- Community tool ecosystem
- Future-proof architecture

**Implementation:** `friday_ai/tools/mcp/`

### Why Circuit Breaker?

**Decision:** Implement circuit breaker pattern for autonomous mode

**Rationale:**
- Prevents runaway loops (common in autonomous systems)
- Three-state logic (CLOSED/HALF_OPEN/OPEN)
- Configurable thresholds
- Automatic recovery

**Implementation:** `friday_ai/agent/autonomous_loop.py`

### Why Comprehensive Error Hierarchy?

**Decision:** Create 20+ specialized error classes

**Rationale:**
- Machine-readable error codes
- Retryable flags for automation
- Structured context for debugging
- Trace ID for distributed tracing

**Implementation:** `friday_ai/utils/errors.py`

---

## Component Documentation

### Agent System

**Location:** `friday_ai/agent/`

**Components:**
- `agent.py` - Main agent loop (184 lines)
- `autonomous_loop.py` - Ralph-inspired autonomous mode (976 lines)
- `session_manager.py` - Session persistence (414 lines)
- `events.py` - Event system (75 lines)
- `session.py` - Session management (88 lines)
- `persistence.py` - Snapshot management (111 lines)

**Responsibilities:**
- Orchestrate tool execution
- Manage conversation context
- Emit events for UI updates
- Handle autonomous development loop
- Persist and restore sessions

### Tool System

**Location:** `friday_ai/tools/`

**Components:**
- `base.py` - Tool base classes
- `registry.py` - Tool registration
- `discovery.py` - Dynamic discovery
- `builtin/` - 16 built-in tools
- `mcp/` - MCP integration

**Built-in Tools:**
- **File Operations:** read_file, write_file, edit_file, list_dir, glob, grep
- **System:** shell, git, docker
- **Network:** http_request, http_download, web_search, web_fetch
- **Infrastructure:** database
- **Utilities:** memory, todos

### Client Layer

**Location:** `friday_ai/client/`

**Components:**
- `llm_client.py` - OpenAI-compatible client (243 lines)
- `response.py` - Response parsing

**Features:**
- Async streaming responses
- Error handling with retry
- Support for multiple providers
- Token usage tracking

### Enterprise Packages (v1.0)

**API Package:** `friday_ai/api/`
- FastAPI REST server
- SSE streaming
- Session management endpoints
- Health checks

**Security Package:** `friday_ai/security/`
- Audit logging (tamper-evident)
- Secret manager (keyring integration)
- Input validation (path traversal, injection prevention)

**Resilience Package:** `friday_ai/resilience/`
- Exponential backoff retry
- Health checks (liveness/readiness)
- Circuit breaker integration

**Observability Package:** `friday_ai/observability/`
- Prometheus metrics
- Counter, Gauge, Histogram, Timer
- JSON export support

---

## Project Audits

### v2 Enterprise++ Audit (Current)

**Date:** February 2026
**Status:** Production Ready
**Lines of Code:** ~45,000
**Test Coverage:** 85%

**Key Findings:**
✅ Comprehensive error handling implemented
✅ Security package with audit logging
✅ Resilience patterns (retry, circuit breaker)
✅ Observability with Prometheus metrics
✅ Database connection pooling
✅ API server with SSE streaming

**Recommendations Implemented:**
1. ✅ Added error hierarchy with retryable flags
2. ✅ Implemented tamper-evident audit logging
3. ✅ Added exponential backoff retry
4. ✅ Implemented health check system
5. ✅ Added Prometheus metrics export

**See:** [docs/PROJECT_AUDIT_v2_ENTERPRISE_PLUSPLUS.md](docs/PROJECT_AUDIT_v2_ENTERPRISE_PLUSPLUS.md)

### v1 Audit

**Date:** January 2026
**Status:** Completed
**Lines of Code:** ~15,000

**Key Findings:**
- Solid foundation with agent architecture
- Good tool system with 16 tools
- Session management working
- Needed: Enterprise features

**Actions Taken:**
- ✅ Added API package
- ✅ Added security package
- ✅ Added resilience package
- ✅ Added observability package

---

## Implementation History

### Phase 1: Foundation (v0.1.0)

**Timeline:** November 2025
**Duration:** 4 weeks

**Deliverables:**
- ✅ Agent loop with tool orchestration
- ✅ 16 built-in tools
- ✅ MCP integration
- ✅ Rich TUI
- ✅ Security features (secret scrubbing, approval)
- ✅ Hook system

**Code:** ~5,000 LOC

### Phase 2: Integration (v0.2.0)

**Timeline:** December 2025
**Duration:** 3 weeks

**Deliverables:**
- ✅ Session management (save, resume, checkpoint)
- ✅ Enhanced Claude integration
- ✅ Agent/skill/workflow loading
- ✅ Context window management

**Code:** ~8,000 LOC (total)

### Phase 3: Autonomous Mode (v0.3.0)

**Timeline:** January 2026
**Duration:** 4 weeks

**Deliverables:**
- ✅ Ralph-inspired autonomous loop
- ✅ Response analysis with JSON parsing
- ✅ Circuit breaker (3-state)
- ✅ Rate limiting (100/hour)
- ✅ Session continuity (24-hour timeout)

**Code:** ~12,000 LOC (total)

### Phase 4: Enterprise Features (v1.0.0)

**Timeline:** February 2026
**Duration:** 5 weeks

**Deliverables:**
- ✅ Comprehensive error hierarchy (20+ classes)
- ✅ Security package (audit, secrets, validation)
- ✅ Resilience package (retry, health checks)
- ✅ Observability package (Prometheus metrics)
- ✅ API package (FastAPI, SSE streaming)
- ✅ Database package (connection pooling)
- ✅ MCP server implementation
- ✅ Monitoring dashboard
- ✅ Rate limiting middleware

**Code:** ~45,000 LOC (total)

---

## Technical Specifications

### Error Hierarchy

**Base Class:** `FridayError`

**Categories:**
1. **Configuration:** ConfigError, ValidationError
2. **Tools:** ToolExecutionError, ToolNotFoundError, ToolTimeoutError
3. **Security:** AuthenticationError, AuthorizationError, PathTraversalError, SQLInjectionError
4. **Resilience:** CircuitOpenError, RetryExhaustedError, RateLimitError, TimeoutError
5. **Database:** DatabaseError
6. **Session:** SessionError, SessionNotFoundError, SessionExpiredError

**Example:**
```python
raise ToolExecutionError(
    message="Failed to execute shell command",
    code="TOOL_EXECUTION_FAILED",
    details={"tool": "shell", "command": "ls", "exit_code": 1},
    retryable=False
)
```

### Circuit Breaker States

**CLOSED:** Normal operation
- Requests pass through
- Tracking failures
- Transition to OPEN on threshold exceeded

**HALF_OPEN:** Testing recovery
- Allow limited requests
- Transition to CLOSED on success
- Transition to OPEN on failure

**OPEN:** Circuit is open
- Block all requests
- Automatic transition to HALF_OPEN after timeout
- Manual reset with `/circuit reset`

### Response Analysis

**JSON Format:**
```json
{
  "exit_signal": true,
  "status": "complete",
  "summary": "Task completed successfully",
  "metadata": {
    "files_modified": ["main.py"],
    "has_errors": false,
    "completion_status": "done"
  }
}
```

**Text Format:**
```
[EXIT_SIGNAL: true]
Project is complete.
All tests passing.
```

---

## Roadmap

### Upcoming Features (v1.1.0)

**Planned:** Q2 2026

- [ ] Multi-agent orchestration
- [ ] Advanced workflow engine
- [ ] Plugin system
- [ ] Web UI dashboard
- [ ] Team collaboration features
- [ ] Code generation templates

### Future Enhancements (v2.0.0)

**Planned:** Q3 2026

- [ ] Distributed agent execution
- [ ] Advanced caching layer
- [ ] Custom tool marketplace
- [ ] Integration with more LLM providers
- [ ] Enterprise SSO integration
- [ ] Advanced analytics

### Long-term Vision

**Goal:** Make Friday AI the most capable and user-friendly AI coding assistant.

**Focus Areas:**
1. **Autonomous Development** - More intelligent, less oversight
2. **Team Collaboration** - Shared sessions, code review integration
3. **Extensibility** - Plugins, custom tools, workflows
4. **Performance** - Faster responses, better caching
5. **Enterprise** - SSO, audit logs, compliance

---

## References

### Documentation

- [README.md](README.md) - Project overview
- [USER-GUIDE.md](USER-GUIDE.md) - User documentation
- [DEVELOPER-GUIDE.md](DEVELOPER-GUIDE.md) - Developer documentation
- [OPERATIONS-GUIDE.md](OPERATIONS-GUIDE.md) - Operations documentation

### External Resources

- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Related Projects

- [Ralph for Claude Code](https://github.com/your-org/ralph-claude-code) - Inspiration for autonomous mode
- [MCP Servers](https://github.com/modelcontextprotocol) - Community MCP servers

---

*Friday AI Teammate v1.0.0 - Project Documentation*

**Last Updated:** February 2026
**Maintainer:** mk-knight23
