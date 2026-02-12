"""Tests for MCP ecosystem."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from friday_ai.tools.mcp.mcp_registry import (
    MCP_SERVER_REGISTRY,
    get_server_info,
    list_servers_by_category,
    get_all_categories,
    search_servers,
    get_popular_servers,
    get_quick_install_servers,
)
from friday_ai.tools.mcp.mcp_installer import MCPInstaller, MCPServerManager


class TestMCPRegistry:
    """Test MCP server registry."""

    def test_get_server_info_exists(self):
        """Test getting info for existing server."""
        info = get_server_info("filesystem")
        assert info is not None
        assert info.name == "filesystem"
        assert "file" in info.description.lower()

    def test_get_server_info_not_exists(self):
        """Test getting info for non-existent server."""
        info = get_server_info("nonexistent")
        assert info is None

    def test_list_servers_by_category(self):
        """Test listing servers by category."""
        servers = list_servers_by_category("Database")
        assert len(servers) > 0
        for server in servers:
            assert server.category == "Database"

    def test_get_all_categories(self):
        """Test getting all categories."""
        categories = get_all_categories()
        assert len(categories) > 0
        assert "Database" in categories
        assert "Development" in categories

    def test_search_servers(self):
        """Test searching servers."""
        results = search_servers("postgres")
        assert len(results) > 0
        # Should find postgres server
        assert any("postgres" in s.name.lower() for s in results)

    def test_get_popular_servers(self):
        """Test getting popular servers."""
        servers = get_popular_servers(min_popularity=4)
        assert len(servers) > 0
        for server in servers:
            assert server.popularity >= 4

    def test_get_quick_install_servers(self):
        """Test getting servers without API keys."""
        servers = get_quick_install_servers()
        for server in servers:
            assert not server.requires_api_key


class TestMCPInstaller:
    """Test MCP installer."""

    @pytest.fixture
    def installer(self, tmp_path):
        return MCPInstaller(allowed_dirs=[str(tmp_path)])

    def test_installer_initialization(self, installer):
        """Test installer initialization."""
        assert installer is not None
        assert len(installer.allowed_dirs) > 0

    @pytest.mark.asyncio
    async def test_install_server_not_found(self, installer):
        """Test installing non-existent server."""
        result = await installer.install_server("nonexistent")
        assert result is False

    def test_get_install_status(self, installer):
        """Test getting install status."""
        assert installer.get_install_status("filesystem") is False


class TestMCPServerManager:
    """Test MCP server manager."""

    @pytest.fixture
    def manager(self):
        return MCPServerManager()

    def test_add_custom_server(self, manager):
        """Test adding custom server."""
        manager.add_custom_server(
            name="test-server",
            command="python",
            args=["-m", "test"],
            description="Test server",
        )

        config = manager.get_server_config("test-server")
        assert config is not None
        assert config["command"] == "python"

    def test_list_servers(self, manager):
        """Test listing all servers."""
        servers = manager.list_servers()
        assert len(servers) > 0
        # Should include registry servers
        assert any(s["name"] == "filesystem" for s in servers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
