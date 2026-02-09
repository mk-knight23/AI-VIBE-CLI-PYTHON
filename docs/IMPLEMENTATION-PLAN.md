# Friday AI - Implementation Plan
## Architecture Decisions and Roadmap

---

## Table of Contents

1. [Architecture Decisions](#architecture-decisions)
2. [Current Implementation Status](#current-implementation-status)
3. [Future Roadmap](#future-roadmap)
4. [Design Principles](#design-principles)

---

## Architecture Decisions

### Why Python?

**Decision:** Build in Python 3.10+ instead of TypeScript/Node.js

**Rationale:**
- Rich ecosystem for AI/ML tooling
- Excellent async/await support
- Easy distribution via PyPI
- Simpler deployment (no Node runtime required)

### Why OpenAI-Compatible API?

**Decision:** Use OpenAI SDK for LLM integration

**Rationale:**
- Widely supported by providers (OpenAI, Anthropic, GLM, MiniMax)
- Standardized chat completions interface
- Built-in streaming support
- Tool calling standard

### Why Event-Driven Architecture?

**Decision:** Stream events from agent to UI

**Rationale:**
- Real-time UI updates
- Decoupled UI from agent logic
- Support for partial responses
- Better user experience with streaming

### Why Rich for TUI?

**Decision:** Use Rich library for terminal UI

**Rationale:**
- Excellent Python integration
- Automatic terminal detection
- Syntax highlighting built-in
- Panel and layout support

---

## Current Implementation Status

### Core Features (✅ Complete)

| Feature | Status | Notes |
|---------|--------|-------|
| Agent System | ✅ | Async event-driven architecture |
| LLM Client | ✅ | OpenAI-compatible |
| Tool Registry | ✅ | Dynamic tool loading |
| Context Management | ✅ | Token compaction, loop detection |
| Session Persistence | ✅ | Save/resume sessions |
| MCP Support | ✅ | External tool servers |
| Subagents | ✅ | Specialized agents |
| Hook System | ✅ | Before/after hooks |

### Built-in Tools (✅ Complete)

| Tool | Status | Description |
|------|--------|-------------|
| read_file | ✅ | Read files with line numbers |
| write_file | ✅ | Create/overwrite files |
| edit_file | ✅ | Surgical text replacement |
| list_dir | ✅ | Directory listing |
| glob | ✅ | File pattern matching |
| grep | ✅ | Content search |
| shell | ✅ | Command execution |
| web_search | ✅ | DuckDuckGo search |
| web_fetch | ✅ | URL fetching |
| memory | ✅ | Persistent storage |
| todos | ✅ | Task management |

### Safety Features (✅ Complete)

| Feature | Status | Description |
|---------|--------|-------------|
| Approval Policies | ✅ | 6 levels of control |
| Dangerous Command Detection | ✅ | Pattern-based detection |
| Secret Scrubbing | ✅ | Automatic redaction |
| Path Validation | ✅ | Directory restrictions |

---

## Future Roadmap

### Phase 1: Tool Enhancements (Short-term)

- [ ] Git tool for repository operations
- [ ] Docker tool for container management
- [ ] Database tool for SQL queries
- [ ] HTTP tool for API testing

### Phase 2: IDE Integration (Medium-term)

- [ ] VS Code extension
- [ ] Neovim plugin
- [ ] Language Server Protocol support

### Phase 3: Collaboration (Long-term)

- [ ] Team session sharing
- [ ] Centralized configuration
- [ ] Audit logging
- [ ] Role-based permissions

### Phase 4: AI Enhancements (Long-term)

- [ ] Multi-model support (simultaneous)
- [ ] Local model support (Ollama, etc.)
- [ ] Embeddings for codebase search
- [ ] Fine-tuning support

---

## Design Principles

### 1. Safety First

- All dangerous operations require approval
- Path validation prevents directory traversal
- Secret scrubbing protects credentials
- Clear audit trail

### 2. Extensibility

- Plugin architecture via MCP
- Dynamic tool discovery
- Hook system for customization
- Configuration at multiple levels

### 3. User Experience

- Streaming responses
- Rich terminal UI
- Contextual help
- Session management

### 4. Simplicity

- Minimal configuration required
- Sensible defaults
- Clear error messages
- Progressive disclosure

---

## Technical Debt

### Known Issues

1. **Context Compaction:** Could be smarter about what to remove
2. **Token Counting:** Estimation could be more accurate
3. **Error Recovery:** Could be more robust

### Areas for Improvement

1. **Test Coverage:** Increase from 80% to 90%+
2. **Documentation:** Add more examples
3. **Performance:** Optimize large file handling
4. **Accessibility:** Improve screen reader support

---

*Implementation Plan v1.0 - Friday AI Teammate*
