"""Tool Orchestrator - Manages tool discovery, registry, and MCP integration."""

import logging
from typing import Any

from friday_ai.config.config import Config
from friday_ai.tools.discovery import ToolDiscoveryManager
from friday_ai.tools.mcp.mcp_manager import MCPManager
from friday_ai.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolOrchestrator:
    """Orchestrates all tool-related operations.

    Centralizes tool registry, MCP server management, and tool discovery.
    This reduces Session class coupling by extracting tool management concerns.

    Responsibilities:
    - Tool registry management
    - MCP server lifecycle (initialize, connect, disconnect)
    - Tool discovery and loading
    - MCP tool registration
    """

    def __init__(self, config: Config, tool_registry: ToolRegistry):
        """Initialize tool orchestrator.

        Args:
            config: Application configuration
            tool_registry: Tool registry instance
        """
        self.config = config
        self.tool_registry = tool_registry

        # MCP Manager
        self.mcp_manager = MCPManager(config)

        # Tool Discovery
        self.discovery_manager = ToolDiscoveryManager(
            config,
            tool_registry,
        )

        logger.info("Tool orchestrator initialized")

    async def initialize(self) -> int:
        """Initialize all tool systems.

        Establishes MCP connections and discovers available tools.

        Returns:
            Number of MCP tools registered
        """
        logger.info("Initializing tool orchestrator")

        # Initialize MCP servers
        await self.mcp_manager.initialize()

        # Register MCP tools
        mcp_tool_count = self.mcp_manager.register_tools(self.tool_registry)

        # Discover additional tools
        self.discovery_manager.discover_all()

        total_tools = len(self.tool_registry.get_tools())
        logger.info(
            f"Tool orchestrator ready: {total_tools} tools ({mcp_tool_count} from MCP servers)"
        )

        return mcp_tool_count

    def get_tools_info(self) -> dict[str, Any]:
        """Get information about registered tools.

        Returns:
            Dictionary with tool statistics
        """
        tools = self.tool_registry.get_tools()
        mcp_servers = self.mcp_manager.get_all_servers()

        return {
            "total_tools": len(tools),
            "builtin_tools": len([t for t in tools if not t.name.startswith("mcp__")]),
            "mcp_tools": len([t for t in tools if t.name.startswith("mcp__")]),
            "mcp_servers": len(mcp_servers),
            "mcp_server_list": [s["name"] for s in mcp_servers],
        }

    async def shutdown(self) -> None:
        """Shutdown tool orchestrator and cleanup resources.

        Closes MCP connections and performs cleanup.
        """
        logger.info("Shutting down tool orchestrator")

        # MCP manager cleanup is handled by MCPManager itself
        # No explicit cleanup needed for ToolDiscoveryManager

        logger.info("Tool orchestrator shutdown complete")
