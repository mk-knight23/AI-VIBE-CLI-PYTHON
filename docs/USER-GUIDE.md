# Friday AI - User Guide

Complete user documentation for Friday AI Teammate.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Built-in Tools](#built-in-tools)
5. [Advanced Features](#advanced-features)
6. [Session Management](#session-management)
7. [Autonomous Mode](#autonomous-mode)
8. [Claude Integration](#claude-integration)
9. [Workflows](#workflows)
10. [Tips & Best Practices](#tips--best-practices)

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Install from PyPI

```bash
pip install friday-ai-teammate
```

### Install from Source

```bash
git clone https://github.com/mk-knight23/AI-VIBE-CLI-PYTHON.git
cd AI-VIBE-CLI-PYTHON
pip install -e ".[dev]"
```

---

## Quick Start

### 1. Get API Credentials

Friday requires an API key from an LLM provider.

**Option A: Z.AI (GLM)**
- Sign up at [z.ai](https://z.ai)
- Get API key from dashboard
- Base URL: `https://api.z.ai/api/coding/paas/v4`

**Option B: MiniMax**
- Sign up at [minimaxi](https://minimaxi.com)
- Base URL: `https://api.minimax.io/v1`

**Option C: OpenAI-Compatible**
- Any OpenAI-compatible API
- Base URL: `https://api.openai.com/v1`

### 2. Configure API Key

**Environment Variables (Recommended):**
```bash
export API_KEY=your_api_key
export BASE_URL=https://api.provider.com/v1
```

**.env File:**
```env
API_KEY=your_api_key
BASE_URL=https://api.provider.com/v1
MODEL_NAME=gpt-4
```

### 3. Run Friday

**Interactive Mode:**
```bash
friday
```

**Single Prompt:**
```bash
friday "List all Python files in src/"
```

**With Working Directory:**
```bash
friday -c /path/to/project "Review this codebase"
```

---

## Configuration

### Config File

Create `~/.config/ai-agent/config.toml` or `./.ai-agent/config.toml`:

```toml
[model]
name = "GLM-4.7"
temperature = 1.0

[approval]
policy = "on-request"  # yolo, auto, on-request, never

[mcp_servers.sqlite]
command = "mcp-server-sqlite"
args = ["--db-path", "data.db"]
```

### Approval Policies

| Policy | Behavior |
|--------|----------|
| `yolo` | Auto-approve everything |
| `auto` | Auto-approve safe operations |
| `on-request` | Ask for each tool use |
| `never` | Never approve dangerous commands |

Change policy: `/approval <mode>`

---

## Built-in Tools

### File System Tools

| Tool | Description | Example |
|------|-------------|---------|
| `read_file` | Read file with line numbers | `read_file(path="main.py")` |
| `write_file` | Create/overwrite files | `write_file(path="test.py", content="...")` |
| `edit_file` | Replace text in files | `edit_file(path="main.py", old_string="foo", new_string="bar")` |
| `list_dir` | List directory contents | `list_dir(path=".")` |
| `glob` | Find files by pattern | `glob(pattern="**/*.py")` |
| `grep` | Search file contents | `grep(pattern="TODO", path="src/")` |

### System Tools

| Tool | Description | Example |
|------|-------------|---------|
| `shell` | Execute shell commands | `shell(command="ls -la")` |
| `git` | Git operations | `git(action="status")` |
| `docker` | Docker management | `docker(command="ps")` |
| `database` | SQL queries | `database(action="query", query="SELECT * FROM users")` |

### Network Tools

| Tool | Description | Example |
|------|-------------|---------|
| `http_request` | HTTP requests | `http_request(url="https://api.example.com", method="GET")` |
| `http_download` | Download files | `http_download(url="https://example.com/file.zip")` |
| `web_search` | DuckDuckGo search | `web_search(query="Python async best practices")` |
| `web_fetch` | Fetch URL content | `web_fetch(url="https://example.com")` |

### Utility Tools

| Tool | Description | Example |
|------|-------------|---------|
| `memory` | Key-value storage | `memory(action="set", key="project_name", value="MyProject")` |
| `todos` | Task management | `todos(action="add", task="Fix bug in login")` |

---

## Advanced Features

### Rich Terminal UI

- **Syntax Highlighting** - Code blocks are highlighted for readability
- **Progress Tracking** - Real-time updates during long operations
- **Streaming Responses** - Watch the AI think and respond in real-time
- **Tool Call Visualization** - See which tools are being used

### Safety Features

- **Secret Scrubbing** - API keys and passwords are automatically masked in output
- **Dangerous Command Detection** - Warnings for risky operations (rm -rf, sudo, etc.)
- **Path Validation** - Operations restricted to safe directories
- **Approval System** - Control when the agent can execute commands

### Hook System

Customize behavior with hooks:

```python
# ~/.claude/settings.json
{
  "hooks": {
    "preToolUse": [
      {
        "name": "check-large-edits",
        "command": "echo 'Reviewing large edit...'"
      }
    ],
    "postToolUse": [
      {
        "name": "auto-format",
        "command": "prettier --write $FILE"
      }
    ]
  }
}
```

---

## Session Management

### Save & Resume Sessions

**Save current session:**
```bash
/save
```

**List saved sessions:**
```bash
/sessions
```

**Resume a session:**
```bash
/resume <session_id>
```
Or:
```bash
friday --resume
```

### Checkpoints

Create named save points:

```bash
/checkpoint create "before-refactor"
/checkpoint restore "before-refactor"
```

---

## Autonomous Mode

Ralph-inspired autonomous development loop with intelligent exit detection.

### Start Autonomous Loop

```bash
friday
> /autonomous 50
```

### Features

- **Response Analysis** - JSON/text parsing with exit signal detection
- **Circuit Breaker** - Prevents runaway loops (CLOSED/HALF_OPEN/OPEN states)
- **Rate Limiting** - 100 API calls per hour
- **Session Continuity** - Maintains context across iterations (24-hour timeout)
- **Dual-Condition Exit** - Requires both completion indicators + EXIT_SIGNAL

### Control Loop

```bash
/loop status    # Show loop status
/loop stop      # Stop the loop
/circuit status # Check circuit breaker state
/circuit reset  # Reset circuit breaker
```

### Status File

Real-time status in `.friday/status.json`:
```json
{
  "state": "running",
  "loop_number": 5,
  "circuit_breaker": {
    "state": "closed",
    "no_progress_count": 0
  },
  "rate_limit": {
    "calls_remaining": 95
  }
}
```

---

## Claude Integration

Friday automatically discovers `.claude/` folders:

### Agents (13)

Specialized sub-agents for specific tasks:

| Agent | Purpose | Command |
|-------|---------|---------|
| `architect` | System design | `/plan "Design auth system"` |
| `code-reviewer` | Code quality | `/code-review` |
| `security-reviewer` | Security analysis | `/skills security-review` |
| `tdd-guide` | Test-driven development | `/tdd` |
| `planner` | Implementation planning | `/plan "Add feature X"` |

### Skills (18)

Domain-specific patterns and guidelines:

```
/skills                    # List all skills
/skills backend-patterns   # Activate backend patterns
/skills security-review    # Activate security review
```

Available skills:
- `backend-patterns` - API design, database optimization
- `frontend-patterns` - React, Next.js, state management
- `golang-patterns` - Go idioms and concurrency
- `security-review` - Security checklist
- `tdd-workflow` - Test-driven development
- And more...

### Rules (7)

Coding standards automatically loaded from `.claude/rules/`:
- `coding-style.md` - Immutability, small files, error handling
- `git-workflow.md` - Commit conventions, PR workflow
- `testing.md` - TDD requirements, 80%+ coverage
- `security.md` - Security checklist
- `performance.md` - Model selection, context management

### Workflows (4)

Multi-step processes:
```bash
/workflow audit       # Code auditing workflow
/workflow testing     # Testing workflow
/workflow deployment  # Deployment workflow
```

---

## Workflows

### Code Review Workflow

```bash
friday
> /code-review
```

The `code-reviewer` agent will:
1. Analyze your code for quality issues
2. Check for security vulnerabilities
3. Suggest improvements
4. Provide detailed feedback

### TDD Workflow

```bash
friday
> /tdd
```

The `tdd-guide` agent will:
1. Enforce writing tests first
2. Implement minimal code to pass
3. Refactor while keeping tests green
4. Verify 80%+ coverage

### Planning Workflow

```bash
friday
> /plan "Implement user authentication"
```

The `planner` agent will:
1. Analyze requirements
2. Design architecture
3. Identify dependencies
4. Create implementation plan

---

## Tips & Best Practices

### For Best Results

1. **Use Interactive Mode** - For complex, multi-step tasks
2. **Provide Context** - Give Friday information about your project
3. **Start Small** - Test with simple tasks before complex ones
4. **Review Output** - Always review generated code before using
5. **Use Version Control** - Keep your work in git

### Common Workflows

**Code Review:**
```bash
friday "Review src/auth.py for security issues"
```

**Refactoring:**
```bash
friday "Refactor this function to be more readable"
```

**Documentation:**
```bash
friday "Generate documentation for this module"
```

**Testing:**
```bash
friday "Write unit tests for database.py"
```

**Debugging:**
```bash
friday "Help me debug this error: [paste error]"
```

### Getting Help

- `/help` - Show all available commands
- `/tools` - List all available tools
- `/stats` - Show usage statistics
- `/config` - Show current configuration

---

## Troubleshooting

### Common Issues

**"API key not found"**
- Check your `.env` file or environment variables
- Ensure `API_KEY` is set

**"Module not found"**
- Reinstall: `pip install --force-reinstall friday-ai-teammate`

**Slow responses**
- Check your internet connection
- Try a different model/provider

**Loop won't start**
- Check `.friday/PROMPT.md` exists
- Verify rate limit not exceeded
- Check circuit breaker: `/circuit status`

### Logs

- Autonomous logs: `.friday/logs/`
- Status file: `.friday/status.json`
- Session file: `.friday/.session_id`

---

*Friday AI Teammate v1.0.0 - User Guide*
