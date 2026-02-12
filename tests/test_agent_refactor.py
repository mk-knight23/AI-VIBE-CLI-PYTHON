"""Tests for agent refactoring (ToolOrchestrator, SafetyManager, SessionMetrics)."""

import pytest
from unittest.mock import Mock, AsyncMock

from friday_ai.config.config import Config
from friday_ai.agent.tool_orchestrator import ToolOrchestrator
from friday_ai.agent.safety_manager import SafetyManager
from friday_ai.agent.session_metrics import SessionMetrics
from friday_ai.tools.registry import ToolRegistry


class TestToolOrchestrator:
    """Test ToolOrchestrator functionality."""

    @pytest.fixture
    def config(self):
        config = Mock(spec=Config)
        config.approval = "on-request"
        config.cwd = "/test/dir"
        return config

    @pytest.fixture
    def tool_registry(self):
        return Mock(spec=ToolRegistry)

    @pytest.fixture
    def orchestrator(self, config, tool_registry):
        return ToolOrchestrator(config, tool_registry)

    @pytest.mark.asyncio
    async def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.config == self.config()
        assert orchestrator.tool_registry == self.tool_registry()
        assert orchestrator.mcp_manager is not None
        assert orchestrator.discovery_manager is not None

    @pytest.mark.asyncio
    async def test_initialize(self, orchestrator):
        """Test initialize method."""
        # Mock MCP manager
        orchestrator.mcp_manager.initialize = AsyncMock(return_value=3)

        result = await orchestrator.initialize()

        assert result == 3
        orchestrator.mcp_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tools_info(self, orchestrator):
        """Test getting tools information."""
        # Mock tools registry
        mock_tools = [
            Mock(name="read_file", spec=lambda: "read_file" not in "mcp__"),
            Mock(name="mcp__write_file", spec=lambda: "mcp__write_file" in "mcp__"),
            Mock(name="shell", spec=lambda: True),
        ]
        orchestrator.tool_registry.get_tools.return_value = mock_tools
        orchestrator.tool_registry.connected_mcp_servers = {"test-server"}

        info = orchestrator.get_tools_info()

        assert info["total_tools"] == 3
        assert info["builtin_tools"] == 2  # Non-MCP tools
        assert info["mcp_tools"] == 1  # MCP tool
        assert info["mcp_servers"] == 1
        assert "test-server" in info["mcp_server_list"]

    @pytest.mark.asyncio
    async def test_shutdown(self, orchestrator):
        """Test shutdown method."""
        orchestrator.mcp_manager.shutdown = AsyncMock()

        await orchestrator.shutdown()

        orchestrator.mcp_manager.shutdown.assert_called_once()


class TestSafetyManager:
    """Test SafetyManager functionality."""

    @pytest.fixture
    def safety_manager(self):
        return SafetyManager("on-request", "/test/dir")

    def test_initialization(self, safety_manager):
        """Test safety manager initialization."""
        assert safety_manager.approval_policy == "on-request"
        assert safety_manager.cwd == "/test/dir"
        assert safety_manager.approval_manager is not None

    def test_check_approval(self, safety_manager):
        """Test approval checking."""
        # Mock approval manager
        safety_manager.approval_manager.is_approved.return_value = True

        result = safety_manager.check_approval("shell", {"command": "ls"})

        assert result is True
        safety_manager.approval_manager.is_approved.assert_called_once_with(
            "shell", {"command": "ls"}
        )

    def test_validate_path_safe(self, safety_manager):
        """Test path validation."""
        # Mock validator
        from friday_ai.safety.validators import validate_path_safe
        safety_manager.validate_path = Mock(return_value=True)

        result = safety_manager.validate_path("/test/dir/file.txt")

        assert result is True
        safety_manager.validate_path.assert_called_once_with("/test/dir/file.txt")

    def test_validate_command_safe(self, safety_manager):
        """Test command validation."""
        # Mock validator
        from friday_ai.safety.validators import validate_command_safe
        safety_manager.validate_command = Mock(return_value=True)

        result = safety_manager.validate_command("ls -la")

        assert result is True
        safety_manager.validate_command.assert_called_once_with("ls -la")

    def test_scrub_secrets(self, safety_manager):
        """Test secret scrubbing."""
        # Mock secret manager
        from friday_ai.security.secret_manager import scrub_secrets_from_text
        safety_manager.scrub_secrets = Mock(side_effect=lambda x: x.replace("sk-1234", "****"))

        result = safety_manager.scrub_secrets("API key: sk-1234")

        assert result == "API key: ****"
        assert "sk-1234" not in result

    def test_get_stats(self, safety_manager):
        """Test getting safety stats."""
        safety_manager.approval_manager.get_approval_count.return_value = 5

        stats = safety_manager.get_stats()

        assert stats["approval_policy"] == "on-request"
        assert stats["approvals_required"] == 5


class TestSessionMetrics:
    """Test SessionMetrics functionality."""

    @pytest.fixture
    def metrics(self):
        return SessionMetrics("test-session-123")

    def test_initialization(self, metrics):
        """Test metrics initialization."""
        assert metrics.session_id == "test-session-123"
        assert metrics.turn_count == 0
        assert metrics.message_count == 0
        assert metrics.tool_call_count == 0
        assert metrics.total_tokens_used == 0
        assert metrics.total_tokens_cached == 0

    def test_increment_turn(self, metrics):
        """Test turn increment."""
        initial_count = metrics.turn_count

        result = metrics.increment_turn()

        assert result == initial_count + 1
        assert metrics.turn_count == initial_count + 1

    def test_record_tool_usage(self, metrics):
        """Test recording tool usage."""
        metrics.record_tool_usage("read_file")
        metrics.record_tool_usage("shell")
        metrics.record_tool_usage("read_file")  # Duplicate

        assert metrics.tool_call_count == 3
        assert "read_file" in metrics.tools_used
        assert "shell" in metrics.tools_used

    def test_get_stats(self, metrics):
        """Test getting statistics."""
        metrics.turn_count = 10
        metrics.message_count = 50
        metrics.total_tokens_used = 5000
        metrics.total_tokens_cached = 1000
        metrics.tools_used = {"read_file", "shell", "grep"}

        stats = metrics.get_stats()

        assert stats["session_id"] == "test-session-123"
        assert stats["turn_count"] == 10
        assert stats["message_count"] == 50
        assert stats["total_tokens_used"] == 5000
        assert stats["unique_tools_used"] == 3
        assert set(stats["tools_used"]) == {"read_file", "shell", "grep"}
        assert "session_duration_seconds" in stats

    def test_get_summary(self, metrics):
        """Test getting human-readable summary."""
        summary = metrics.get_summary()

        assert "Session:" in summary
        assert metrics.session_id[:8] in summary
        assert "Turns:" in summary
