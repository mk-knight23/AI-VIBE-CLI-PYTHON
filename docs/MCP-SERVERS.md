# MCP Servers Installation Guide

This document describes the MCP (Model Context Protocol) servers installed for Friday AI Teammate.

---

## Installed MCP Servers

### 1. Brave Search MCP Server

**Package:** `@brave/brave-search-mcp-server` v2.0.72

**Purpose:** Fast web search with Brave Search API

**Features:**
- Web search results
- Image search
- Video search
- Rich results
- AI summaries

**Installation:**
```bash
npm install -g @brave/brave-search-mcp-server
```

**API Key:** Optional - works without API key but with limitations
- Get free API key at: https://brave.com/search/api/

**Usage in Friday:**
```toml
[mcp_servers.brave-search]
command = "brave-search-mcp-server"
args = []
enabled = true
```

**Tools Provided:**
- `brave_web_search` - Search the web
- `brave_search_images` - Search for images
- `brave_search_videos` - Search for videos
- `brave_search_news` - Search news
- `brave_summarize` - Get AI summaries

---

### 2. Web Reader MCP Server

**Package:** `mcp-web-reader` v2.1.0

**Purpose:** Read web content with Jina Reader and local parser support

**Features:**
- Jina Reader integration for clean content extraction
- Local HTML parser fallback
- Metadata extraction
- Full content retrieval

**Installation:**
```bash
npm install -g mcp-web-reader
```

**Usage in Friday:**
```toml
[mcp_servers.web-reader]
command = "mcp-web-reader"
args = []
enabled = true
```

**Tools Provided:**
- `read_webpage` - Read a webpage and extract content
- `fetch_url` - Fetch URL with metadata
- `extract_markdown` - Extract content as markdown

---

### 3. GitHub MCP Server (Official - Deprecated)

**Package:** `@modelcontextprotocol/server-github` v2025.4.8

**⚠️ Status:** Deprecated but still functional

**Purpose:** Interrogate GitHub repositories for docs, structure, and files

**Features:**
- Repository file listing
- File content retrieval
- Repository search
- Issue and PR access
- Branch and tag management

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-github
```

**Usage in Friday:**
```toml
[mcp_servers.github]
command = "npx"
args = ["@modelcontextprotocol/server-github"]
enabled = true
```

**Tools Provided:**
- `github_get_file` - Get file contents
- `github_search_repositories` - Search repos
- `github_list_files` - List directory contents
- `github_create_issue` - Create GitHub issues
- `github_create_pr` - Create pull requests

**Authentication:**
Requires GitHub token for private repos:
```bash
export GITHUB_TOKEN=your_token_here
```

---

## Configuration

All MCP servers are configured in: `~/.config/ai-agent/config.toml`

```toml
# MCP Servers Configuration
[mcp_servers.brave-search]
command = "brave-search-mcp-server"
args = []
enabled = true

[mcp_servers.web-reader]
command = "mcp-web-reader"
args = []
enabled = true

[mcp_servers.github]
command = "npx"
args = ["@modelcontextprotocol/server-github"]
enabled = true
```

---

## Usage Examples

### Web Search with Friday

```bash
friday
> Search for "Python async best practices" using brave search
> Read the top result and summarize key points
```

### Web Reading with Friday

```bash
friday
> Read https://example.com/article and extract the main content
> Fetch this documentation page and convert to markdown
```

### GitHub Repository Analysis

```bash
friday
> List the files in the src/ directory of facebook/react
> Get the README from vercel/next.js
> Search for repositories matching "python async framework"
```

---

## Troubleshooting

### MCP Server Not Starting

**Check if command is available:**
```bash
which brave-search-mcp-server
which mcp-web-reader
npx @modelcontextprotocol/server-github --help
```

**Check Friday logs:**
```bash
friday
> /mcp  # Shows MCP server status
```

### GitHub Authentication Issues

**Set token:**
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

**Or in .env:**
```env
GITHUB_TOKEN=ghp_your_token_here
```

### Brave Search API Key

**Optional but recommended for better results:**
1. Go to https://brave.com/search/api/
2. Sign up for free tier
3. Get API key
4. Add to config:

```toml
[mcp_servers.brave-search]
command = "brave-search-mcp-server"
args = ["--brave-api-key", "YOUR_API_KEY"]
enabled = true
```

---

## Alternative MCP Servers

If the official GitHub server becomes unavailable, consider:

### @ama-mcp/github

**Package:** `@ama-mcp/github` v13.5.4

**Installation:**
```bash
npm install -g @ama-mcp/github
```

**Note:** Requires Node 20/22/24 (may have warnings on Node 25)

---

## Verification

Test MCP servers are working:

```bash
# Test brave search
brave-search-mcp-server --help

# Test web reader  
mcp-web-reader --help

# Test GitHub server
npx @modelcontextprotocol/server-github --help
```

---

## Resources

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Brave Search API](https://brave.com/search/api/)
- [Jina Reader](https://jina.ai/reader)
- [GitHub API](https://docs.github.com/en/rest)

---

*Last Updated: February 2026*
