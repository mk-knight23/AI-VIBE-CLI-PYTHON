"""Friday AI Tools MCP module."""

# Import from the mcp package (not tools/mcp)
from friday_ai.mcp.server import MCPServer, TransportType, start_mcp_server
from friday_ai.tools.mcp.client import MCPClient, MCPServerStatus, MCPToolInfo
from friday_ai.tools.mcp.mcp_manager import MCPManager
from friday_ai.tools.mcp.mcp_tool import MCPTool
from friday_ai.tools.mcp.mcp_registry import (
    MCPServerInfo,
    MCP_SERVER_REGISTRY,
    get_server_info,
    list_servers_by_category,
    get_all_categories,
    search_servers,
    get_popular_servers,
    get_quick_install_servers,
)
from friday_ai.tools.mcp.mcp_installer import (
    MCPInstaller,
    MCPServerManager,
)

__all__ = [
    # Server
    "MCPServer",
    "TransportType",
    "start_mcp_server",
    # Client
    "MCPClient",
    "MCPServerStatus",
    "MCPToolInfo",
    # Manager
    "MCPManager",
    "MCPTool",
    # Registry
    "MCPServerInfo",
    "MCP_SERVER_REGISTRY",
    "get_server_info",
    "list_servers_by_category",
    "get_all_categories",
    "search_servers",
    "get_popular_servers",
    "get_quick_install_servers",
    # Installer
    "MCPInstaller",
    "MCPServerManager",
]
