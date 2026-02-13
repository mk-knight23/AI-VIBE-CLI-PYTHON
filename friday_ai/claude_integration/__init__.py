"""Claude folder integration for Friday AI.

This module provides integration with the .claude folder structure, enabling:
- Agent discovery and invocation from .claude/agents/
- Skill loading and contextual application from .claude/skills/
- Rule enforcement from .claude/rules/
- Workflow execution from .claude/workflows/
- Slash command mapping from .claude/commands/
"""

from typing import TYPE_CHECKING

from friday_ai.claude_integration.utils import (
    ensure_claude_structure,
    find_claude_dir,
    load_markdown_file,
    parse_frontmatter,
)

if TYPE_CHECKING:
    from friday_ai.claude_integration.agent_loader import ClaudeAgentLoader
    from friday_ai.claude_integration.command_mapper import CommandMapper
    from friday_ai.claude_integration.context import ClaudeContext
    from friday_ai.claude_integration.rules_engine import RulesEngine
    from friday_ai.claude_integration.skills_manager import SkillsManager
    from friday_ai.claude_integration.workflow_engine import WorkflowEngine

__all__ = [
    "find_claude_dir",
    "parse_frontmatter",
    "load_markdown_file",
    "ensure_claude_structure",
    "ClaudeAgentLoader",
    "SkillsManager",
    "RulesEngine",
    "WorkflowEngine",
    "CommandMapper",
    "ClaudeContext",
]


# Lazy imports for components that may not be needed immediately
def __getattr__(name: str):
    """Lazy load components to avoid circular imports."""
    if name == "ClaudeAgentLoader":
        from friday_ai.claude_integration.agent_loader import ClaudeAgentLoader

        return ClaudeAgentLoader
    elif name == "SkillsManager":
        from friday_ai.claude_integration.skills_manager import SkillsManager

        return SkillsManager
    elif name == "RulesEngine":
        from friday_ai.claude_integration.rules_engine import RulesEngine

        return RulesEngine
    elif name == "WorkflowEngine":
        from friday_ai.claude_integration.workflow_engine import WorkflowEngine

        return WorkflowEngine
    elif name == "CommandMapper":
        from friday_ai.claude_integration.command_mapper import CommandMapper

        return CommandMapper
    elif name == "ClaudeContext":
        from friday_ai.claude_integration.context import ClaudeContext

        return ClaudeContext

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
