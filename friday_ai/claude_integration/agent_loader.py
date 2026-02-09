"""Agent loader for .claude/agents/ directory.

Parses agent markdown files with YAML frontmatter and converts them
to SubagentDefinition objects for use in the tool registry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from friday_ai.claude_integration.utils import load_markdown_file
from friday_ai.config.config import Config
from friday_ai.tools.subagents import SubagentDefinition

logger = logging.getLogger(__name__)


@dataclass
class ClaudeAgentDefinition:
    """Definition of an agent from .claude/agents/*.md file.

    Attributes:
        name: Unique identifier for the agent (from filename or frontmatter)
        description: Short description of what the agent does
        tools: List of tool names the agent is allowed to use
        model: Preferred model (haiku, sonnet, opus) - mapped to actual model names
        prompt_template: The full system prompt/content for the agent
        max_turns: Maximum conversation turns for this agent
        timeout_seconds: Timeout for agent execution
        metadata: Additional frontmatter fields
    """

    name: str
    description: str
    tools: list[str] = field(default_factory=list)
    model: str = "sonnet"  # Default to sonnet for best coding
    prompt_template: str = ""
    max_turns: int = 20
    timeout_seconds: float = 600
    metadata: dict[str, Any] = field(default_factory=dict)


class ClaudeAgentLoader:
    """Loader for .claude/agents/ directory.

    Discovers and parses agent markdown files, converting them to
    definitions that can be registered as subagent tools.
    """

    def __init__(self, claude_dir: Path | None):
        """Initialize the agent loader.

        Args:
            claude_dir: Path to the .claude directory. If None, no agents will be loaded.
        """
        self.claude_dir = claude_dir
        self.agents_dir = claude_dir / "agents" if claude_dir else None
        self._agents: dict[str, ClaudeAgentDefinition] = {}

    def load_all_agents(self) -> list[ClaudeAgentDefinition]:
        """Load all agent definitions from the agents directory.

        Returns:
            List of loaded agent definitions.
        """
        if not self.agents_dir or not self.agents_dir.exists():
            logger.debug("No .claude/agents directory found")
            return []

        agents = []
        for md_file in sorted(self.agents_dir.glob("*.md")):
            try:
                agent_def = self.parse_agent_file(md_file)
                if agent_def:
                    agents.append(agent_def)
                    self._agents[agent_def.name] = agent_def
                    logger.debug(f"Loaded agent: {agent_def.name}")
            except Exception as e:
                logger.warning(f"Failed to parse agent file {md_file}: {e}")
                continue

        return agents

    def parse_agent_file(self, path: Path) -> ClaudeAgentDefinition | None:
        """Parse a single agent markdown file.

        Args:
            path: Path to the .md file.

        Returns:
            Parsed agent definition or None if parsing failed.
        """
        result = load_markdown_file(path)
        if result is None:
            return None

        frontmatter, content = result

        # Get name from frontmatter or filename
        name = frontmatter.get("name", path.stem)

        # Validate required fields
        description = frontmatter.get("description", "")
        if not description:
            # Try to extract from first paragraph of content
            first_para = content.split("\n\n")[0].strip()
            if first_para:
                description = first_para[:100] + "..." if len(first_para) > 100 else first_para
            else:
                description = f"Agent loaded from {path.name}"

        # Parse tools (can be string or list)
        tools = frontmatter.get("tools", [])
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]

        # Parse model preference
        model = frontmatter.get("model", "sonnet")

        # Parse max_turns
        max_turns = frontmatter.get("max_turns", 20)
        try:
            max_turns = int(max_turns)
        except (ValueError, TypeError):
            max_turns = 20

        # Parse timeout
        timeout = frontmatter.get("timeout_seconds", 600)
        try:
            timeout = float(timeout)
        except (ValueError, TypeError):
            timeout = 600

        # Store extra frontmatter in metadata
        metadata = {k: v for k, v in frontmatter.items() if k not in [
            "name", "description", "tools", "model", "max_turns", "timeout_seconds"
        ]}

        return ClaudeAgentDefinition(
            name=name,
            description=description,
            tools=tools,
            model=model,
            prompt_template=content,
            max_turns=max_turns,
            timeout_seconds=timeout,
            metadata=metadata,
        )

    def get_agent(self, name: str) -> ClaudeAgentDefinition | None:
        """Get a loaded agent by name.

        Args:
            name: The agent name.

        Returns:
            Agent definition if found, None otherwise.
        """
        return self._agents.get(name)

    def convert_to_subagent_definition(
        self,
        agent_def: ClaudeAgentDefinition,
        config: Config,
    ) -> SubagentDefinition:
        """Convert a ClaudeAgentDefinition to a SubagentDefinition.

        This converts the .claude agent format to the internal Friday AI
        subagent format that can be registered as a tool.

        Args:
            agent_def: The parsed agent definition.
            config: The current config (for model mapping).

        Returns:
            SubagentDefinition ready for tool registration.
        """
        # Map model preference to actual model name
        model_mapping = {
            "haiku": config.model_name if "haiku" in config.model_name.lower() else "claude-3-haiku-20240307",
            "sonnet": config.model_name if "sonnet" in config.model_name.lower() else "claude-4-sonnet-20250501",
            "opus": config.model_name if "opus" in config.model_name.lower() else "claude-3-opus-20240229",
        }

        # Build the goal prompt from the template
        goal_prompt = agent_def.prompt_template

        # Add tools instruction if tools are specified
        if agent_def.tools:
            tools_list = ", ".join(agent_def.tools)
            goal_prompt += f"\n\nYou have access to these tools: {tools_list}\n"
            goal_prompt += "Use them appropriately to complete your task."

        return SubagentDefinition(
            name=agent_def.name,
            description=agent_def.description,
            goal_prompt=goal_prompt,
            allowed_tools=agent_def.tools if agent_def.tools else None,
            max_turns=agent_def.max_turns,
            timeout_seconds=agent_def.timeout_seconds,
        )

    def convert_all_to_subagents(
        self,
        config: Config,
    ) -> list[SubagentDefinition]:
        """Convert all loaded agents to subagent definitions.

        Args:
            config: The current config.

        Returns:
            List of SubagentDefinitions.
        """
        return [
            self.convert_to_subagent_definition(agent_def, config)
            for agent_def in self._agents.values()
        ]
