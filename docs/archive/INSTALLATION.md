# Installation Guide

Friday AI Teammate can be installed via PyPI or from source.

## Requirements

- Python 3.10 or higher
- pip (Python package installer)
- Git (for some tools)

## Installation Methods

### Method 1: PyPI (Recommended)

```bash
pip install friday-ai-teammate
```

Or with pip3:

```bash
pip3 install friday-ai-teammate
```

### Method 2: From Source

```bash
# Clone the repository
git clone https://github.com/mk-knight23/Friday.git
cd Friday

# Install in editable mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Method 3: Using requirements.txt

```bash
# Clone the repository
git clone https://github.com/mk-knight23/Friday.git
cd Friday

# Install from requirements.txt
pip install -r requirements.txt
```

## Configuration

### 1. Set API Key

Friday AI requires an API key for the LLM backend. You can use any OpenAI-compatible API.

#### Option A: Environment Variables (Recommended)

```bash
export API_KEY=your_api_key_here
export BASE_URL=https://api.openai.com/v1
```

Or for MiniMax:

```bash
export API_KEY=your_minimax_api_key
export BASE_URL=https://api.minimax.io/v1
```

#### Option B: .env File

Create a `.env` file in your working directory:

```env
API_KEY=your_api_key_here
BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4
```

Friday will automatically load environment variables from `.env` files.

### 2. Configuration File (Optional)

You can create a configuration file at:
- `~/.config/ai-agent/config.toml` (Linux/macOS)
- `%APPDATA%\ai-agent\config.toml` (Windows)

Example `config.toml`:

```toml
[model]
name = "gpt-4"
temperature = 0.7
max_tokens = 4096

[shell_environment]
allowed_commands = ["git", "npm", "python", "ls", "cat"]
blocked_commands = ["rm -rf", "sudo"]

[safety]
approval_mode = "on-request"
```

### 3. .claude Folder Integration (Optional)

Friday automatically discovers `.claude/` folders for enhanced functionality:

```
.claude/
├── agents/         # Sub-agent definitions
├── skills/         # Reusable patterns
├── rules/          # Coding standards
├── commands/       # Slash commands
└── workflows/      # Workflow templates
```

## Verification

### Test Installation

```bash
friday --help
```

You should see the help output with all available options.

### Run Basic Test

```bash
friday "Hello, can you help me?"
```

### Check Available Tools

```bash
friday
# Then type: /tools
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'pydantic'"

The dependencies weren't installed correctly. Reinstall:

```bash
pip install -r requirements.txt
```

### "API key not configured"

Make sure you've set the `API_KEY` environment variable or created a `.env` file.

### "Permission denied" error

Some shell commands may require approval. Check your approval mode:

```bash
friday
# Then type: /approval auto
```

### Git/Docker tools not working

Make sure git and docker are installed and available in your PATH:

```bash
which git
which docker
```

## Uninstallation

```bash
pip uninstall friday-ai-teammate
```

## Development Installation

For development with all dependencies:

```bash
git clone https://github.com/mk-knight23/Friday.git
cd Friday
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Next Steps

- Read the [User Guide](USER-GUIDE.md) for usage instructions
- Check the [Feature Guide](FEATURE-GUIDE.md) for all available features
- See [Best Practices](BEST-PRACTICES.md) for coding standards
- Review [Security](SECURITY.md) for safety features
