# Friday AI Agent

Friday is a powerful AI assistant designed to help you with coding tasks, file management, and information retrieval directly from your terminal.

## Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- An API Key (e.g., from MiniMax or OpenRouter)

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/mk-knight23/Friday.git
cd Friday
pip install -r requirements.txt
```

### 3. Setup Global Command
To run `friday` from any directory, you can create a symbolic link (replace `/path/to/Friday` with your actual path):
```bash
chmod +x /path/to/Friday/friday
sudo ln -s /path/to/Friday/friday /usr/local/bin/friday
```

### 4. Configuration
Friday uses environment variables for configuration. The easiest way is to use a `.env` file:
```bash
cp .env.example .env
```
Open `.env` and add your API key:
```env
API_KEY=your_sk_...
BASE_URL=https://api.minimax.io/v1
```

## Usage

### Interactive Mode
Launch the interactive shell by simply typing:
```bash
friday
```

### Single Prompt
Run a specific task without entering interactive mode:
```bash
friday "Scan the current directory for security risks"
```

### Options
- `-c, --cwd DIRECTORY`: Set the working directory for the agent.
- `--help`: Show available options.

## Built-in Tools
Friday comes equipped with a suite of tools:
- **File System**: `read_file`, `write_file`, `edit_file`, `list_dir`, `glob`
- **Search**: `grep` for pattern matching
- **Shell**: `shell` to execute system commands safely
- **Web**: `web_search` and `web_fetch`
- **Memory**: `memory` to store and retrieve context
- **Tasks**: `todos` to manage work lists

## Security Features
- **Secret Scrubbing**: Friday automatically masks sensitive information (API keys, passwords) in tool outputs based on configurable patterns.
- **Approval Policies**: You can configure how the agent asks for permission before executing dangerous commands (`/approval`).
- **Path Validation**: Operations are restricted to allowed directories to protect your system.

## Testing
Run the comprehensive test suite to ensure everything is working correctly:
```bash
python3 tests/test_all_tools.py
python3 tests/test_real_world.py
python3 tests/test_security.py
```

## License
MIT
