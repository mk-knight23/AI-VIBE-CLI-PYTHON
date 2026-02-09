# Friday AI - User Guide
## Getting Started with Friday AI Teammate

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Basic Usage](#basic-usage)
5. [Working with Projects](#working-with-projects)
6. [Safety Features](#safety-features)
7. [Tips and Best Practices](#tips-and-best-practices)

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
git clone https://github.com/mk-knight23/Friday.git
cd Friday
pip install -e ".[dev]"
```

---

## Quick Start

### 1. Get API Credentials

Friday requires an API key from an LLM provider:

**Option A: Z.AI (GLM)**
- Sign up at [z.ai](https://z.ai)
- Get API key from dashboard
- Base URL: `https://api.z.ai/api/coding/paas/v4`

**Option B: MiniMax**
- Sign up at [minimax.io](https://minimax.io)
- Get API key
- Base URL: `https://api.minimax.io/v1`

**Option C: OpenAI-Compatible Provider**
- Any provider with OpenAI API compatibility
- Set base URL accordingly

### 2. Configure Environment

**Method 1: Environment Variables**

```bash
export API_KEY=your_api_key_here
export BASE_URL=https://api.z.ai/api/coding/paas/v4
```

**Method 2: .env File**

Create a `.env` file in your working directory:

```env
API_KEY=your_api_key_here
BASE_URL=https://api.z.ai/api/coding/paas/v4
```

### 3. Run Friday

**Interactive mode:**
```bash
friday
```

**Single prompt:**
```bash
friday "Hello! List all files in the current directory"
```

---

## Configuration

### Configuration File Locations

Friday loads configuration from (in order of priority):

1. `./.ai-agent/config.toml` - Project-specific
2. `~/.config/ai-agent/config.toml` - User-specific
3. Environment variables

### Basic Configuration

```toml
# .ai-agent/config.toml or ~/.config/ai-agent/config.toml

[model]
name = "GLM-4.7"
temperature = 1.0

# Default working directory
cwd = "/home/user/projects"

# Approval policy: yolo, auto, auto-edit, on-request, on-failure, never
approval = "auto"

# Maximum conversation turns
max_turns = 100
```

### Shell Environment Configuration

```toml
[shell_environment]
ignore_default_excludes = false
exclude_patterns = ["*KEY*", "*TOKEN*", "*SECRET*", "*PASSWORD*"]

[shell_environment.set_vars]
PYTHONPATH = "/custom/path"
MY_VAR = "value"
```

---

## Basic Usage

### Interactive Mode

Start a conversation with Friday:

```bash
$ friday

╭─ Friday ─────────────────────────────────────────────────────────────────────╮
│                                                                              │
│  model: GLM-4.7                                                              │
│  cwd: /Users/mkazi/CLI/AI-VIBE-CLI-V2                                        │
│  commands: /help /config /approval /model /exit                              │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

[user]> Hello! What can you help me with?
```

### Single Prompt Mode

Execute one command and exit:

```bash
friday "Find all Python files modified in the last week"
friday "Review this codebase for security issues"
friday "Help me refactor the auth module"
```

### Working Directory

Set a specific directory for the agent to work in:

```bash
friday -c ~/projects/my-app "Analyze the API endpoints"
friday --cwd /path/to/project "Generate tests"
```

---

## Working with Projects

### Project Structure

For best results, organize your project with Friday in mind:

```
my-project/
├── .ai-agent/
│   ├── config.toml      # Project-specific config
│   └── tools/           # Custom tools (optional)
├── src/
├── tests/
└── README.md
```

### Creating Project Configuration

```bash
mkdir -p .ai-agent
cat > .ai-agent/config.toml << 'EOF'
[model]
name = "GLM-4.7"

# Project-specific settings
approval = "auto"
cwd = "."

# Custom instructions for the AI
developer_instructions = """
This is a Python web application using FastAPI.
- Follow PEP 8 style guide
- Use type hints
- Write docstrings for all public functions
"""
EOF
```

### Common Tasks

#### Code Analysis

```
[user]> Analyze the codebase structure and identify main components
```

#### File Operations

```
[user]> Read the main.py file and explain what it does
[user]> Create a new file called config.py with a Config class
[user]> Edit the utils.py file to add error handling
```

#### Search and Exploration

```
[user]> Search for all functions that handle user authentication
[user]> Find all files that import the requests library
[user]> List all test files in the project
```

#### Web Research

```
[user]> Search for best practices for Python async programming
[user]> Fetch the documentation from https://docs.python.org/3/library/asyncio.html
```

---

## Safety Features

### Approval Policies

Choose how much control you want:

| Policy | When to Use |
|--------|-------------|
| `on-request` | Maximum safety - approve every tool call |
| `auto` | Balanced - approve only dangerous operations |
| `auto-edit` | Read freely, confirm edits |
| `yolo` | ⚠️ Never ask - use only in safe environments |

**Change policy during session:**

```
[user]> /approval auto
[success] Approval policy changed to: auto
```

### Dangerous Command Detection

Friday automatically warns about:

- `rm -rf` commands
- Database drop operations
- File overwrites with `>`
- `curl | bash` patterns
- Commands with `sudo`

### Review Before Execution

When approval is required, Friday shows:

```
╭─ ⏺ shell  #call_abc ─────────────────────────────────────────────────────────╮
│                                                                              │
│  command rm -rf /tmp/old-data                                                │
│                                                                              │
╰──────────────────────────────────────────────────────────────────── running ─╯

Approve this shell command? [y/N]: y
```

---

## Tips and Best Practices

### 1. Be Specific

**Good:**
```
Find all Python files in the src directory that contain class definitions
```

**Less effective:**
```
Find classes
```

### 2. Use Context

Friday remembers conversation context:

```
[user]> Find all API routes in the app
... (Friday lists routes)

[user]> Now add authentication to the first one
... (Friday knows which one you mean)
```

### 3. Clear Context When Needed

If context gets too long or confusing:

```
[user]> /clear
[success] Conversation cleared
```

### 4. Save Important Sessions

```
[user]> /save
[success] Session saved: abc-123-def

# Later:
[user]> /resume abc-123-def
```

### 5. Use Checkpoints for Complex Tasks

```
[user]> /checkpoint
[success] Checkpoint created: checkpoint-1

# Do some work...

[user]> /restore checkpoint-1  # If something goes wrong
```

### 6. Check Available Tools

```
[user]> /tools
Available tools (11)
  • read_file
  • write_file
  • edit_file
  • list_dir
  • glob
  • grep
  • shell
  • web_search
  • web_fetch
  • memory
  • todos
```

### 7. Use Memory for Persistence

```
[user]> Remember that the main entry point is in app/main.py
... (Friday uses memory tool)

[user]> How do I run this app again?
... (Friday recalls the entry point)
```

### 8. Manage Todos

```
[user]> Add a todo: Review the authentication module
[user]> Add a todo: Write tests for user service
[user]> Show my todos
```

---

## Troubleshooting

### "No API key found"

Set your API key:
```bash
export API_KEY=your_key_here
export BASE_URL=https://api.provider.com/v1
```

### "API error: usage limit exceeded"

Your API key has hit a rate limit. Check your provider dashboard or wait before retrying.

### Commands not executing

Check your approval policy:
```
[user]> /approval yolo  # Auto-approve everything (use with caution)
```

### Context too long

Clear the conversation:
```
[user]> /clear
```

---

## Next Steps

- Read the [Feature Guide](FEATURE-GUIDE.md) for complete feature reference
- Check [Commands Reference](COMMANDS.md) for all CLI options
- See [Developer Guide](DEVELOPER-GUIDE.md) to contribute

---

*User Guide v1.0 - Friday AI Teammate*
