# Friday AI Teammate

[![PyPI version](https://badge.fury.io/py/friday-ai-teammate.svg)](https://pypi.org/project/friday-ai-teammate/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Friday is a powerful AI assistant designed to help you with coding tasks, file management, and information retrieval directly from your terminal.

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

Friday comes equipped with a suite of tools:

| Category | Tools |
|----------|-------|
| **File System** | `read_file`, `write_file`, `edit_file`, `list_dir`, `glob` |
| **Search** | `grep` for pattern matching |
| **Shell** | `shell` to execute system commands safely |
| **Web** | `web_search` and `web_fetch` |
| **Memory** | `memory` to store and retrieve context |
| **Tasks** | `todos` to manage work lists |

## Security Features

- **Secret Scrubbing**: Automatically masks sensitive information (API keys, passwords) in tool outputs
- **Approval Policies**: Configure how the agent asks for permission before executing dangerous commands (`/approval`)
- **Path Validation**: Operations are restricted to allowed directories to protect your system

## Development

### From Source
```bash
git clone https://github.com/mk-knight23/Friday.git
cd Friday
pip install -e ".[dev]"
```

### Running Tests
```bash
pytest tests/ -v
```

## License

MIT
