"""Tests for context module."""

import tempfile
from pathlib import Path

import pytest

from friday_ai.claude_integration.context import ClaudeContext
from friday_ai.claude_integration.skills_manager import SkillDefinition
from friday_ai.claude_integration.rules_engine import RuleSet


class TestClaudeContext:
    """Tests for ClaudeContext class."""

    def test_create_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            ctx = ClaudeContext(claude_dir=claude_dir)

            assert ctx.claude_dir == claude_dir
            assert ctx.agents == {}
            assert ctx.skills == {}
            assert ctx.active_skills == []

    def test_activate_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            ctx = ClaudeContext(claude_dir=claude_dir)
            ctx.skills["test-skill"] = SkillDefinition(
                name="test-skill",
                description="Test",
                content="Content"
            )

            result = ctx.activate_skill("test-skill")
            assert result is True
            assert "test-skill" in ctx.active_skills

            # Already active
            result2 = ctx.activate_skill("test-skill")
            assert result2 is False  # Already in list

            # Nonexistent
            result3 = ctx.activate_skill("nonexistent")
            assert result3 is False

    def test_deactivate_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            ctx = ClaudeContext(claude_dir=claude_dir)
            ctx.skills["test"] = SkillDefinition(name="test", description="T", content="C")
            ctx.activate_skill("test")

            result = ctx.deactivate_skill("test")
            assert result is True
            assert "test" not in ctx.active_skills

            result2 = ctx.deactivate_skill("test")
            assert result2 is False  # Not active

    def test_get_active_skill_definitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            ctx = ClaudeContext(claude_dir=claude_dir)
            skill = SkillDefinition(name="test", description="T", content="C")
            ctx.skills["test"] = skill
            ctx.activate_skill("test")

            active = ctx.get_active_skill_definitions()
            assert len(active) == 1
            assert active[0].name == "test"

    def test_format_skills_for_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            ctx = ClaudeContext(claude_dir=claude_dir)
            ctx.skills["test"] = SkillDefinition(
                name="test",
                description="Test skill",
                content="Skill content here"
            )
            ctx.activate_skill("test")

            formatted = ctx.format_skills_for_prompt()
            assert "# Relevant Skills and Patterns" in formatted
            assert "test" in formatted
            assert "Skill content here" in formatted

    def test_format_rules_for_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            ctx = ClaudeContext(claude_dir=claude_dir)
            ctx.rules = [
                RuleSet(name="Rule1", category="style", content="Be consistent")
            ]
            ctx.active_rules = ["Rule1"]

            formatted = ctx.format_rules_for_prompt()
            assert "# Coding Standards and Rules" in formatted
            assert "Be consistent" in formatted

    def test_get_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            from friday_ai.claude_integration.command_mapper import SlashCommand

            ctx = ClaudeContext(claude_dir=claude_dir)
            cmd = SlashCommand(name="test", description="Test cmd")
            ctx.commands["test"] = cmd

            found = ctx.get_command("test")
            assert found == cmd

            with_slash = ctx.get_command("/test")
            assert with_slash == cmd

            not_found = ctx.get_command("nonexistent")
            assert not_found is None
