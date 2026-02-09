# Friday AI - Operations Guide

Complete operations and maintenance documentation for Friday AI Teammate.

---

## Table of Contents

1. [Installation](#installation)
2. [Configuration Management](#configuration-management)
3. [CI/CD Pipeline](#cicd-pipeline)
4. [Upgrading](#upgrading)
5. [Deployment](#deployment)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Version History](#version-history)

---

## Installation

### System Requirements

- **Python:** 3.10 or higher
- **Operating System:** Linux, macOS, Windows
- **Memory:** 512MB minimum, 1GB recommended
- **Disk Space:** 100MB for installation

### Installation Methods

#### Method 1: PyPI (Recommended)

```bash
pip install friday-ai-teammate
```

#### Method 2: From Source

```bash
git clone https://github.com/mk-knight23/AI-VIBE-CLI-PYTHON.git
cd AI-VIBE-CLI-PYTHON
pip install -e .
```

#### Method 3: With Development Dependencies

```bash
git clone https://github.com/mk-knight23/AI-VIBE-CLI-PYTHON.git
cd AI-VIBE-CLI-PYTHON
pip install -e ".[dev]"
```

### Docker Deployment

```bash
# Build image
docker build -t friday-ai:latest -f Dockerfile.api .

# Run container
docker-compose up -d
```

### Verification

```bash
# Check installation
friday --version

# Run help
friday --help

# Run tests
pytest tests/ -v
```

---

## Configuration Management

### Configuration Locations

Friday searches for config in this order:

1. `./.ai-agent/config.toml` (project-specific)
2. `~/.config/ai-agent/config.toml` (user-specific)
3. Environment variables
4. `.env` file in working directory

### Config File Structure

```toml
# ~/.config/ai-agent/config.toml

[model]
name = "GLM-4.7"
temperature = 1.0
context_window = 256000

[approval]
policy = "on-request"
auto_edit = false

[loop]
max_calls_per_hour = 100
max_no_progress_loops = 3
max_consecutive_errors = 5

[mcp_servers.sqlite]
command = "mcp-server-sqlite"
args = ["--db-path", "data.db"]

[mcp_servers.github]
command = "mcp-server-github"
args = ["--token", "$GITHUB_TOKEN"]
```

### Environment Variables

```bash
# API Configuration
export API_KEY=your_api_key
export BASE_URL=https://api.provider.com/v1
export MODEL_NAME=GLM-4.7

# Optional
export CLAUDE_DIR=/path/to/.claude
export FRIDAY_LOG_LEVEL=INFO
```

### .env File

```env
# .env
API_KEY=your_api_key
BASE_URL=https://api.provider.com/v1
MODEL_NAME=GLM-4.7
TEMPERATURE=1.0
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -e ".[dev]"

    - name: Run tests
      run: |
        pytest tests/ -v --cov=friday_ai

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

---

## Upgrading

### Version Compatibility

| Friday Version | Python 3.10 | Python 3.11 | Python 3.12 |
|----------------|------------|------------|------------|
| 1.0.x          | ✅         | ✅         | ✅         |
| 0.3.x          | ✅         | ✅         | ✅         |
| 0.2.x          | ✅         | ✅         | ✅         |

### Upgrade Procedure

#### From v0.3.0 to v1.0.0

**Breaking Changes:**
- `.env` file format changed
- Session storage moved to `~/.config/friday/sessions/`
- Config file moved to `~/.config/ai-agent/config.toml`

**Migration Steps:**

1. Backup your configuration:
   ```bash
   cp ~/.friday/config.toml ~/.friday/config.toml.backup
   ```

2. Upgrade:
   ```bash
   pip install --upgrade friday-ai-teammate
   ```

3. Update config format:
   ```bash
   # Old location: ~/.friday/config.toml
   # New location: ~/.config/ai-agent/config.toml
   mkdir -p ~/.config/ai-agent
   mv ~/.friday/config.toml ~/.config/ai-agent/config.toml
   ```

4. Update API keys in `.env`:
   ```env
   # Old format
   API_KEY=sk-cp-...

   # New format (replace with placeholder)
   API_KEY=your-api-key-here
   ```

See [UPGRADE-v0.3.0.md](docs/UPGRADE-v0.3.0.md) for details.

#### From v0.2.0 to v0.3.0

**New Features:**
- Ralph-inspired autonomous mode
- Session management
- Circuit breaker
- Rate limiting

**Migration:** No breaking changes. Simply upgrade:
```bash
pip install --upgrade friday-ai-teammate
```

#### From v0.1.0 to v0.2.0

**New Features:**
- Session save/restore
- Checkpoint system
- Enhanced Claude integration

**Migration:** No breaking changes. Simply upgrade:
```bash
pip install --upgrade friday-ai-teammate
```

---

## Deployment

### Production Deployment

#### As Python Package

```bash
# Install
pip install friday-ai-teammate

# Configure
mkdir -p ~/.config/ai-agent
cat > ~/.config/ai-agent/config.toml << EOF
[model]
name = "GLM-4.7"

[approval]
policy = "on-request"
EOF

# Run
friday
```

#### As Docker Service

```yaml
# docker-compose.yml
version: '3.8'

services:
  friday-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - API_KEY=${API_KEY}
      - BASE_URL=${BASE_URL}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
```

```bash
# Deploy
docker-compose up -d

# View logs
docker-compose logs -f friday-api
```

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics
```

---

## Monitoring

### Metrics Endpoint

Friday AI exposes Prometheus-compatible metrics:

```
# Available metrics
friday_requests_total
friday_duration_seconds
friday_errors_total
friday_active_sessions
```

### Performance Dashboard

```bash
# Start monitoring dashboard
friday-monitor

# Or access web UI
open http://localhost:8000/dashboard
```

### Log Levels

Configure log level:

```bash
export FRIDAY_LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

Or in config:

```toml
[logging]
level = "INFO"
file = "/var/log/friday/app.log"
```

---

## Troubleshooting

### Common Issues

#### "API key not found"

**Cause:** API key not configured

**Solution:**
```bash
export API_KEY=your_api_key
export BASE_URL=https://api.provider.com/v1
```

#### "Module not found"

**Cause:** Installation incomplete

**Solution:**
```bash
pip install --force-reinstall friday-ai-teammate
```

#### "Rate limit exceeded"

**Cause:** Too many API calls

**Solution:**
```bash
# Check status
/monitor

# Reset circuit breaker
/circuit reset

# Wait for hourly reset (automatic)
```

#### "Session expired"

**Cause:** Session older than 24 hours

**Solution:**
```bash
# Start new session
friday

# Or resume if within 24 hours
friday --resume
```

### Debug Mode

Enable debug logging:

```bash
export FRIDAY_LOG_LEVEL=DEBUG
friday
```

### Diagnostic Commands

```bash
# Check version
friday --version

# Check configuration
/config

# Check tools
/tools

# Check Claude integration
/claude

# View stats
/stats
```

---

## Version History

### v1.0.0 (Current)

**Release Date:** February 2026

**Major Features:**
- Enterprise packages (API, monitoring, security, resilience)
- Comprehensive error hierarchy (20+ error classes)
- Ralph-inspired autonomous mode with JSON response parsing
- Session continuity across iterations (24-hour timeout)
- Circuit breaker with 3 states (CLOSED/HALF_OPEN/OPEN)
- Retry logic with exponential backoff
- Health checks and observability
- API server with SSE streaming
- Database connection pooling
- Security package (audit logging, secret management)

**Breaking Changes:**
- Config moved to `~/.config/ai-agent/config.toml`
- Session storage moved to `~/.config/friday/sessions/`

**Migration:** See [UPGRADE-v0.3.0.md](docs/UPGRADE-v0.3.0.md)

### v0.3.0

**Release Date:** January 2026

**Major Features:**
- Ralph-inspired autonomous development loop
- Session management (save, resume, checkpoint)
- Circuit breaker pattern
- Rate limiting (100 calls/hour)
- Dual-condition exit detection

### v0.2.0

**Release Date:** December 2025

**Major Features:**
- Session persistence
- Checkpoint system
- Enhanced Claude integration
- Agent/skill/workflow loading

### v0.1.0

**Release Date:** November 2025

**Initial Release:**
- 15+ built-in tools
- MCP support
- Rich TUI
- Security features
- Hook system

---

*Friday AI Teammate v1.0.0 - Operations Guide*
