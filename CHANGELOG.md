# Changelog

All notable changes to Friday AI Teammate will be documented in this file.

## [Unreleased]

## [2.1.1.0] - 2025-02-13

### Added
- Tool registration validation
- Command injection fixes (shell, docker)
- SQL injection prevention
- Path traversal prevention
- Session ID security (32-bit -> 128-bit)
- Security audit logging tool
- Security documentation updates

### Changed
- Refactored autonomous loop response analysis
- Extract command handlers to reduce main.py file size
- Extract circuit breaker control and status display
- Extract response analyzer to separate module

### Fixed
- Syntax error in tools/registry.py
- Duplicate TOML section in pyproject.toml

## [2.1.0.0] - 2025-02-12

### Added
- Simple caching layer with LRU eviction
- Event bus for component decoupling
- Plugin system with version management
- Scheduler for async task execution
- Metrics exporter for Prometheus

### Changed
- Refactored autonomous_loop.py structure
- Extract response_analyzer from autonomous_loop.py
- File size reduction (main.py: 1271 → 900 lines)

### Contributors
- Claude Sonnet 4.5 <noreply@anthropic.com>
