# Friday AI - Feature Guide
## Complete Feature Reference

---

## Table of Contents

1. [Core Features](#core-features)
2. [Built-in Tools](#built-in-tools)
3. [Advanced Features](#advanced-features)
4. [Safety & Security](#safety--security)
5. [Session Management](#session-management)
6. [Configuration](#configuration)

---

## Core Features

### Interactive Mode
Start an interactive chat session with the AI assistant.

```bash
friday
```

Features in interactive mode:
- Context-aware conversations
- Tool call visualization
- Command history
- Real-time streaming responses

### Single Prompt Mode
Run a specific task and get results immediately.

```bash
friday "List all Python files in the current directory"
friday "Review this codebase for security issues"
friday "Help me refactor this function"
```

### Working Directory Support
Set a custom working directory for the agent.

```bash
friday -c /path/to/project "Analyze this codebase"
```

---

## Built-in Tools

Friday comes with 13 built-in tools organized by category:

### File System Tools

| Tool | Description | Example |
|------|-------------|---------|
| `read_file` | Read file contents with line numbers | `read_file(path="main.py")` |
| `write_file` | Create or overwrite files | `write_file(path="test.py", content="...")` |
| `edit_file` | Surgical text replacement | `edit_file(path="main.py", old_string="...", new_string="...")` |
| `list_dir` | List directory contents | `list_dir(path=".")` |
| `glob` | Find files by pattern | `glob(pattern="**/*.py")` |
| `grep` | Search file contents | `grep(pattern="def ", path="src")` |

### System Tools

| Tool | Description | Example |
|------|-------------|---------|
| `shell` | Execute shell commands safely | `shell(command="ls -la")` |
| `docker` | Docker container management | `docker(command="ps")` |
| `database` | Execute SQL queries | `database(action="query", query="SELECT * FROM users")` |

### Web Tools

| Tool | Description | Example |
|------|-------------|---------|
| `web_search` | DuckDuckGo search | `web_search(query="Python asyncio")` |
| `web_fetch` | Fetch URL content | `web_fetch(url="https://example.com")` |

### Utility Tools

| Tool | Description | Example |
|------|-------------|---------|
| `memory` | Persistent key-value storage | `memory(action="set", key="context", value="...")` |
| `todos` | Task list management | `todos(action="add", text="Review PR")` |

---

## Advanced Features

### MCP (Model Context Protocol) Support

Friday supports MCP for connecting to external tool servers.

**Configuration in `config.toml`:**

```toml
[mcp_servers.my-server]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"]
enabled = true
```

**Features:**
- Connect to stdio-based MCP servers
- HTTP/SSE transport support
- Automatic tool discovery from MCP servers
- Server health monitoring

### Subagents

Specialized agents for complex tasks:

| Subagent | Purpose |
|----------|---------|
| `codebase_investigator` | Deep codebase analysis and exploration |
| `code_reviewer` | Code review with structured feedback |

**Usage:**

```python
# From within the agent framework
await subagent.run("codebase_investigator", "Find all API endpoints")
```

### Dynamic Tool Discovery

Friday can load custom tools from the `.ai-agent/tools/` directory.

**Structure:**

```
.ai-agent/
├── tools/
│   ├── my_custom_tool.py
│   └── another_tool.py
└── config.toml
```

**Custom Tool Example:**

```python
# .ai-agent/tools/my_custom_tool.py
from friday_ai.tools.base import Tool, ToolParameter

class MyCustomTool(Tool):
    name = "my_custom_tool"
    description = "Does something custom"
    parameters = [
        ToolParameter(name="input", type="string", required=True)
    ]

    async def execute(self, input: str) -> str:
        return f"Processed: {input}"
```

### Hook System

Execute custom code before/after agent runs and tool calls.

**Hook Types:**

| Trigger | Description |
|---------|-------------|
| `before_agent` | Run before agent starts |
| `after_agent` | Run after agent completes |
| `before_tool` | Run before tool execution |
| `after_tool` | Run after tool execution |
| `on_error` | Run when errors occur |

**Configuration:**

```toml
hooks_enabled = true

[[hooks]]
name = "log-tool-calls"
trigger = "after_tool"
command = "echo 'Tool executed: {{tool_name}}' >> /tmp/friday.log"
timeout_sec = 5
enabled = true
```

---

## .claude Folder Integration

Friday integrates with `.claude` folders for enhanced functionality:

### What is .claude?

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

### Available Commands

| Command | Description |
|---------|-------------|
| `/claude` | Show .claude integration status |
| `/agents` | List available .claude agents |
| `/skills` | List and activate skills |
| `/skills <name>` | Activate a specific skill |

### Agents

Agents from `.claude/agents/` are loaded as subagent tools:

```
[user]> /agents
Available Agents
  • code-reviewer: Expert code review specialist
  • security-reviewer: Security vulnerability detection
  • tdd-guide: Test-Driven Development specialist
  ...
```

### Skills

Skills provide contextual guidance for specific tasks:

```
[user]> /skills
Available Skills
  ● tdd-workflow: TDD with 80%+ coverage
  ○ golang-patterns: Idiomatic Go patterns
  ○ postgres-patterns: PostgreSQL best practices

[user]> /skills golang-patterns
[success] Activated skill: golang-patterns
```

### Commands

All `.claude/commands/` are available as slash commands:

```
[user]> /tdd "Implement user authentication"
# Invokes the tdd-guide agent

[user]> /plan "Add payment integration"
# Invokes the planner agent

[user]> /e2e
# Runs end-to-end testing workflow
```

---

## Safety & Security

### Approval Policies

Control when Friday asks for permission:

| Policy | Description |
|--------|-------------|
| `yolo` | Never ask (dangerous) |
| `auto` | Ask for dangerous commands only |
| `auto-edit` | Auto-approve reads, ask for edits |
| `on-request` | Ask for every tool call |
| `on-failure` | Auto-approve, ask on failure |
| `never` | Never execute tools |

**Change in interactive mode:**

```
[user]> /approval auto
[success] Approval policy changed to: auto
```

### Dangerous Command Detection

Friday automatically detects and flags:

- `rm -rf` commands
- Database drop operations
- `>` output redirection to existing files
- `>>` append to sensitive files
- `curl | bash` patterns
- `wget | sh` patterns
- Commands with `sudo`

### Secret Scrubbing

Sensitive patterns are automatically redacted in output:
- API keys
- Passwords
- Tokens
- Environment variables with secrets

---

## Session Management

### Session Persistence

Save and resume agent sessions:

```
[user]> /save
[success] Session saved: session-uuid-here

[user]> /sessions
Saved Sessions
  • session-uuid-here (turns: 15, updated: 2025-01-31T10:30:00)

[user]> /resume session-uuid-here
[success] Resumed session: session-uuid-here
```

### Checkpoints

Create restore points during complex tasks:

```
[user]> /checkpoint
[success] Checkpoint created: checkpoint-abc123

# Do some work...

[user]> /restore checkpoint-abc123
[success] Restored session: session-uuid, checkpoint: checkpoint-abc123
```

### Session Statistics

View usage statistics:

```
[user]> /stats
Session Statistics
   turn_count: 15
   message_count: 32
   total_tokens: 15420
   tool_calls: 8
```

---

## Configuration

### Configuration Files

Friday loads configuration from multiple sources:

1. **System config**: `~/.config/ai-agent/config.toml`
2. **Project config**: `./.ai-agent/config.toml`
3. **Environment variables**: `API_KEY`, `BASE_URL`

### Configuration Options

```toml
# Model settings
[model]
name = "GLM-4.7"
temperature = 1.0
context_window = 256000

# Working directory
cwd = "/path/to/project"

# Approval policy
approval = "on-request"  # yolo, auto, auto-edit, on-request, on-failure, never

# Maximum turns per session
max_turns = 100

# Enable hooks
hooks_enabled = true

# Shell environment
[shell_environment]
ignore_default_excludes = false
exclude_patterns = ["*KEY*", "*TOKEN*", "*SECRET*"]

[shell_environment.set_vars]
MY_VAR = "value"

# MCP servers
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
enabled = true

[mcp_servers.fetch]
url = "https://example.com/mcp"
enabled = true

# Hooks
[[hooks]]
name = "notify"
trigger = "after_agent"
command = "notify-send 'Friday AI' 'Task completed'"
enabled = true
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `API_KEY` | API key for LLM provider | Yes |
| `BASE_URL` | Base URL for API endpoint | Yes |
| `FRIDAY_DEBUG` | Enable debug logging | No |

---

## Interactive Commands

When running in interactive mode, these commands are available:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/exit` or `/quit` | Exit the application |
| `/clear` | Clear conversation context |
| `/config` | Show current configuration |
| `/model <name>` | Change the AI model |
| `/approval <policy>` | Change approval policy |
| `/stats` | Show session statistics |
| `/tools` | List available tools |
| `/mcp` | Show MCP server status |
| `/save` | Save current session |
| `/sessions` | List saved sessions |
| `/resume <id>` | Resume a saved session |
| `/checkpoint` | Create a checkpoint |
| `/restore <id>` | Restore a checkpoint |

---

*Feature Guide v1.0 - Friday AI Teammate*
