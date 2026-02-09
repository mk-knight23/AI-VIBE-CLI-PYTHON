# Changelog

All notable changes to Friday AI Teammate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-02-09

### Added
- **Autonomous Development Loop** - Complete Ralph-inspired autonomous development system
  - AutonomousLoop class with intelligent exit detection
  - ResponseAnalyzer for semantic response understanding
  - CircuitBreaker with three-state logic (CLOSED, HALF_OPEN, OPEN)
  - RateLimiter with 100 calls/hour limit and automatic reset
  - Dual-condition exit gate (completion indicators + EXIT_SIGNAL)
- **Session Management** - Enhanced session persistence and tracking
  - SessionManager class with full CRUD operations
  - Session event tracking (STARTED, PAUSED, RESUMED, STOPPED, ERROR, COMPLETED)
  - Session history with 100-entry limit
  - Session expiration (configurable, default 24 hours)
- **CLI Commands** - Autonomous mode control commands
  - `/autonomous [max_loops]` - Start autonomous development loop
  - `/loop <cmd>` - Control loop (stop, pause, resume, status)
  - `/monitor` - Show loop status and metrics
  - `/circuit <cmd>` - Control circuit breaker (reset, status, open, close)
- **Project Structure** - Friday project folder for autonomous mode
  - `.friday/PROMPT.md` - Main development instructions
  - `.friday/fix_plan.md` - Task checklist
  - `.friday/AGENT.md` - Build/run instructions
  - `.friday/status.json` - Real-time status
  - `.friday/.call_count` - Rate limiting state
  - `.friday/.session_id` - Session continuity
  - `.friday/logs/` - Loop execution logs
- **Documentation**
  - docs/UPGRADE-v0.2.0.md - Comprehensive upgrade guide
  - Updated README.md with autonomous mode
  - Enhanced TUI help text with new commands

### Changed
- Updated version from 0.1.0 to 0.2.0
- Enhanced CLI with autonomous mode integration
- Improved session management architecture

### Fixed
- Test import paths for better project structure

## [0.1.0] - 2025-02-09

### Added
- **Git Tool** - Complete Git operations support (status, log, diff, add, commit, branch, checkout, clone)
- **Database Tool** - Multi-database SQL execution (PostgreSQL, MySQL, SQLite)
- **Docker Tool** - Container and image management (ps, images, logs, exec, build, compose)
- **HTTP Request Tool** - Full-featured HTTP client (GET, POST, PUT, DELETE, PATCH, etc.)
- **HTTP Download Tool** - File downloads with progress tracking
- **Claude Integration** - Full .claude folder support (agents, skills, rules, commands, workflows)
  - Agent loader for .claude/agents/*.md
  - Skills manager for .claude/skills/*/SKILL.md
  - Rules engine for .claude/rules/*.md
  - Command mapper for .claude/commands/*.md
  - Workflow engine for .claude/workflows/*.md
  - Context manager for aggregating resources
  - Auto-discovery of .claude folders
- **Test Suite** - Comprehensive test coverage
  - tests/test_new_tools.py - New tools tests
  - tests/test_claude_integration/ - Claude integration tests
- **Documentation** - Complete documentation set
  - docs/UPGRADE-v0.1.0.md - Upgrade guide
  - docs/FEATURE-GUIDE.md - Feature reference
  - docs/USER-GUIDE.md - User guide
  - docs/DEVELOPER-GUIDE.md - Contributing guide
  - docs/BEST-PRACTICES.md - Coding standards
  - docs/TESTING.md - Testing guide
  - docs/SECURITY.md - Security features
  - docs/TECH-STACK.md - Architecture
  - docs/WORKFLOWS.md - Usage patterns
  - docs/CICD.md - CI/CD config
  - docs/CLAUDE.md - AI context
  - docs/IMPLEMENTATION-PLAN.md - Architecture decisions
- **Dependencies**
  - pyyaml>=6.0.0 - YAML parsing
  - asyncpg>=0.29.0 - PostgreSQL support
  - aiomysql>=0.2.0 - MySQL support
  - python-dotenv>=1.0.0 - Environment loading
  - pytest-asyncio>=0.21.0 - Async testing

### Changed
- Updated version from 0.0.3 to 0.1.0
- Enhanced TUI help text with all new tools
- Updated README with new features
- Fixed test import paths (friday_ai.config.config instead of config.config)
- Organized tools by category in documentation

### Fixed
- Import paths in test files
- PyProject.toml dependencies

## [0.0.3] - Previous Release

### Added
- Initial tool set (read_file, write_file, edit_file, list_dir, glob, grep, shell)
- Web tools (web_search, web_fetch)
- Utilities (memory, todos)
- MCP support
- Rich TUI interface
- Session management
- Security features

## [0.0.2] - Previous Release

### Changed
- Restructured as PyPI package (friday-ai-teammate)

## [0.0.1] - Initial Release

### Added
- Initial Friday AI release
