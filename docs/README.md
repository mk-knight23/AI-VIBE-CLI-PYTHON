# Friday AI Teammate - Documentation

**Consolidated Documentation** (v1.0.0)

All documentation has been reorganized into 5 comprehensive files located in the project root:

## Core Documentation

| Document | Purpose | Location |
|----------|---------|----------|
| **[README.md](../README.md)** | Project overview, quick start, features | Root directory |
| **[USER-GUIDE.md](USER-GUIDE.md)** | Complete user documentation | docs/ |
| **[DEVELOPER-GUIDE.md](DEVELOPER-GUIDE.md)** | Developer & contributing guide | docs/ |
| **[OPERATIONS-GUIDE.md](OPERATIONS-GUIDE.md)** | Installation, CI/CD, upgrades | docs/ |
| **[PROJECT-DOCS.md](PROJECT-DOCS.md)** | Architecture, audits, implementation | docs/ |
| **[CHANGELOG.md](CHANGELOG.md)** | Version history and changes | docs/ |

## Quick Links

### For Users
- **[Getting Started](../README.md#quick-start)** - Install and run Friday
- **[Built-in Tools](../USER-GUIDE.md#built-in-tools)** - 16 tools for file, system, web operations
- **[Claude Integration](../USER-GUIDE.md#claude-integration)** - 13 agents, 18 skills, workflows
- **[Autonomous Mode](../USER-GUIDE.md#autonomous-mode)** - Ralph-inspired development loop
- **[Session Management](../USER-GUIDE.md#session-management)** - Save, resume, checkpoint

### For Developers
- **[Development Setup](../DEVELOPER-GUIDE.md#development-setup)** - Clone and install
- **[Adding Tools](../DEVELOPER-GUIDE.md#adding-new-tools)** - Create custom tools
- **[Testing](../DEVELOPER-GUIDE.md#testing)** - Run and write tests
- **[Architecture](../PROJECT-DOCS.md#architecture-overview)** - System design
- **[Best Practices](../DEVELOPER-GUIDE.md#best-practices)** - Coding standards

### For Operations
- **[Installation](../OPERATIONS-GUIDE.md#installation)** - Deploy Friday
- **[Configuration](../OPERATIONS-GUIDE.md#configuration-management)** - Setup and config
- **[CI/CD](../OPERATIONS-GUIDE.md#cicd-pipeline)** - GitHub Actions
- **[Upgrading](../OPERATIONS-GUIDE.md#upgrading)** - Version upgrades
- **[Monitoring](../OPERATIONS-GUIDE.md#monitoring)** - Metrics and logging

## Archive

Historical documentation files have been moved to the [archive/](archive/) directory:
- Original 23 documentation files
- Previous versions of guides
- Legacy audit documents

---

## Project Overview

Friday AI is an agent-based AI assistant for terminal-based coding workflows:

- **16 Built-in Tools** - File operations, shell, git, docker, database, HTTP, web search
- **Claude Integration** - Load agents, skills, rules, workflows from `.claude/` folders
- **Security First** - Secret scrubbing, approval policies, path validation
- **Session Management** - Save, resume, checkpoint sessions
- **MCP Support** - Model Context Protocol for external tools
- **Autonomous Mode** - Ralph-inspired development loop with circuit breaker
- **Enterprise Ready** - API server, monitoring, observability, resilience

---

## Quick Start

```bash
# Install
pip install friday-ai-teammate

# Configure
export API_KEY=your_api_key
export BASE_URL=https://api.provider.com/v1

# Run
friday "Help me refactor this code"
```

---

*Documentation for Friday AI Teammate v1.0.0*
