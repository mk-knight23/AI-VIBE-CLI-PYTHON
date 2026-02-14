"""Command mapper for .claude/commands/ directory.

Maps command markdown files to slash commands that can be executed
in the Friday AI CLI, supporting agents, skills, and workflows.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from friday_ai.claude_integration.utils import load_markdown_file

if TYPE_CHECKING:
    from friday_ai.agent.agent import Agent

logger = logging.getLogger(__name__)


@dataclass
class SlashCommand:
    """Definition of a slash command from .claude/commands/*.md.

    Attributes:
        name: Command name (e.g., "tdd", "e2e")
        description: Short description for help text
        agent: Optional agent to invoke when command is run
        skill: Optional skill to activate when command is run
        workflow: Optional workflow to execute when command is run
        prompt_template: Template for generating the prompt
        aliases: Alternative command names
        args_schema: Expected arguments schema
        examples: Usage examples
    """

    name: str
    description: str = ""
    agent: str | None = None
    skill: str | None = None
    workflow: str | None = None
    prompt_template: str = ""
    aliases: list[str] = field(default_factory=list)
    args_schema: dict[str, Any] = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)

    @property
    def full_command(self) -> str:
        """Get the full command name with slash prefix."""
        return f"/{self.name}"

    def build_prompt(self, args: str = "") -> str:
        """Build the prompt for this command.

        Args:
            args: Command arguments provided by user.

        Returns:
            Formatted prompt string.
        """
        if self.prompt_template:
            # Replace {args} placeholder if present
            if "{args}" in self.prompt_template:
                return self.prompt_template.replace("{args}", args)
            # Append args if template doesn't have placeholder
            if args:
                return f"{self.prompt_template}\n\n{args}"
            return self.prompt_template

        # Default prompt construction
        if self.agent:
            base = f"Use the {self.agent} to help with:"
        elif self.workflow:
            base = f"Run the {self.workflow} workflow for:"
        elif self.skill:
            base = f"Apply {self.skill} expertise to:"
        else:
            base = "Help with:"

        if args:
            return f"{base}\n{args}"
        return base


class CommandMapper:
    """Mapper for loading and executing slash commands from .claude/commands/."""

    # Pattern to extract agent/skill/workflow references
    AGENT_PATTERN = re.compile(
        r"invokes?\s+(?:the\s+)?`?([^`\s]+)`?(?:\s+agent)?", re.IGNORECASE
    )
    SKILL_PATTERN = re.compile(
        r"references?\s+(?:the\s+)?`?([^`\s]+)`?(?:\s+skill)?", re.IGNORECASE
    )
    WORKFLOW_PATTERN = re.compile(
        r"runs?\s+(?:the\s+)?`?([^`\s]+)`?(?:\s+workflow)?", re.IGNORECASE
    )

    def __init__(self, claude_dir: Path | None):
        """Initialize the command mapper.

        Args:
            claude_dir: Path to the .claude directory. If None, no commands will be loaded.
        """
        self.claude_dir = claude_dir
        self.commands_dir = claude_dir / "commands" if claude_dir else None
        self._commands: dict[str, SlashCommand] = {}
        self._aliases: dict[str, str] = {}  # alias -> command name

    def load_all_commands(self) -> list[SlashCommand]:
        """Load all command definitions from the commands directory.

        Returns:
            List of loaded command definitions.
        """
        if not self.commands_dir or not self.commands_dir.exists():
            logger.debug("No .claude/commands directory found")
            return []

        commands = []
        for md_file in sorted(self.commands_dir.glob("*.md")):
            try:
                command = self._parse_command_file(md_file)
                if command:
                    self._commands[command.name] = command
                    commands.append(command)

                    # Register aliases
                    for alias in command.aliases:
                        self._aliases[alias] = command.name

                    logger.debug(f"Loaded command: /{command.name}")
            except Exception as e:
                logger.warning(f"Failed to parse command file {md_file}: {e}")
                continue

        return commands

    def _parse_command_file(self, path: Path) -> SlashCommand | None:
        """Parse a single command markdown file.

        Args:
            path: Path to the .md file.

        Returns:
            Parsed command definition or None if parsing failed.
        """
        result = load_markdown_file(path)
        if result is None:
            return None

        frontmatter, content = result

        # Command name from filename
        name = path.stem

        # Get description from frontmatter
        description = frontmatter.get("description", "")

        # Try to extract agent/skill/workflow from content
        agent = self._extract_agent(content)
        skill = self._extract_skill(content)
        workflow = self._extract_workflow(content)

        # Get aliases from frontmatter
        aliases = frontmatter.get("aliases", [])
        if isinstance(aliases, str):
            aliases = [a.strip() for a in aliases.split(",") if a.strip()]

        # Extract prompt template (first instruction section)
        prompt_template = self._extract_prompt_template(content)

        # Extract examples
        examples = self._extract_examples(content)

        return SlashCommand(
            name=name,
            description=description,
            agent=agent,
            skill=skill,
            workflow=workflow,
            prompt_template=prompt_template,
            aliases=aliases,
            examples=examples,
        )

    def _extract_agent(self, content: str) -> str | None:
        """Extract agent reference from content."""
        # Look for explicit agent mentions
        match = self.AGENT_PATTERN.search(content)
        if match:
            return match.group(1)

        # Look for "This command invokes the X agent"
        agent_line = re.search(
            r"invokes?\s+(?:the\s+)?([\w\-]+)(?:\s+agent)", content, re.IGNORECASE
        )
        if agent_line:
            return agent_line.group(1)

        return None

    def _extract_skill(self, content: str) -> str | None:
        """Extract skill reference from content."""
        match = self.SKILL_PATTERN.search(content)
        if match:
            return match.group(1)
        return None

    def _extract_workflow(self, content: str) -> str | None:
        """Extract workflow reference from content."""
        match = self.WORKFLOW_PATTERN.search(content)
        if match:
            return match.group(1)
        return None

    def _extract_prompt_template(self, content: str) -> str:
        """Extract the main prompt template from content."""
        # Look for "How It Works" or "What This Command Does" section
        sections = [
            r"##\s*(?:What\s+This\s+Command\s+Does|How\s+It\s+Works)\s*\n(.+?)(?=\n##|$)",
            r"##\s*Usage\s*\n(.+?)(?=\n##|$)",
            r"##\s*Prompt\s*\n(.+?)(?=\n##|$)",
        ]

        for pattern in sections:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                section_content = match.group(1).strip()
                # Extract just the instruction part, not the full documentation
                # Look for numbered lists or the first substantial paragraph
                lines = section_content.split("\n")
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith("-"):
                        # Found start of content
                        return "\n".join(lines[i:]).strip()[:500]

        return ""

    def _extract_examples(self, content: str) -> list[str]:
        """Extract usage examples from content."""
        examples = []

        # Look for Example Usage section
        example_match = re.search(
            r"##\s*(?:Example\s+Usage|Examples)\s*\n(.+?)(?=\n##|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if example_match:
            example_section = example_match.group(1)
            # Extract code blocks or quoted examples
            code_blocks = re.findall(r"```\n(.+?)```", example_section, re.DOTALL)
            examples.extend(code_blocks)

            # Also look for User: /command patterns
            user_examples = re.findall(
                r"User:\s*(/.+?)(?=\n|$)", example_section, re.MULTILINE
            )
            examples.extend(user_examples)

        return examples[:3]  # Limit to first 3 examples

    def get_command(self, name: str) -> SlashCommand | None:
        """Get a command by name.

        Args:
            name: Command name (with or without leading slash).

        Returns:
            Command definition if found, None otherwise.
        """
        name = name.lstrip("/")

        # Direct lookup
        if name in self._commands:
            return self._commands[name]

        # Alias lookup
        if name in self._aliases:
            actual_name = self._aliases[name]
            return self._commands.get(actual_name)

        return None

    def list_commands(self) -> list[SlashCommand]:
        """List all loaded commands.

        Returns:
            List of all command definitions.
        """
        return list(self._commands.values())

    def list_command_names(self) -> list[str]:
        """List all command names including aliases.

        Returns:
            List of all command and alias names.
        """
        names = list(self._commands.keys())
        names.extend(self._aliases.keys())
        return sorted(names)

    async def execute_command(
        self,
        command_name: str,
        args: str,
        agent: Agent,
    ) -> str:
        """Execute a command.

        Args:
            command_name: Name of the command to execute.
            args: Command arguments.
            agent: The agent instance to use.

        Returns:
            Command execution result.
        """
        command = self.get_command(command_name)
        if not command:
            return f"Unknown command: /{command_name}"

        # Build the prompt
        prompt = command.build_prompt(args)

        # Execute based on command type
        if command.agent:
            # Invoke agent tool
            tool_name = f"subagent_{command.agent}"
            try:
                from friday_ai.tools.base import ToolInvocation

                result = await agent.session.tool_registry.invoke(
                    tool_name,
                    {"goal": prompt},
                    agent.config.cwd,
                    agent.session.hook_system,
                    agent.session.approval_manager,
                )
                # Use to_model_output() to get properly formatted result
                return result.to_model_output()
            except Exception as e:
                logger.error(f"Failed to execute agent command: {e}")
                return f"Error executing /{command.name}: {e}"

        elif command.workflow:
            # Execute workflow
            # This would integrate with the workflow engine
            return f"Executing workflow: {command.workflow}\n{prompt}"

        elif command.skill:
            # Activate skill and return prompt
            return f"[{command.skill} activated]\n{prompt}"

        else:
            # Just return the prompt for normal processing
            return prompt

    def get_help_text(self) -> str:
        """Generate help text for all commands.

        Returns:
            Formatted help text.
        """
        lines = ["Available Commands:\n"]

        # Group by type
        agent_cmds = []
        skill_cmds = []
        workflow_cmds = []
        other_cmds = []

        for cmd in self._commands.values():
            if cmd.agent:
                agent_cmds.append(cmd)
            elif cmd.skill:
                skill_cmds.append(cmd)
            elif cmd.workflow:
                workflow_cmds.append(cmd)
            else:
                other_cmds.append(cmd)

        if agent_cmds:
            lines.append("Agent Commands:")
            for cmd in sorted(agent_cmds, key=lambda c: c.name):
                lines.append(f"  /{cmd.name:<15} - {cmd.description[:50]}")
            lines.append("")

        if skill_cmds:
            lines.append("Skill Commands:")
            for cmd in sorted(skill_cmds, key=lambda c: c.name):
                lines.append(f"  /{cmd.name:<15} - {cmd.description[:50]}")
            lines.append("")

        if workflow_cmds:
            lines.append("Workflow Commands:")
            for cmd in sorted(workflow_cmds, key=lambda c: c.name):
                lines.append(f"  /{cmd.name:<15} - {cmd.description[:50]}")
            lines.append("")

        if other_cmds:
            lines.append("Other Commands:")
            for cmd in sorted(other_cmds, key=lambda c: c.name):
                lines.append(f"  /{cmd.name:<15} - {cmd.description[:50]}")

        return "\n".join(lines)
