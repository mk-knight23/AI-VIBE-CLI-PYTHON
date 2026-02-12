"""MCP Server Registry - Known and popular MCP servers."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MCPServerInfo:
    """Information about a known MCP server."""

    name: str
    description: str
    command: str
    args: list[str]
    env_vars: dict[str, str]
    category: str
    popularity: int  # 1-5 stars
    requires_api_key: bool
    docs_url: Optional[str] = None
    repo_url: Optional[str] = None


# Registry of known MCP servers
MCP_SERVER_REGISTRY: dict[str, MCPServerInfo] = {
    "filesystem": MCPServerInfo(
        name="filesystem",
        description="Read, write, and edit files on disk",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
        env_vars={},
        category="File System",
        popularity=5,
        requires_api_key=False,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "github": MCPServerInfo(
        name="github",
        description="Interact with GitHub repositories, issues, PRs",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env_vars={"GITHUB_PERSONAL_ACCESS_TOKEN": "your-token"},
        category="Development",
        popularity=5,
        requires_api_key=True,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "postgres": MCPServerInfo(
        name="postgres",
        description="Query and interact with PostgreSQL databases",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost:5432/db"],
        env_vars={},
        category="Database",
        popularity=4,
        requires_api_key=False,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "redis": MCPServerInfo(
        name="redis",
        description="Interact with Redis key-value store",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-redis", "redis://localhost:6379"],
        env_vars={},
        category="Database",
        popularity=3,
        requires_api_key=False,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "slack": MCPServerInfo(
        name="slack",
        description="Send messages to Slack channels",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-slack"],
        env_vars={"SLACK_BOT_TOKEN": "xoxb-your-token"},
        category="Communication",
        popularity=4,
        requires_api_key=True,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "google-maps": MCPServerInfo(
        name="google-maps",
        description="Access Google Maps API for locations and directions",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-google-maps"],
        env_vars={"GOOGLE_MAPS_API_KEY": "your-api-key"},
        category="Services",
        popularity=3,
        requires_api_key=True,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "puppeteer": MCPServerInfo(
        name="puppeteer",
        description="Browser automation with Puppeteer",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-puppeteer"],
        env_vars={},
        category="Automation",
        popularity=4,
        requires_api_key=False,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "fetch": MCPServerInfo(
        name="fetch",
        description="Fetch web content and APIs",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-fetch"],
        env_vars={},
        category="Web",
        popularity=4,
        requires_api_key=False,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "memory": MCPServerInfo(
        name="memory",
        description="Knowledge graph memory storage",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
        env_vars={},
        category="Knowledge",
        popularity=3,
        requires_api_key=False,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "brave-search": MCPServerInfo(
        name="brave-search",
        description="Web search using Brave Search API",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env_vars={"BRAVE_API_KEY": "your-api-key"},
        category="Web",
        popularity=4,
        requires_api_key=True,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "sequential-thinking": MCPServerInfo(
        name="sequential-thinking",
        description="Sequential reasoning and problem solving",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
        env_vars={},
        category="Reasoning",
        popularity=3,
        requires_api_key=False,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "everything": MCPServerInfo(
        name="everything",
        description="Desktop search using Everything (Windows)",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-everything"],
        env_vars={},
        category="Search",
        popularity=3,
        requires_api_key=False,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "aws": MCPServerInfo(
        name="aws",
        description="Interact with AWS services",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-aws"],
        env_vars={"AWS_ACCESS_KEY_ID": "your-key", "AWS_SECRET_ACCESS_KEY": "your-secret"},
        category="Cloud",
        popularity=4,
        requires_api_key=True,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
    "gitlab": MCPServerInfo(
        name="gitlab",
        description="Interact with GitLab repositories",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-gitlab"],
        env_vars={"GITLAB_PERSONAL_ACCESS_TOKEN": "your-token"},
        category="Development",
        popularity=3,
        requires_api_key=True,
        docs_url="https://github.com/modelcontextprotocol/servers",
        repo_url="https://github.com/modelcontextprotocol/servers",
    ),
}


def get_server_info(name: str) -> Optional[MCPServerInfo]:
    """Get information about a known MCP server.

    Args:
        name: Server name.

    Returns:
        Server info or None if not found.
    """
    return MCP_SERVER_REGISTRY.get(name)


def list_servers_by_category(category: str) -> list[MCPServerInfo]:
    """List MCP servers by category.

    Args:
        category: Category name.

    Returns:
        List of servers in the category.
    """
    return [s for s in MCP_SERVER_REGISTRY.values() if s.category.lower() == category.lower()]


def get_all_categories() -> list[str]:
    """Get all available categories.

    Returns:
        List of category names.
    """
    return list(set(s.category for s in MCP_SERVER_REGISTRY.values()))


def search_servers(query: str) -> list[MCPServerInfo]:
    """Search for MCP servers by name or description.

    Args:
        query: Search query.

    Returns:
        List of matching servers.
    """
    query_lower = query.lower()
    return [
        s for s in MCP_SERVER_REGISTRY.values()
        if query_lower in s.name.lower() or query_lower in s.description.lower()
    ]


def get_popular_servers(min_popularity: int = 4) -> list[MCPServerInfo]:
    """Get popular MCP servers.

    Args:
        min_popularity: Minimum popularity rating.

    Returns:
        List of popular servers.
    """
    return [s for s in MCP_SERVER_REGISTRY.values() if s.popularity >= min_popularity]


def get_quick_install_servers() -> list[MCPServerInfo]:
    """Get servers that don't require API keys.

    Returns:
        List of servers without API key requirements.
    """
    return [s for s in MCP_SERVER_REGISTRY.values() if not s.requires_api_key]
