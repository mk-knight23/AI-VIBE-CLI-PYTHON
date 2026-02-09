"""Tests for command_mapper module."""

import tempfile
from pathlib import Path

import pytest

from friday_ai.claude_integration.command_mapper import (
    CommandMapper,
    SlashCommand,
)


class TestCommandMapper:
    """Tests for CommandMapper class."""

    def test_load_command_with_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            commands_dir = claude_dir / "commands"
            commands_dir.mkdir(parents=True)

            cmd_file = commands_dir / "tdd.md"
            cmd_file.write_text("""---
description: Test-driven development command
aliases: test, tests
---

# TDD Command

This command invokes the `tdd-guide` agent.

## Usage

/tdd <feature description>
""")

            mapper = CommandMapper(claude_dir)
            commands = mapper.load_all_commands()

            assert len(commands) == 1
            cmd = commands[0]
            assert cmd.name == "tdd"
            assert cmd.description == "Test-driven development command"
            assert cmd.agent == "tdd-guide"
            assert cmd.aliases == ["test", "tests"]

    def test_get_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            commands_dir = claude_dir / "commands"
            commands_dir.mkdir(parents=True)

            cmd_file = commands_dir / "my-cmd.md"
            cmd_file.write_text("""---
description: My command
---

Content.
""")

            mapper = CommandMapper(claude_dir)
            mapper.load_all_commands()

            found = mapper.get_command("my-cmd")
            assert found is not None
            assert found.name == "my-cmd"

            with_slash = mapper.get_command("/my-cmd")
            assert with_slash is not None

            not_found = mapper.get_command("nonexistent")
            assert not_found is None

    def test_alias_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            commands_dir = claude_dir / "commands"
            commands_dir.mkdir(parents=True)

            cmd_file = commands_dir / "main.md"
            cmd_file.write_text("""---
description: Main command
aliases: m, primary
---

Content.
""")

            mapper = CommandMapper(claude_dir)
            mapper.load_all_commands()

            found = mapper.get_command("m")
            assert found is not None
            assert found.name == "main"

    def test_build_prompt(self):
        cmd = SlashCommand(
            name="test",
            description="Test cmd",
            agent="test-agent",
            prompt_template="Help with: {args}"
        )

        prompt = cmd.build_prompt("something")
        assert prompt == "Help with: something"

        no_template = SlashCommand(
            name="simple",
            description="Simple cmd",
            agent="simple-agent"
        )
        simple_prompt = no_template.build_prompt("task")
        assert "simple-agent" in simple_prompt
        assert "task" in simple_prompt

    def test_list_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            commands_dir = claude_dir / "commands"
            commands_dir.mkdir(parents=True)

            (commands_dir / "cmd1.md").write_text("---\ndescription: Cmd 1\n---\n")
            (commands_dir / "cmd2.md").write_text("---\ndescription: Cmd 2\n---\n")

            mapper = CommandMapper(claude_dir)
            mapper.load_all_commands()

            commands = mapper.list_commands()
            assert len(commands) == 2


class TestSlashCommand:
    """Tests for SlashCommand dataclass."""

    def test_full_command(self):
        cmd = SlashCommand(name="test", description="Test")
        assert cmd.full_command == "/test"

    def test_build_prompt_with_template(self):
        cmd = SlashCommand(
            name="test",
            description="Test",
            prompt_template="Process: {args}"
        )
        assert cmd.build_prompt("input") == "Process: input"

    def test_build_prompt_without_placeholder(self):
        cmd = SlashCommand(
            name="test",
            description="Test",
            prompt_template="Base prompt"
        )
        result = cmd.build_prompt("extra")
        assert "Base prompt" in result
        assert "extra" in result
