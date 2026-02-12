"""MCP Server Installer - Auto-install and configure MCP servers."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
import logging

from friday_ai.tools.mcp.mcp_registry import MCPServerInfo, MCP_SERVER_REGISTRY, get_server_info

logger = logging.getLogger(__name__)


class MCPInstaller:
    """Installer for MCP servers."""

    def __init__(self, allowed_dirs: Optional[list[str]] = None):
        """Initialize the installer.

        Args:
            allowed_dirs: List of allowed directories for MCP servers.
        """
        self.allowed_dirs = allowed_dirs or [str(Path.cwd())]
        self._install_cache: dict[str, bool] = {}

    async def install_server(
        self,
        server_name: str,
        install_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
    ) -> bool:
        """Install and configure an MCP server.

        Args:
            server_name: Name of the server to install.
            install_dir: Directory to install the server config.
            api_key: API key for servers requiring authentication.
            extra_args: Additional arguments for the server.

        Returns:
            True if installation was successful.
        """
        server_info = get_server_info(server_name)
        if server_info is None:
            logger.error(f"Unknown MCP server: {server_name}")
            return False

        logger.info(f"Installing MCP server: {server_name}")

        # Check if npx is available
        if server_info.command == "npx":
            if not await self._check_command("npx"):
                logger.error("npx is not installed. Please install Node.js first.")
                return False

        # Create install directory
        if install_dir is None:
            install_dir = self.allowed_dirs[0]

        install_path = Path(install_dir) / ".friday" / "mcp" / server_name
        install_path.mkdir(parents=True, exist_ok=True)

        # Generate server configuration
        config = await self._generate_config(
            server_info,
            str(install_path),
            api_key,
            extra_args,
        )

        # Write configuration
        config_path = install_path / "server.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"MCP server {server_name} installed at {config_path}")
        self._install_cache[server_name] = True

        return True

    async def _generate_config(
        self,
        server_info: MCPServerInfo,
        install_dir: str,
        api_key: Optional[str],
        extra_args: Optional[list[str]],
    ) -> dict:
        """Generate MCP server configuration.

        Args:
            server_info: Server information.
            install_dir: Installation directory.
            api_key: API key for authentication.
            extra_args: Additional arguments.

        Returns:
            Configuration dictionary.
        """
        # Build command args
        args = list(server_info.args)

        # Replace placeholder paths
        args = [arg.replace("/path/to/dir", install_dir) for arg in args]

        # Add extra args
        if extra_args:
            args.extend(extra_args)

        # Build environment variables
        env_vars = dict(server_info.env_vars)
        if api_key:
            for key in env_vars:
                if "TOKEN" in key or "KEY" in key:
                    env_vars[key] = api_key

        # Add PATH for npx
        env_vars["PATH"] = os.environ.get("PATH", "")

        config = {
            "name": server_info.name,
            "command": server_info.command,
            "args": args,
            "env": env_vars,
            "description": server_info.description,
            "category": server_info.category,
        }

        return config

    async def _check_command(self, command: str) -> bool:
        """Check if a command is available.

        Args:
            command: Command to check.

        Returns:
            True if command is available.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                command,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except FileNotFoundError:
            return False

    async def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server.

        Args:
            server_name: Name of the server to remove.

        Returns:
            True if removal was successful.
        """
        server_info = get_server_info(server_name)
        if server_info is None:
            logger.error(f"Unknown MCP server: {server_name}")
            return False

        # Remove from install cache
        if server_name in self._install_cache:
            del self._install_cache[server_name]

        logger.info(f"MCP server {server_name} removed from registry")
        return True

    def get_install_status(self, server_name: str) -> bool:
        """Check if a server is installed.

        Args:
            server_name: Name of the server.

        Returns:
            True if installed.
        """
        return self._install_cache.get(server_name, False)

    async def install_recommended_servers(
        self,
        categories: Optional[list[str]] = None,
    ) -> dict[str, bool]:
        """Install recommended MCP servers.

        Args:
            categories: Categories to install from. If None, installs popular servers.

        Returns:
            Dictionary of server names to installation status.
        """
        results = {}

        if categories:
            for category in categories:
                servers = [
                    s for s in MCP_SERVER_REGISTRY.values()
                    if s.category.lower() == category.lower()
                ]
                for server in servers:
                    results[server.name] = await self.install_server(server.name)
        else:
            # Install popular servers
            popular = [s for s in MCP_SERVER_REGISTRY.values() if s.popularity >= 4]
            for server in popular:
                results[server.name] = await self.install_server(server.name)

        return results

    def generate_config_template(self, server_name: str) -> dict:
        """Generate a configuration template for an MCP server.

        Args:
            server_name: Name of the server.

        Returns:
            Configuration template dictionary.
        """
        server_info = get_server_info(server_name)
        if server_info is None:
            return {}

        template = {
            "mcp_servers": {
                server_name: {
                    "command": server_info.command,
                    "args": server_info.args,
                    "env": {key: f"<{key}>" for key in server_info.env_vars},
                }
            }
        }

        return template


class MCPServerManager:
    """Manager for MCP server lifecycle."""

    def __init__(self):
        """Initialize the server manager."""
        self.installer = MCPInstaller()
        self._servers: dict[str, dict] = {}

    def add_custom_server(
        self,
        name: str,
        command: str,
        args: list[str],
        env: Optional[dict[str, str]] = None,
        description: Optional[str] = None,
    ) -> None:
        """Add a custom MCP server.

        Args:
            name: Server name.
            command: Command to run.
            args: Command arguments.
            env: Environment variables.
            description: Server description.
        """
        self._servers[name] = {
            "command": command,
            "args": args,
            "env": env or {},
            "description": description or f"Custom MCP server: {name}",
            "custom": True,
        }

    def remove_server(self, name: str) -> bool:
        """Remove a custom MCP server.

        Args:
            name: Server name.

        Returns:
            True if removed.
        """
        if name in self._servers:
            del self._servers[name]
            return True
        return False

    def list_servers(self) -> list[dict]:
        """List all configured MCP servers.

        Returns:
            List of server configurations.
        """
        servers = []

        # Add registry servers
        for name, info in MCP_SERVER_REGISTRY.items():
            servers.append({
                "name": name,
                "description": info.description,
                "category": info.category,
                "popularity": info.popularity,
                "requires_api_key": info.requires_api_key,
                "custom": False,
            })

        # Add custom servers
        for name, config in self._servers.items():
            servers.append({
                "name": name,
                "description": config.get("description", ""),
                "category": "Custom",
                "popularity": 0,
                "requires_api_key": bool(config.get("env", {})),
                "custom": True,
            })

        return servers

    def get_server_config(self, name: str) -> Optional[dict]:
        """Get configuration for a specific server.

        Args:
            name: Server name.

        Returns:
            Server configuration or None.
        """
        # Check custom servers first
        if name in self._servers:
            return self._servers[name]

        # Check registry
        info = get_server_info(name)
        if info:
            return {
                "command": info.command,
                "args": info.args,
                "env": info.env_vars,
                "description": info.description,
            }

        return None
