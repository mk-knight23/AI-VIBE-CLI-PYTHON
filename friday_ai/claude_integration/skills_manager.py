"""Skills manager for .claude/skills/ directory.

Loads and manages skill definitions from skill directories,
supporting contextual activation based on file types and user intent.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from friday_ai.claude_integration.utils import load_markdown_file

logger = logging.getLogger(__name__)


@dataclass
class SkillDefinition:
    """Definition of a skill from .claude/skills/<name>/SKILL.md.

    Attributes:
        name: Unique identifier for the skill
        description: Short description of what the skill provides
        content: The full skill content (markdown)
        triggers: List of patterns that trigger this skill (file extensions, etc.)
        config: Optional configuration from config.json
        auto_activate: Whether to auto-activate based on triggers
        metadata: Additional fields from frontmatter
    """

    name: str
    description: str
    content: str
    triggers: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    auto_activate: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches_file(self, file_path: Path) -> bool:
        """Check if this skill matches a given file path.

        Args:
            file_path: The file to check against triggers.

        Returns:
            True if any trigger matches the file.
        """
        if not self.triggers:
            return False

        file_name = file_path.name
        file_ext = file_path.suffix.lstrip(".")
        file_path_str = str(file_path)

        for trigger in self.triggers:
            # Exact extension match
            if trigger.startswith(".") and file_name.endswith(trigger):
                return True
            # Extension without dot
            if file_ext == trigger:
                return True
            # Glob pattern
            if "*" in trigger:
                import fnmatch

                if fnmatch.fnmatch(file_name, trigger) or fnmatch.fnmatch(
                    file_path_str, trigger
                ):
                    return True
            # Substring match (for paths like "api/", "components/")
            if trigger in file_path_str:
                return True

        return False

    def format_for_prompt(self) -> str:
        """Format the skill content for system prompt injection."""
        lines = [f"# Skill: {self.name}"]
        if self.description:
            lines.append(f"*{self.description}*")
        lines.append("")
        lines.append(self.content)
        return "\n".join(lines)


class SkillsManager:
    """Manager for loading and activating skills from .claude/skills/."""

    def __init__(self, claude_dir: Path | None):
        """Initialize the skills manager.

        Args:
            claude_dir: Path to the .claude directory. If None, no skills will be loaded.
        """
        self.claude_dir = claude_dir
        self.skills_dir = claude_dir / "skills" if claude_dir else None
        self._skills: dict[str, SkillDefinition] = {}

    def load_all_skills(self) -> list[SkillDefinition]:
        """Load all skill definitions from the skills directory.

        Returns:
            List of loaded skill definitions.
        """
        if not self.skills_dir or not self.skills_dir.exists():
            logger.debug("No .claude/skills directory found")
            return []

        skills = []
        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            try:
                skill_def = self._load_skill(skill_dir)
                if skill_def:
                    skills.append(skill_def)
                    self._skills[skill_def.name] = skill_def
                    logger.debug(f"Loaded skill: {skill_def.name}")
            except Exception as e:
                logger.warning(f"Failed to load skill from {skill_dir}: {e}")
                continue

        return skills

    def _load_skill(self, skill_dir: Path) -> SkillDefinition | None:
        """Load a single skill from its directory.

        Args:
            skill_dir: Path to the skill directory.

        Returns:
            Loaded skill definition or None if loading failed.
        """
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return None

        # Load config.json if present
        config: dict[str, Any] = {}
        config_file = skill_dir / "config.json"
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load config.json for {skill_dir.name}: {e}")

        # Parse the SKILL.md file
        result = load_markdown_file(skill_file)
        if result is None:
            return None

        frontmatter, content = result

        # Get name from frontmatter or directory name
        name = frontmatter.get("name", skill_dir.name)

        # Get description
        description = frontmatter.get("description", "")

        # Get triggers from frontmatter or config
        triggers = frontmatter.get("triggers", [])
        if isinstance(triggers, str):
            triggers = [t.strip() for t in triggers.split(",") if t.strip()]
        if not triggers and "triggers" in config:
            triggers = config["triggers"]

        # Get auto-activate setting
        auto_activate = frontmatter.get("auto_activate", config.get("auto_activate", False))

        # Store extra fields in metadata
        known_fields = {"name", "description", "triggers", "auto_activate"}
        metadata = {k: v for k, v in frontmatter.items() if k not in known_fields}

        return SkillDefinition(
            name=name,
            description=description,
            content=content,
            triggers=triggers,
            config=config,
            auto_activate=auto_activate,
            metadata=metadata,
        )

    def get_skill(self, name: str) -> SkillDefinition | None:
        """Get a loaded skill by name.

        Args:
            name: The skill name.

        Returns:
            Skill definition if found, None otherwise.
        """
        return self._skills.get(name)

    def get_all_skills(self) -> list[SkillDefinition]:
        """Get all loaded skills.

        Returns:
            List of all skill definitions.
        """
        return list(self._skills.values())

    def get_relevant_skills(
        self,
        file_path: Path | None = None,
        file_extensions: list[str] | None = None,
        operation: str | None = None,
    ) -> list[SkillDefinition]:
        """Get skills relevant to the current context.

        Args:
            file_path: Optional file path to match against triggers.
            file_extensions: Optional file extensions to match.
            operation: Optional operation type (e.g., "testing", "refactoring").

        Returns:
            List of relevant skill definitions.
        """
        relevant = []

        for skill in self._skills.values():
            # Check if file path matches triggers
            if file_path and skill.matches_file(file_path):
                relevant.append(skill)
                continue

            # Check if any extension matches
            if file_extensions:
                for ext in file_extensions:
                    test_path = Path(f"test.{ext.lstrip('.')}")
                    if skill.matches_file(test_path):
                        relevant.append(skill)
                        break
                continue

            # Check if operation matches skill name or description
            if operation and (
                operation.lower() in skill.name.lower()
                or operation.lower() in skill.description.lower()
            ):
                relevant.append(skill)
                continue

            # Include auto-activate skills
            if skill.auto_activate:
                relevant.append(skill)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for skill in relevant:
            if skill.name not in seen:
                seen.add(skill.name)
                unique.append(skill)

        return unique

    def get_skills_for_prompt(
        self,
        active_skills: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Format skills for system prompt injection.

        Args:
            active_skills: List of skill names to include.
            context: Optional context dict with file_path, operation, etc.

        Returns:
            Formatted skills content for prompt.
        """
        skills_to_include = []

        # Add explicitly active skills
        if active_skills:
            for name in active_skills:
                skill = self._skills.get(name)
                if skill and skill not in skills_to_include:
                    skills_to_include.append(skill)

        # Add contextually relevant skills
        if context:
            file_path = context.get("file_path")
            operation = context.get("operation")
            extensions = context.get("file_extensions")

            relevant = self.get_relevant_skills(file_path, extensions, operation)
            for skill in relevant:
                if skill not in skills_to_include:
                    skills_to_include.append(skill)

        if not skills_to_include:
            return ""

        lines = ["# Relevant Skills and Patterns\n"]
        for skill in skills_to_include:
            lines.append(skill.format_for_prompt())
            lines.append("\n---\n")

        return "\n".join(lines)
