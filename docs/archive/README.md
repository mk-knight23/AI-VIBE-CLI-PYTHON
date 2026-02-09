# Friday AI Teammate - Documentation

Welcome to the Friday AI Teammate documentation. This is a Python-based AI assistant framework for terminal-based coding workflows.

## Documentation Structure

| Document | Purpose |
|----------|---------|
| [USER-GUIDE.md](USER-GUIDE.md) | Getting started and usage instructions |
| [FEATURE-GUIDE.md](FEATURE-GUIDE.md) | Complete feature reference |
| [COMMANDS.md](COMMANDS.md) | CLI commands and options |
| [DEVELOPER-GUIDE.md](DEVELOPER-GUIDE.md) | Contributing and development |
| [BEST-PRACTICES.md](BEST-PRACTICES.md) | Python development standards |
| [TESTING.md](TESTING.md) | Testing strategy and patterns |
| [SECURITY.md](SECURITY.md) | Security features and guidelines |
| [TECH-STACK.md](TECH-STACK.md) | Technology stack overview |
| [WORKFLOWS.md](WORKFLOWS.md) | Common usage workflows |
| [CICD.md](CICD.md) | CI/CD configuration |
| [CLAUDE.md](CLAUDE.md) | AI assistant instructions |
| [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) | Architecture decisions |

## .claude Folder Integration

Friday AI integrates with `.claude` folders to provide:

- **Agents** - Specialized sub-agents from `.claude/agents/`
- **Skills** - Contextual patterns from `.claude/skills/`
- **Rules** - Coding standards from `.claude/rules/`
- **Commands** - Slash commands from `.claude/commands/`
- **Workflows** - Multi-step workflows from `.claude/workflows/`

See [CLAUDE-INTEGRATION.md](CLAUDE-INTEGRATION.md) for details.

## Quick Start

```bash
# Install
pip install friday-ai-teammate

# Configure
export API_KEY=your_api_key
export BASE_URL=https://api.provider.com/v1

# Run
friday "Help me with this code"
```

## Project Overview

Friday AI is an agent-based AI assistant with:

- **11 Built-in Tools** - File operations, shell, web search, memory, todos
- **MCP Support** - Model Context Protocol for external tools
- **Subagents** - Specialized agents for codebase investigation
- **Hook System** - Customizable execution hooks
- **Safety Features** - Approval policies and dangerous command detection
- **Session Management** - Persistent sessions with save/restore

---

*Documentation for Friday AI Teammate v0.0.2*
