"""Tests for skills_manager module."""

import json
import tempfile
from pathlib import Path

import pytest

from friday_ai.claude_integration.skills_manager import SkillDefinition, SkillsManager


class TestSkillsManager:
    """Tests for SkillsManager class."""

    def test_load_skill_with_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            skills_dir = claude_dir / "test-skill"
            skills_dir.mkdir(parents=True)

            skill_file = skills_dir / "SKILL.md"
            skill_file.write_text("""---
name: test-skill
description: A test skill
triggers: [".ts", ".tsx"]
auto_activate: true
---

# Test Skill

This is a test skill content.
""")

            manager = SkillsManager(claude_dir)
            skills = manager.load_all_skills()

            assert len(skills) == 1
            skill = skills[0]
            assert skill.name == "test-skill"
            assert skill.description == "A test skill"
            assert skill.triggers == [".ts", ".tsx"]
            assert skill.auto_activate is True

    def test_load_skill_from_config_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            skills_dir = claude_dir / "my-skill"
            skills_dir.mkdir(parents=True)

            skill_file = skills_dir / "SKILL.md"
            skill_file.write_text("""---
name: my-skill
---

Content.
""")

            config_file = skills_dir / "config.json"
            config_file.write_text(json.dumps({
                "triggers": [".py"],
                "auto_activate": True
            }))

            manager = SkillsManager(claude_dir)
            skills = manager.load_all_skills()

            assert len(skills) == 1
            assert skills[0].triggers == [".py"]
            assert skills[0].auto_activate is True

    def test_matches_file(self):
        skill = SkillDefinition(
            name="test",
            description="Test",
            content="Content",
            triggers=[".ts", "*.tsx", "api/"]
        )

        assert skill.matches_file(Path("test.ts")) is True
        assert skill.matches_file(Path("test.tsx")) is True
        assert skill.matches_file(Path("src/api/routes.ts")) is True
        assert skill.matches_file(Path("test.py")) is False

    def test_get_relevant_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            skills_dir = claude_dir / "ts-skill"
            skills_dir.mkdir(parents=True)

            skill_file = skills_dir / "SKILL.md"
            skill_file.write_text("""---
name: ts-skill
triggers: [".ts"]
---

Content.
""")

            manager = SkillsManager(claude_dir)
            manager.load_all_skills()

            relevant = manager.get_relevant_skills(file_path=Path("test.ts"))
            assert len(relevant) == 1
            assert relevant[0].name == "ts-skill"

            not_relevant = manager.get_relevant_skills(file_path=Path("test.py"))
            assert len(not_relevant) == 0

    def test_format_for_prompt(self):
        skill = SkillDefinition(
            name="my-skill",
            description="My skill",
            content="# Skill Content\n\nInstructions here."
        )

        formatted = skill.format_for_prompt()
        assert "# Skill: my-skill" in formatted
        assert "My skill" in formatted
        assert "# Skill Content" in formatted
