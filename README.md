# 🚀 AI-VIBE-CLI-PYTHON (Collective Production Edition)

## 💎 Overview
Fully production-grade implementation of AI-VIBE-CLI-PYTHON, refactored by the **69-Agent Opencode Collective**.

## 🛡️ Trust & Compliance
- **CI/CD**: Automated GitHub Actions with Gitleaks security scans.
- **Security**: Standardized [SECURITY.md](SECURITY.md) protocol.
- **Design**: Opencode Premium Design Tokens integrated.

## 🏁 48-Hour Roadmap
1. Initialize infrastructure via `.github/workflows`.
2. Set your secrets in GitHub Environment settings.
3. Deploy to production via Vercel/Docker.

<p align="center">
  <img src="https://img.shields.io/badge/AI--VIBE-CLI--PYTHON-blue?style=for-the-badge&logo=python&logoColor=white" alt="AI Vibe Project">
  <br>
  <b>Empowering developers with enterprise-grade autonomous AI coding assistance directly in the terminal.</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/friday-ai-teammate/"><img src="https://badge.fury.io/py/friday-ai-teammate.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

---

## 🗺️ Quick Navigation

- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📚 Built-in Tools](#-built-in-tools)
- [🧠 Claude Integration](#-claude-integration)
- [🔒 Security Features](#-security-features)
- [🚀 Autonomous Mode](#-autonomous-mode)
- [📖 Documentation](#-documentation)
- [🛠️ Development](#%EF%B8%8F-development)
- [📊 Version History](#-version-history)

---

## 🛠️ Engineered With

<p align="left">
  <a href="https://python.org"><img src="https://skillicons.dev/icons?i=python" alt="Python"></a>
  <a href="https://openai.com"><img src="https://skillicons.dev/icons?i=openai" alt="OpenAI"></a>
  <a href="https://docker.com"><img src="https://skillicons.dev/icons?i=docker" alt="Docker"></a>
  <a href="https://postgres.org"><img src="https://skillicons.dev/icons?i=postgres" alt="PostgreSQL"></a>
  <a href="https://git-scm.com"><img src="https://skillicons.dev/icons?i=git" alt="Git"></a>
</p>

---

## ✨ Features

**Friday** is a powerful AI assistant designed to help you with coding tasks, file management, database operations, container management, and information retrieval directly from your terminal.

- 🛠️ **16+ Built-in Tools** - File operations, shell, git, docker, database, HTTP requests, web search
- 🧠 **Claude Integration** - Load agents, skills, rules, workflows, and commands from `.claude/` folders
- 🔒 **Security First** - Secret scrubbing, approval policies, path validation, dangerous command detection
- 💾 **Session Management** - Save, resume, and checkpoint sessions
- 🔌 **MCP Support** - Connect to external tool servers via Model Context Protocol
- 📝 **Rich TUI** - Beautiful terminal UI with syntax highlighting and progress tracking
- 🚀 **Autonomous Mode** - Ralph-inspired autonomous development loop with intelligent exit detection
- 📊 **Enterprise Ready** - API server, monitoring, observability, circuit breakers, retry logic

---

## 🚀 Quick Start

### Installation

```bash
pip install friday-ai-teammate
```

### Configuration

Set your API credentials:

```bash
export API_KEY=your_api_key
export BASE_URL=https://api.provider.com/v1
```

Or create a `.env` file:
```env
API_KEY=your_api_key
BASE_URL=https://api.provider.com/v1
```

### Usage

**Interactive mode:**
```bash
friday
```

**Single prompt:**
```bash
friday "Help me refactor this code"
```

**With working directory:**
```bash
friday -c /path/to/project "Review this codebase"
```

---

## 📚 Built-in Tools

### File System
| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with line numbers |
| `write_file` | Create or overwrite files |
| `edit_file` | Surgical text replacement |
| `list_dir` | List directory contents |
| `glob` | Find files by pattern |
| `grep` | Search file contents |

### System & Infrastructure
| Tool | Description |
|------|-------------|
| `shell` | Execute shell commands safely |
| `git` | Git operations (status, log, diff, add, commit, branch) |
| `docker` | Docker container management (ps, logs, exec, build, compose) |
| `database` | SQL queries (PostgreSQL, MySQL, SQLite) |

### Network & Web
| Tool | Description |
|------|-------------|
| `http_request` | HTTP requests (GET, POST, PUT, DELETE, PATCH) |
| `http_download` | Download files from URLs |
| `web_search` | DuckDuckGo search |
| `web_fetch` | Fetch URL content |

### Utilities
| Tool | Description |
|------|-------------|
| `memory` | Persistent key-value storage |
| `todos` | Task list management |

---

## 🧠 Claude Integration

Friday automatically discovers and integrates with `.claude/` folders:

```
.claude/
├── agents/         # Sub-agent definitions (13 agents)
├── skills/         # Reusable patterns (18 skills)
├── rules/          # Coding standards (7 rules)
├── commands/       # Slash commands (18 commands)
└── workflows/      # Multi-step workflows (4 workflows)
```

### Available Commands
- `/agents` - List available agents
- `/skills` - List and activate skills
- `/plan "task"` - Use planner agent
- `/tdd` - Test-driven development
- `/code-review` - Code review
- `/workflow <name>` - Run workflow

---

## 🔒 Security Features

- **Secret Scrubbing** - Automatically masks API keys, passwords in tool outputs
- **Approval Policies** - Configure permission behavior (`/approval`)
- **Path Validation** - Operations restricted to allowed directories
- **Dangerous Command Detection** - Flags risky operations (rm -rf, sudo, etc.)
- **Audit Logging** - Tamper-evident structured JSON logging
- **Input Validation** - Protection against path traversal, command injection, SQL injection

---

## 🚀 Autonomous Mode

Ralph-inspired autonomous development with:

- **Response Analysis** - JSON/text parsing, exit signal detection
- **Circuit Breaker** - Three-state logic (CLOSED/HALF_OPEN/OPEN)
- **Rate Limiting** - 100 calls/hour with auto-reset
- **Session Continuity** - 24-hour session persistence
- **Dual-Condition Exit** - Requires completion indicators + EXIT_SIGNAL

```bash
friday
> /autonomous 50  # Run for 50 iterations
```

---

## 📖 Documentation

- **[USER-GUIDE.md](docs/USER-GUIDE.md)** - Complete user documentation
- **[DEVELOPER-GUIDE.md](docs/DEVELOPER-GUIDE.md)** - Contributing and development
- **[OPERATIONS-GUIDE.md](docs/OPERATIONS-GUIDE.md)** - Installation, CI/CD, upgrades
- **[PROJECT-DOCS.md](docs/PROJECT-DOCS.md)** - Architecture, audits, implementation

---

## 🛠️ Development

### From Source

```bash
git clone https://github.com/mk-knight23/AI-VIBE-CLI-PYTHON.git
cd AI-VIBE-CLI-PYTHON
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_security.py -v
```

---

## 📊 Version History

See [CHANGELOG.md](docs/CHANGELOG.md) for details.

- **v1.0.0** - Enterprise features (API, monitoring, security, resilience)
- **v0.3.0** - Ralph-inspired autonomous development
- **v0.2.0** - Session management
- **v0.1.0** - Initial release with tool system

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <i>Friday AI Teammate v1.0.0 - Enterprise Grade AI Coding Assistant</i>
</p>


## 🎯 Problem Solved

This repository provides a streamlined approach to modern development needs, enabling developers to build robust applications with minimal complexity and maximum efficiency.

## 🏗️ Architecture

```
```

## 🌐 Deployment

### Live URLs

| Platform | URL |
|----------|-----|
| Vercel | [Deployed Link] |
| GitHub Pages | [Deployed Link] |

## Security

This project follows security best practices:
- No hardcoded credentials
- Dependency scanning enabled
- Security headers configured
- Regular security audits performed
