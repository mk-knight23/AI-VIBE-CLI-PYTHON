from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class ClaudeIntegrationManager:
    def __init__(self, config: Any):
        self.config = config
        self.context: Any | None = None
        self.workflow_engine: Any | None = None
        self.command_mapper: Any | None = None

    def initialize(self) -> None:
        if not self.config.claude_dir and not self.config.get_claude_dir():
            return

        try:
            from friday_ai.claude_integration import (
                ClaudeAgentLoader,
                CommandMapper,
                RulesEngine,
                SkillsManager,
                WorkflowEngine,
            )
            from friday_ai.claude_integration.context import ClaudeContext

            claude_dir = self.config.get_claude_dir()
            if not claude_dir:
                return

            self.context = ClaudeContext(claude_dir=claude_dir)

            if self.config.claude_agents_enabled:
                agent_loader = ClaudeAgentLoader(claude_dir)
                agents = agent_loader.load_all_agents()
                for agent_def in agents:
                    self.context.agents[agent_def.name] = agent_def

            if self.config.claude_skills_enabled:
                skills_manager = SkillsManager(claude_dir)
                skills = skills_manager.load_all_skills()
                for skill in skills:
                    self.context.skills[skill.name] = skill

            if self.config.claude_rules_enabled:
                rules_engine = RulesEngine(claude_dir)
                rules = rules_engine.load_all_rules()
                self.context.rules = rules

            if self.config.claude_workflows_enabled:
                self.workflow_engine = WorkflowEngine(claude_dir)
                self.workflow_engine.load_all_workflows()
                for workflow in self.workflow_engine.list_workflows():
                    self.context.workflows[workflow.name] = workflow

            if self.config.claude_commands_enabled:
                self.command_mapper = CommandMapper(claude_dir)
                self.command_mapper.load_all_commands()
                for cmd in self.command_mapper.list_commands():
                    self.context.commands[cmd.name] = cmd

        except Exception as e:
            logger.debug(f"Claude integration failed: {e}")

    def get_stats(self) -> Dict[str, int]:
        if not self.context:
            return {}

        return {
            "agents": len(self.context.agents),
            "skills": len(self.context.skills),
            "rules": len(self.context.rules),
            "workflows": len(self.context.workflows),
            "commands": len(self.context.commands),
        }
