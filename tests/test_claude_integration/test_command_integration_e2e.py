"""End-to-end integration test for command execution with agents."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCommandIntegrationE2E:
    """End-to-end tests for command integration."""

    @pytest.mark.asyncio
    async def test_full_command_execution_flow(self):
        """Test complete flow from command file to subagent invocation."""
        from friday_ai.claude_integration import (
            ClaudeContext,
            CommandMapper,
        )
        from friday_ai.config.config import Config

        with tempfile.TemporaryDirectory() as tmp:
            # Setup .claude directory structure
            claude_dir = Path(tmp) / ".claude"
            commands_dir = claude_dir / "commands"
            commands_dir.mkdir(parents=True)

            # Create a command file
            cmd_file = commands_dir / "review.md"
            cmd_file.write_text("""---
description: Code review command
---

This command invokes `code-reviewer` agent.

## Usage

/review <file>
""")

            # Initialize mapper
            mapper = CommandMapper(claude_dir)
            mapper.load_all_commands()

            # Verify command loaded
            command = mapper.get_command("review")
            assert command is not None
            assert command.agent == "code-reviewer"
            assert command.description == "Code review command"

            # Create mock agent
            mock_agent = MagicMock()
            mock_agent.session = MagicMock()
            mock_agent.config = MagicMock()
            mock_agent.config.cwd = Path(tmp)

            # Mock tool registry
            mock_tool_registry = MagicMock()
            from friday_ai.tools.base import ToolResult

            mock_result = ToolResult.success_result(
                "Code review complete: No issues found"
            )
            mock_tool_registry.invoke = AsyncMock(return_value=mock_result)

            mock_agent.session.tool_registry = mock_tool_registry
            mock_agent.session.hook_system = MagicMock()
            mock_agent.session.approval_manager = MagicMock()

            # Execute command
            result = await mapper.execute_command(
                "review",
                "auth.py",
                mock_agent
            )

            # Verify subagent was invoked correctly
            mock_tool_registry.invoke.assert_called_once()
            call_args = mock_tool_registry.invoke.call_args

            assert call_args[0][0] == "subagent_code-reviewer"
            assert call_args[0][1]["goal"] == "Use the code-reviewer agent to help with:\n\nauth.py"
            assert call_args[0][2] == Path(tmp)
            assert result == "Code review complete: No issues found"

    @pytest.mark.asyncio
    async def test_command_with_no_agent(self):
        """Test command without agent reference works correctly."""
        from friday_ai.claude_integration import CommandMapper

        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            commands_dir = claude_dir / "commands"
            commands_dir.mkdir(parents=True)

            # Create command without agent
            cmd_file = commands_dir / "info.md"
            cmd_file.write_text("""---
description: Info command
---

Just displays information.
""")

            mapper = CommandMapper(claude_dir)
            mapper.load_all_commands()

            # Create mock agent
            mock_agent = MagicMock()

            # Execute command
            result = await mapper.execute_command(
                "info",
                "some info",
                mock_agent
            )

            # Should return help text (no agent to invoke)
            assert "Help with:" in result
            assert "some info" in result
