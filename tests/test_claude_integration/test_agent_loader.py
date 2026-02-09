"""Tests for agent_loader module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from friday_ai.claude_integration.agent_loader import (
    ClaudeAgentDefinition,
    ClaudeAgentLoader,
)


class TestClaudeAgentLoader:
    """Tests for ClaudeAgentLoader class."""

    def test_load_agent_with_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            agents_dir = claude_dir / "agents"
            agents_dir.mkdir(parents=True)

            agent_file = agents_dir / "test-agent.md"
            agent_file.write_text("""---
name: test-agent
description: A test agent
tools: [read_file, edit_file]
model: sonnet
max_turns: 10
timeout_seconds: 300
---

# Test Agent

You are a helpful test agent.
""")

            loader = ClaudeAgentLoader(claude_dir)
            agents = loader.load_all_agents()

            assert len(agents) == 1
            agent = agents[0]
            assert agent.name == "test-agent"
            assert agent.description == "A test agent"
            assert agent.tools == ["read_file", "edit_file"]
            assert agent.model == "sonnet"
            assert agent.max_turns == 10
            assert agent.timeout_seconds == 300
            assert "Test Agent" in agent.prompt_template

    def test_load_agent_from_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            agents_dir = claude_dir / "agents"
            agents_dir.mkdir(parents=True)

            agent_file = agents_dir / "custom-agent.md"
            agent_file.write_text("""---
description: Custom description
---

Content here.
""")

            loader = ClaudeAgentLoader(claude_dir)
            agents = loader.load_all_agents()

            assert len(agents) == 1
            assert agents[0].name == "custom-agent"  # From filename

    def test_tools_as_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            agents_dir = claude_dir / "agents"
            agents_dir.mkdir(parents=True)

            agent_file = agents_dir / "agent.md"
            agent_file.write_text("""---
tools: read_file, edit_file, grep
---

Content.
""")

            loader = ClaudeAgentLoader(claude_dir)
            agents = loader.load_all_agents()

            assert agents[0].tools == ["read_file", "edit_file", "grep"]

    def test_no_agents_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            loader = ClaudeAgentLoader(claude_dir)
            agents = loader.load_all_agents()

            assert agents == []

    def test_no_claude_dir(self):
        loader = ClaudeAgentLoader(None)
        agents = loader.load_all_agents()

        assert agents == []

    def test_get_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            agents_dir = claude_dir / "agents"
            agents_dir.mkdir(parents=True)

            agent_file = agents_dir / "my-agent.md"
            agent_file.write_text("""---
name: my-agent
---

Content.
""")

            loader = ClaudeAgentLoader(claude_dir)
            loader.load_all_agents()

            agent = loader.get_agent("my-agent")
            assert agent is not None
            assert agent.name == "my-agent"

            not_found = loader.get_agent("nonexistent")
            assert not_found is None


class TestConvertToSubagentDefinition:
    """Tests for convert_to_subagent_definition method."""

    def test_basic_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            agents_dir = claude_dir / "agents"
            agents_dir.mkdir(parents=True)

            agent_file = agents_dir / "test.md"
            agent_file.write_text("""---
name: test-agent
description: Test agent
tools: [read_file]
---

You are a test agent.
""")

            loader = ClaudeAgentLoader(claude_dir)
            agents = loader.load_all_agents()
            agent_def = agents[0]

            mock_config = MagicMock()
            mock_config.model_name = "test-model"

            subagent_def = loader.convert_to_subagent_definition(agent_def, mock_config)

            assert subagent_def.name == "test-agent"
            assert subagent_def.description == "Test agent"
            assert subagent_def.allowed_tools == ["read_file"]
            assert "You are a test agent" in subagent_def.goal_prompt
