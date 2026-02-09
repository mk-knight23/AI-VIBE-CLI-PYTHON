"""Context management for .claude folder integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from friday_ai.claude_integration.agent_loader import ClaudeAgentDefinition
    from friday_ai.claude_integration.command_mapper import SlashCommand
    from friday_ai.claude_integration.rules_engine import RuleSet
    from friday_ai.claude_integration.skills_manager import SkillDefinition
    from friday_ai.claude_integration.workflow_engine import WorkflowDefinition


@dataclass
class ClaudeContext:
    """Aggregates all .claude folder content for a session.

    This class holds references to all loaded .claude resources that should
    be considered when building system prompts and executing commands.
    """

    # Source directory
    claude_dir: Path

    # Loaded resources
    agents: dict[str, "ClaudeAgentDefinition"] = field(default_factory=dict)
    skills: dict[str, "SkillDefinition"] = field(default_factory=dict)
    rules: list["RuleSet"] = field(default_factory=list)
    workflows: dict[str, "WorkflowDefinition"] = field(default_factory=dict)
    commands: dict[str, "SlashCommand"] = field(default_factory=dict)

    # Active/selected resources for current context
    active_skills: list[str] = field(default_factory=list)
    active_rules: list[str] = field(default_factory=list)

    def get_active_skill_definitions(self) -> list["SkillDefinition"]:
        """Get definitions for currently active skills."""
        return [
            self.skills[name]
            for name in self.active_skills
            if name in self.skills
        ]

    def get_active_rule_definitions(self) -> list["RuleSet"]:
        """Get definitions for currently active rules."""
        active_set = set(self.active_rules)
        return [r for r in self.rules if r.name in active_set]

    def get_relevant_rules_for_file(self, file_path: Path) -> list["RuleSet"]:
        """Get rules relevant to a specific file."""
        from friday_ai.claude_integration.rules_engine import RulesEngine

        return RulesEngine(self.claude_dir).get_rules_for_context(
            file_path=file_path
        )

    def activate_skill(self, skill_name: str) -> bool:
        """Activate a skill by name.

        Returns:
            True if skill was found and activated, False otherwise.
        """
        if skill_name in self.skills and skill_name not in self.active_skills:
            self.active_skills.append(skill_name)
            return True
        return False

    def deactivate_skill(self, skill_name: str) -> bool:
        """Deactivate a skill by name.

        Returns:
            True if skill was deactivated, False if not active.
        """
        if skill_name in self.active_skills:
            self.active_skills.remove(skill_name)
            return True
        return False

    def format_skills_for_prompt(self) -> str:
        """Format active skills for system prompt injection."""
        if not self.active_skills:
            return ""

        lines = ["# Relevant Skills and Patterns\n"]
        for skill_def in self.get_active_skill_definitions():
            lines.append(f"## {skill_def.name}")
            if skill_def.description:
                lines.append(f"*{skill_def.description}*")
            lines.append("")
            lines.append(skill_def.content)
            lines.append("")

        return "\n".join(lines)

    def format_rules_for_prompt(self) -> str:
        """Format active rules for system prompt injection."""
        active_rules = self.get_active_rule_definitions()
        if not active_rules:
            return ""

        lines = ["# Coding Standards and Rules\n"]
        for rule in active_rules:
            lines.append(f"## {rule.name}")
            if rule.category:
                lines.append(f"*Category: {rule.category}*")
            lines.append("")
            lines.append(rule.content)
            lines.append("")

        return "\n".join(lines)

    def get_agent_tool(self, agent_name: str) -> "ClaudeAgentDefinition" | None:
        """Get an agent definition by name."""
        return self.agents.get(agent_name)

    def get_command(self, command_name: str) -> "SlashCommand" | None:
        """Get a command definition by name."""
        # Remove leading slash if present
        name = command_name.lstrip("/")
        return self.commands.get(name)

    def get_workflow(self, workflow_name: str) -> "WorkflowDefinition" | None:
        """Get a workflow definition by name."""
        return self.workflows.get(workflow_name)
