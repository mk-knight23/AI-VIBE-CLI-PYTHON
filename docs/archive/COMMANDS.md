# Friday AI - Commands Reference
## CLI Commands and Options

---

## Global Usage

```bash
friday [OPTIONS] [PROMPT]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `PROMPT` | No | Single prompt to execute (if omitted, starts interactive mode) |

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--cwd DIRECTORY` | `-c` | Set the working directory for the agent |
| `--help` | | Show help message and exit |

## Examples

### Interactive Mode

Start an interactive chat session:

```bash
friday
```

### Single Prompt

Execute a single prompt and exit:

```bash
friday "List all Python files"
friday "Review this code for bugs"
friday "Help me understand this codebase"
```

### With Custom Working Directory

```bash
friday -c /path/to/project "Analyze this codebase"
friday --cwd ~/projects/my-app "Generate tests for the auth module"
```

---

## Interactive Mode Commands

When running in interactive mode, these slash commands are available:

### Session Management

| Command | Description |
|---------|-------------|
| `/exit` or `/quit` | Exit the application |
| `/save` | Save the current session to disk |
| `/sessions` | List all saved sessions |
| `/resume <id>` | Resume a previously saved session |
| `/checkpoint` | Create a checkpoint (restore point) |
| `/restore <id>` | Restore to a checkpoint |
| `/clear` | Clear conversation context and loop detector |
| `/stats` | Show session statistics |

### Configuration

| Command | Description |
|---------|-------------|
| `/config` | Display current configuration |
| `/model <name>` | Change the AI model (e.g., `/model GLM-4.7`) |
| `/approval <policy>` | Change approval policy (see below) |

### Tool Management

| Command | Description |
|---------|-------------|
| `/tools` | List all available tools |
| `/mcp` | Show MCP server status and connected tools |

### .claude Integration

| Command | Description |
|---------|-------------|
| `/claude` | Show .claude integration status |
| `/agents` | List available .claude agents |
| `/skills` | List available skills |
| `/skills <name>` | Activate a specific skill |

### Help

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |

---

## Approval Policies

Set with `/approval <policy>`:

| Policy | Description | Use Case |
|--------|-------------|----------|
| `yolo` | Never ask for approval | ⚠️ Dangerous - use with caution |
| `auto` | Ask only for dangerous commands | ✅ Recommended default |
| `auto-edit` | Auto-approve reads, ask for edits | ✅ Balanced approach |
| `on-request` | Ask for every tool call | 🔒 Maximum safety |
| `on-failure` | Auto-approve, ask on failure | 🔄 Retry-focused |
| `never` | Never execute any tools | 🔒 Disabled mode |

### Examples

```
[user]> /approval auto
[success] Approval policy changed to: auto

[user]> /approval yolo
[success] Approval policy changed to: yolo
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_KEY` | Yes | API key for your LLM provider |
| `BASE_URL` | Yes | Base URL for the API endpoint |
| `FRIDAY_DEBUG` | No | Enable debug logging (set to `1` or `true`) |

### Examples

```bash
# Configure for MiniMax
export API_KEY=your_minimax_key
export BASE_URL=https://api.minimax.io/v1

# Configure for GLM/Z.AI
export API_KEY=your_glm_key
export BASE_URL=https://api.z.ai/api/coding/paas/v4

# Run
friday
```

Or use a `.env` file:

```env
API_KEY=your_api_key_here
BASE_URL=https://api.provider.com/v1
```

---

## Configuration Files

Friday loads configuration from (in order of priority):

1. `./.ai-agent/config.toml` (project-level)
2. `~/.config/ai-agent/config.toml` (user-level)
3. Environment variables

### Example `config.toml`

```toml
[model]
name = "GLM-4.7"
temperature = 1.0

# Working directory
cwd = "/home/user/projects/my-app"

# Approval policy
approval = "auto"

# Maximum turns per session
max_turns = 100

# Enable hooks
hooks_enabled = false
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (configuration, API, or execution error) |

---

## Tips

1. **Use quotes for complex prompts:**
   ```bash
   friday "Find all functions that use the requests library"
   ```

2. **Set working directory for project-specific tasks:**
   ```bash
   friday -c ~/projects/webapp "Analyze the API routes"
   ```

3. **Interactive mode for multi-step tasks:**
   ```bash
   friday
   # Then have a conversation
   ```

4. **Use `/clear` when context gets too long:**
   ```
   [user]> /clear
   [success] Conversation cleared
   ```

---

*Commands Reference v1.0 - Friday AI Teammate*
