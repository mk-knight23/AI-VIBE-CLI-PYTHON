# Changelog

All notable changes to Friday AI Teammate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-09

### Added
- **Enterprise Packages:**
  - API server with FastAPI and SSE streaming
  - Security package (audit logging, secret manager, input validation)
  - Resilience package (retry with exponential backoff, health checks)
  - Observability package (Prometheus metrics)
  - Database package (connection pooling, Redis backend)
  - MCP server implementation
  - Monitoring dashboard
  - Rate limiting middleware
  - Workflow executor

- **Error Handling:**
  - Comprehensive error hierarchy with 20+ specialized error classes
  - Machine-readable error codes
  - Retryable flags for automatic retry decisions
  - Trace ID support for distributed tracing
  - Structured context in errors

- **Autonomous Mode (Ralph-inspired):**
  - JSON response parsing with RALPH_STATUS block support
  - Two-stage error filtering (eliminates false positives)
  - Permission denial detection (Issue #101)
  - Session continuity across iterations with 24-hour timeout
  - Real-time status.json updates
  - Circuit breaker with 3 states (CLOSED/HALF_OPEN/OPEN)
  - Output decline detection (70% threshold)
  - Enhanced iteration logging with metadata

- **HTTP Tools:**
  - Retry logic with exponential backoff for GET/HEAD/OPTIONS
  - Transient failure handling (Timeout, Connect, Network errors)

- **Configuration:**
  - Added redis_url property for Redis support

### Changed
- Version bump from 0.3.0 to 1.0.0
- Development status changed from Alpha to Production/Stable
- Config file moved from `~/.friday/config.toml` to `~/.config/ai-agent/config.toml`
- Session storage moved to `~/.config/friday/sessions/`
- Removed `.env` file with exposed API key (replaced with placeholder)

### Security
- Removed 3 exposed API keys from git history using BFG Repo-Cleaner
- Updated `.env.example` with placeholder values
- Added comprehensive input validation
- Added tamper-evident audit logging

### Documentation
- Consolidated 23 documentation files into 5 organized files:
  - README.md - Overview & quick start
  - USER-GUIDE.md - Complete user documentation
  - DEVELOPER-GUIDE.md - Developer documentation
  - OPERATIONS-GUIDE.md - Operations & maintenance
  - PROJECT-DOCS.md - Architecture & audits

### Removed
- Virtual environment `.venv/` (198MB) - should never be in repo
- `ralph-claude-code/` (2.1MB) - separate repository
- `database.db` - runtime database file
- `.DS_Store` files - macOS metadata
- `__pycache__/` directories - Python cache
- `.pytest_cache/` - test cache
- `friday_ai_teammate.egg-info/` - build artifacts
- `.friday/logs/` - old runtime logs
- Malformed directory `"file_path": "/` - command error artifact

## [0.3.0] - 2026-01-15

### Added
- Ralph-inspired autonomous development loop
- Session management (save, resume, checkpoint)
- Circuit breaker pattern with 3 states
- Rate limiting (100 API calls per hour)
- Dual-condition exit detection
- Response analysis with JSON and text parsing
- Session continuity across iterations (24-hour timeout)
- Real-time status file updates (`.friday/status.json`)
- Permission denial detection
- Output decline detection

### Changed
- Enhanced autonomous_loop.py with Ralph patterns
- Improved session_manager.py with persistence
- Updated main.py with autonomous mode commands

### Documentation
- Added AUTONOMOUS-MODE.md
- Added SESSION-MANAGEMENT.md
- Added UPGRADE-v0.3.0.md

## [0.2.0] - 2025-12-20

### Added
- Session persistence with save/restore
- Checkpoint system for named save points
- Enhanced Claude integration from `.claude/` folders
- Agent loading (13 specialized agents)
- Skills activation (18 domain patterns)
- Rules auto-loading (7 coding standards)
- Commands loading (18 slash commands)
- Workflows (4 multi-step processes)
- Session expiration (24-hour timeout)
- Session list command

### Changed
- Enhanced context manager for session support
- Updated main.py with session commands
- Improved TUI for session management

### Documentation
- Updated FEATURE-GUIDE.md with Claude integration
- Added SESSION-MANAGEMENT documentation

## [0.1.0] - 2025-11-15

### Added
- Initial release of Friday AI Teammate
- 16 built-in tools (file, system, web, utilities)
- MCP (Model Context Protocol) support
- Rich terminal UI with syntax highlighting
- Secret scrubbing for security
- Approval policies (yolo, auto, on-request, never)
- Dangerous command detection
- Path validation
- Hook system for extensibility
- Tool registry and discovery
- OpenAI-compatible LLM client
- Async streaming responses
- Context window management
- Event-driven architecture

### Documentation
- Initial documentation set
- Installation guide
- User guide
- Developer guide
- API reference

## [Unreleased]

### Planned
- Multi-agent orchestration
- Advanced workflow engine
- Plugin system
- Web UI dashboard
- Team collaboration features

---

**Note:** For detailed upgrade instructions, see [OPERATIONS-GUIDE.md](OPERATIONS-GUIDE.md#upgrading).
