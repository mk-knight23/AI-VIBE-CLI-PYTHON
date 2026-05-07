<div align="center">

# 🐍 AI-VIBE-CLI-PYTHON

### **Friday — Enterprise Autonomous AI Coding Assistant**
*Python · Click · Rich · Pydantic · MCP · Agent Swarms · Kubernetes*

[![PyPI](https://img.shields.io/pypi/v/friday-ai-teammate?style=for-the-badge&color=blue)](https://pypi.org/project/friday-ai-teammate/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/mk-knight23/AI-VIBE-CLI-PYTHON/ci.yml?style=for-the-badge&label=CI)](https://github.com/mk-knight23/AI-VIBE-CLI-PYTHON/actions)

**[📦 PyPI](https://pypi.org/project/friday-ai-teammate/)** · **[📖 Docs](#documentation)** · **[🐛 Issues](https://github.com/mk-knight23/AI-VIBE-CLI-PYTHON/issues)**

</div>

---

## 🎯 What Is Friday?

**Friday** is your enterprise-grade AI teammate in the terminal. It's a fully autonomous AI coding assistant CLI with **18+ built-in tools**, **agent swarm orchestration**, **MCP (Model Context Protocol) integration**, and a production-ready API server — all from a single `pip install`.

Think of Friday as having a senior engineer available 24/7 in your terminal, capable of reading your codebase, writing tests, fixing bugs, running Docker, querying databases, and shipping features — autonomously.

---

## ⚡ One-Line Install

```bash
pip install friday-ai-teammate
```

Then configure your preferred AI:

```bash
friday config set provider anthropic
friday config set api-key sk-ant-...
friday start  # Begin interactive session
```

---

## 🛠️ 18+ Built-in Tools

### 📁 File System
| Tool | Description |
|------|-------------|
| `read_file` | Read any file with syntax highlighting |
| `write_file` | Create/overwrite files atomically |
| `edit_file` | Surgical edits with diff preview |
| `list_directory` | Recursive directory listing with ignore patterns |
| `find_files` | Glob + regex file search |
| `delete_file` | Safe deletion with confirmation |

### 💻 Shell & Code Execution
| Tool | Description |
|------|-------------|
| `bash` | Execute bash commands with timeout + approval |
| `python_repl` | Interactive Python REPL with state |
| `node_repl` | Node.js execution for JS/TS |

### 🔧 Git Integration
| Tool | Description |
|------|-------------|
| `git_status` | Full repo status with diff preview |
| `git_commit` | Commit with auto-generated message |
| `git_diff` | Show detailed file diffs |
| `git_log` | Browse commit history |
| `git_branch` | Create/switch/list branches |

### 🐳 Docker & Kubernetes
| Tool | Description |
|------|-------------|
| `docker_build` | Build images with progress tracking |
| `docker_run` | Run containers with port mapping |
| `kubectl_apply` | Apply K8s manifests |
| `kubectl_logs` | Stream pod logs |

### 🌐 HTTP & Web
| Tool | Description |
|------|-------------|
| `http_request` | Full HTTP client (GET/POST/PUT/DELETE) |
| `web_search` | DuckDuckGo search with result extraction |
| `fetch_url` | Fetch and parse web pages |

### 🗄️ Database
| Tool | Description |
|------|-------------|
| `db_query` | Execute SQL queries (PostgreSQL/SQLite/MySQL) |
| `db_schema` | Inspect table schemas |

---

## 🧠 Multi-Provider Support

```bash
# Claude (recommended for complex tasks)
friday config set provider anthropic
friday config set api-key sk-ant-...

# OpenAI
friday config set provider openai
friday config set api-key sk-...

# Groq (ultra-fast for quick tasks)
friday config set provider groq
friday config set api-key gsk_...

# Local Ollama (no API key needed)
friday config set provider ollama
friday config set base-url http://localhost:11434
friday config set model llama3.2
```

---

## 🤖 Agent Modes

### Interactive Mode (Default)
```bash
friday start
# Opens REPL with full tool access
```

### Autonomous Mode
```bash
friday run "Add comprehensive unit tests to the auth module"
friday run "Refactor the database layer to use connection pooling"
friday run "Fix the N+1 query issue in getUserWithPosts()"
```

### Task File Mode
```bash
# .friday/tasks.yaml
tasks:
  - name: "Setup CI/CD"
    description: "Create GitHub Actions workflow for testing and deployment"
    priority: high

friday run --from-file .friday/tasks.yaml
```

### Agent Swarm Mode
```bash
friday swarm --agents 3 "Build a complete REST API for a todo app with auth, CRUD, and tests"
# Spawns 3 sub-agents working in parallel on different parts
```

---

## 🔌 MCP Integration

Friday supports the **Model Context Protocol** — connect any MCP server to extend Friday's capabilities:

```bash
# Add an MCP server
friday mcp add github https://github.com/modelcontextprotocol/servers
friday mcp add postgres postgresql://localhost/mydb
friday mcp add filesystem /path/to/project

# List connected servers
friday mcp list

# Friday now has access to all MCP tools automatically
friday start
```

---

## 🏗️ Architecture

```
friday/
├── cli/
│   ├── main.py              # Click CLI entry point
│   ├── commands/
│   │   ├── start.py         # Interactive REPL
│   │   ├── run.py           # Autonomous task runner
│   │   ├── swarm.py         # Multi-agent orchestrator
│   │   └── config.py        # Configuration management
├── core/
│   ├── agent.py             # Base agent loop
│   ├── orchestrator.py      # Multi-agent coordinator
│   ├── memory.py            # Conversation + context memory
│   ├── approval.py          # Human-in-the-loop approval system
│   └── security.py          # Secret scrubbing, path validation
├── tools/
│   ├── filesystem.py        # File read/write/edit/search
│   ├── shell.py             # Bash execution with safety
│   ├── git.py               # Git operations
│   ├── docker.py            # Docker/Kubernetes management
│   ├── http.py              # HTTP client + web search
│   ├── database.py          # Multi-dialect SQL client
│   └── mcp_bridge.py        # MCP server connector
├── providers/
│   ├── anthropic.py         # Claude API client
│   ├── openai.py            # OpenAI API client
│   ├── groq.py              # Groq API client
│   └── ollama.py            # Ollama local client
└── ui/
    ├── tui.py               # Rich TUI interface
    ├── spinner.py           # Progress indicators
    └── diff.py              # Syntax-highlighted diffs
```

---

## 🔒 Security Architecture

Friday takes security seriously for agentic execution:

```python
# Security layers applied to every tool execution:
# 1. Secret scrubbing — no API keys in logs
# 2. Path validation — no traversal outside project
# 3. Dangerous command detection — sudo, rm -rf, etc.
# 4. Approval policies — configurable per command type
# 5. Execution sandboxing — optional Docker isolation
# 6. Audit log — every tool call logged to ~/.friday/audit.log
```

Configure approval policy:

```bash
friday config set approval.policy strict   # All commands need approval
friday config set approval.policy balanced  # Only destructive commands (default)
friday config set approval.policy yolo      # Fully autonomous (use carefully)
```

---

## 📊 Enterprise Features

### API Server Mode
```bash
friday server start --port 8080
# Exposes REST API for CI/CD integration
```

### Monitoring & Observability
```bash
friday metrics                 # Token usage, cost, tool calls
friday audit --last 50         # Audit log of recent actions
friday session list            # All saved sessions
friday session resume <id>     # Resume a previous session
```

### CI/CD Integration
```yaml
# .github/workflows/friday-review.yml
- name: Friday Code Review
  run: |
    pip install friday-ai-teammate
    friday run "Review the changed files and identify potential issues" \
      --diff $(git diff HEAD~1) \
      --output .friday/review.md
```

---

## 🚀 Quick Start Examples

```bash
# Understand a codebase
friday run "Explain the architecture of this project in detail"

# Fix a bug
friday run "The login endpoint returns 500 when email contains '+', fix it"

# Write tests
friday run "Write comprehensive unit and integration tests for src/api/users.py"

# Refactor
friday run "Refactor the UserService class to use dependency injection"

# Deploy
friday run "Build and push Docker image to registry, then update K8s deployment"
```

---

## 📖 Documentation

| Section | Description |
|---------|-------------|
| [Installation Guide](docs/installation.md) | Detailed setup instructions |
| [Configuration Reference](docs/configuration.md) | All config options |
| [Tools Reference](docs/tools.md) | Complete tool documentation |
| [Agent Modes](docs/agent-modes.md) | Interactive, Autonomous, Swarm |
| [MCP Integration](docs/mcp.md) | Connecting MCP servers |
| [Security Guide](docs/security.md) | Approval policies, sandboxing |
| [API Reference](docs/api.md) | REST API for server mode |
| [Contributing](CONTRIBUTING.md) | Development setup |

---

## 📦 Version History

| Version | Date | Highlights |
|---------|------|------------|
| **v3.0.0** | 2026-05 | Multi-provider routing, agent swarms v2, K8s tools |
| **v2.1.0** | 2025-10 | MCP integration, approval policies, audit log |
| **v2.0.0** | 2025-07 | Rich TUI, streaming output, plugin system |
| **v1.0.0** | 2025-02 | Initial release, 12 core tools |

---

<div align="center">

**Built with 🐍 by [Kazi Musharraf](https://mkazi.live)**

[![GitHub](https://img.shields.io/badge/GitHub-mk--knight23-181717?style=flat&logo=github)](https://github.com/mk-knight23)
[![PyPI](https://img.shields.io/badge/PyPI-friday--ai--teammate-3775A9?style=flat&logo=pypi)](https://pypi.org/project/friday-ai-teammate/)
[![Twitter](https://img.shields.io/badge/Twitter-@mk__knight__23-1DA1F2?style=flat&logo=twitter)](https://twitter.com/mk_knight_23)

*Part of the [AI-VIBE Ecosystem](https://github.com/mk-knight23/AI-VIBE-ECOSYSTEM) · Built in India 🇮🇳*

</div>
