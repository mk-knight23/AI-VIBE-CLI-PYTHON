# Friday AI Teammate

[![PyPI version](https://badge.fury.io/py/friday-ai-teammate.svg)](https://pypi.org/project/friday-ai-teammate/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Friday is a powerful AI assistant designed to help you with coding tasks, file management, database operations, container management, and information retrieval directly from your terminal.

## Features

- 🛠️ **15+ Built-in Tools**: File operations, shell commands, git, docker, database, HTTP requests, web search
- 🧠 **Claude Integration**: Load agents, skills, rules, workflows, and commands from `.claude/` folders
- 🔒 **Security First**: Secret scrubbing, approval policies, path validation, dangerous command detection
- 💾 **Session Management**: Save, resume, and checkpoint sessions
- 🔌 **MCP Support**: Connect to external tool servers via Model Context Protocol
- 📝 **Rich TUI**: Beautiful terminal UI with syntax highlighting and progress tracking

## Installation

```bash
pip install friday-ai-teammate
```

## Quick Start

### 1. Configuration
Set up your API key:
```bash
export API_KEY=your_sk_...
export BASE_URL=https://api.minimax.io/v1  # or your preferred provider
```

Or create a `.env` file in your working directory:
```env
API_KEY=your_sk_...
BASE_URL=https://api.minimax.io/v1
```

### 2. Usage

**Interactive Mode** - Launch the interactive shell:
```bash
friday
```

**Single Prompt** - Run a specific task:
```bash
friday "Scan the current directory for security risks"
```

**Options**:
- `-c, --cwd DIRECTORY`: Set the working directory for the agent
- `--help`: Show available options

## Built-in Tools

Friday comes equipped with 15+ tools organized by category:

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
| `git` | Git operations (status, log, diff, add, commit, branch, clone) |
| `docker` | Docker container management (ps, logs, exec, build, compose) |
| `database` | Execute SQL queries (PostgreSQL, MySQL, SQLite) |

### Network & Web
| Tool | Description |
|------|-------------|
| `http_request` | Make HTTP requests (GET, POST, PUT, DELETE, PATCH, etc.) |
| `http_download` | Download files from URLs |
| `web_search` | DuckDuckGo search |
| `web_fetch` | Fetch URL content |

### Utilities
| Tool | Description |
|------|-------------|
| `memory` | Persistent key-value storage |
| `todos` | Task list management |

## Claude Integration

Friday automatically discovers and integrates with `.claude/` folders:

### What is `.claude`?

The `.claude` folder contains specialized resources:

```
.claude/
├── agents/         # Sub-agent definitions
├── skills/         # Reusable patterns and guidelines
├── rules/          # Coding standards and rules
├── commands/       # Slash command definitions
└── workflows/      # Multi-step workflow templates
```

### Auto-Discovery

Friday automatically discovers `.claude` folders:
1. Current working directory (walking up)
2. `CLAUDE_DIR` environment variable
3. `~/.claude/` in home directory

### Commands

| Command | Description |
|---------|-------------|
| `/claude` | Show .claude integration status |
| `/agents` | List available .claude agents |
| `/skills` | List and activate skills |
| `/skills <name>` | Activate a specific skill |

## Security Features

- **Secret Scrubbing**: Automatically masks sensitive information (API keys, passwords) in tool outputs
- **Approval Policies**: Configure how the agent asks for permission before executing dangerous commands (`/approval`)
- **Path Validation**: Operations are restricted to allowed directories to protect your system
- **Dangerous Command Detection**: Automatically flags risky operations (rm -rf, sudo, etc.)

## Development

### From Source
```bash
git clone https://github.com/mk-knight23/Friday.git
cd Friday
pip install -e ".[dev]"
```

### Running Tests
```bash
# Run all tests
python tests/test_all_tools.py
python tests/test_new_tools.py

# Run claude integration tests (requires pytest)
pytest tests/test_claude_integration/ -v
```

## License

MIT
