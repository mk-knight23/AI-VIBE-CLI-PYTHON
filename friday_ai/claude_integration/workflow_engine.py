"""Workflow engine for .claude/workflows/ directory.

Parses workflow markdown files and executes multi-step workflows
with state management and progress tracking.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator

from friday_ai.agent.events import AgentEvent, AgentEventType
from friday_ai.claude_integration.utils import load_markdown_file
from friday_ai.tools.base import Tool
from friday_ai.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """A single step in a workflow.

    Attributes:
        name: Step identifier
        description: What this step does
        prompt: The prompt/instruction for this step
        agent: Optional agent to invoke for this step
        tools: Optional tools available for this step
        verification: Optional verification criteria
    """

    name: str
    description: str = ""
    prompt: str = ""
    agent: str | None = None
    tools: list[str] = field(default_factory=list)
    verification: str | None = None


@dataclass
class WorkflowDefinition:
    """Definition of a workflow from .claude/workflows/*.md.

    Attributes:
        name: Workflow name
        description: Short description
        category: Workflow category (testing, deployment, audit, etc.)
        steps: Ordered list of workflow steps
        prerequisites: List of prerequisites
        variables: Available template variables
    """

    name: str
    description: str = ""
    category: str = "general"
    steps: list[WorkflowStep] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Current state of a workflow execution.

    Attributes:
        workflow_name: Name of the workflow being executed
        current_step_index: Index of the current step
        completed_steps: List of completed step indices
        context: Shared context across steps
        started_at: Start timestamp
        errors: List of errors encountered
    """

    workflow_name: str
    current_step_index: int = 0
    completed_steps: list[int] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=lambda: __import__("time").time())
    errors: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        workflow = self.context.get("_workflow")
        if not workflow:
            return False
        return self.current_step_index >= len(workflow.steps)

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "workflow_name": self.workflow_name,
            "current_step_index": self.current_step_index,
            "completed_steps": self.completed_steps,
            "context": {k: v for k, v in self.context.items() if not k.startswith("_")},
            "started_at": self.started_at,
            "errors": self.errors,
            "is_complete": self.is_complete,
        }


class WorkflowEngine:
    """Engine for loading and executing workflows from .claude/workflows/."""

    def __init__(self, claude_dir: Path | None):
        """Initialize the workflow engine.

        Args:
            claude_dir: Path to the .claude directory. If None, no workflows will be loaded.
        """
        self.claude_dir = claude_dir
        self.workflows_dir = claude_dir / "workflows" if claude_dir else None
        self._workflows: dict[str, WorkflowDefinition] = {}

    def load_all_workflows(self) -> list[WorkflowDefinition]:
        """Load all workflow definitions from the workflows directory.

        Returns:
            List of loaded workflow definitions.
        """
        if not self.workflows_dir or not self.workflows_dir.exists():
            logger.debug("No .claude/workflows directory found")
            return []

        workflows = []
        for md_file in sorted(self.workflows_dir.glob("*.md")):
            try:
                workflow = self._parse_workflow_file(md_file)
                if workflow:
                    self._workflows[workflow.name] = workflow
                    workflows.append(workflow)
                    logger.debug(f"Loaded workflow: {workflow.name} ({workflow.category})")
            except Exception as e:
                logger.warning(f"Failed to parse workflow file {md_file}: {e}")
                continue

        return workflows

    def _parse_workflow_file(self, path: Path) -> WorkflowDefinition | None:
        """Parse a single workflow markdown file.

        Args:
            path: Path to the .md file.

        Returns:
            Parsed workflow definition or None if parsing failed.
        """
        result = load_markdown_file(path)
        if result is None:
            return None

        frontmatter, content = result

        # Get name from frontmatter, H1, or filename
        name = frontmatter.get("name", path.stem)
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1_match:
            name = h1_match.group(1).strip()

        # Get description
        description = frontmatter.get("description", "")
        if not description:
            # Try first paragraph after H1
            desc_match = re.search(r"^#\s+.+\n\n(.+?)(?:\n\n|$)", content, re.MULTILINE)
            if desc_match:
                description = desc_match.group(1).strip()

        # Get category
        category = frontmatter.get("category", self._infer_category(path.stem))

        # Parse steps from content
        steps = self._extract_steps(content)

        # Parse prerequisites
        prerequisites = self._extract_prerequisites(content)

        return WorkflowDefinition(
            name=name,
            description=description,
            category=category,
            steps=steps,
            prerequisites=prerequisites,
        )

    def _infer_category(self, filename: str) -> str:
        """Infer workflow category from filename."""
        filename_lower = filename.lower()

        categories = {
            "testing": ["test", "testing", "coverage", "tdd"],
            "deployment": ["deploy", "release", "publish", "ci", "cd"],
            "audit": ["audit", "review", "security", "check"],
            "upgrade": ["upgrade", "update", "migrate"],
            "setup": ["setup", "init", "configure", "install"],
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    return category

        return "general"

    def _extract_steps(self, content: str) -> list[WorkflowStep]:
        """Extract workflow steps from content."""
        steps = []

        # Look for numbered sections like "## 1. Step Name" or "### Step 1: Name"
        step_patterns = [
            r"(?:^|\n)#{2,3}\s*(?:Step\s*)?(\d+)[.:\s]+(.+?)(?=\n#{2,3}\s*(?:Step\s*)?\d+|$)",
            r"(?:^|\n)#{2,3}\s*(\d+)[.:\s]+(.+?)(?=\n#{2,3}\s*\d+|$)",
        ]

        for pattern in step_patterns:
            matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))
            if matches:
                for i, match in enumerate(matches):
                    step_num = match.group(1)
                    step_content = match.group(2).strip()

                    # Extract step name (first line)
                    lines = step_content.split("\n")
                    name = lines[0].strip() if lines else f"Step {step_num}"

                    # Extract description (rest of content)
                    description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

                    # Extract prompt if there's a code block or specific instruction
                    prompt = self._extract_step_prompt(step_content)

                    steps.append(
                        WorkflowStep(
                            name=name,
                            description=description[:200],  # Truncate long descriptions
                            prompt=prompt,
                        )
                    )

                break  # Found valid pattern

        return steps

    def _extract_step_prompt(self, step_content: str) -> str:
        """Extract the actionable prompt from step content."""
        # Look for code blocks that might contain commands
        code_blocks = re.findall(r"```(?:bash|sh|shell)?\n(.+?)```", step_content, re.DOTALL)
        if code_blocks:
            return f"Execute the following:\n{code_blocks[0].strip()}"

        # Look for action items or instructions
        action_match = re.search(
            r"(?:Action|Instruction|Task|Run|Execute):\s*(.+?)(?=\n\n|$)",
            step_content,
            re.DOTALL | re.IGNORECASE,
        )
        if action_match:
            return action_match.group(1).strip()

        # Use the content itself as the prompt
        return step_content[:500]  # Limit length

    def _extract_prerequisites(self, content: str) -> list[str]:
        """Extract prerequisites from content."""
        prereqs = []

        # Look for Prerequisites section
        prereq_match = re.search(
            r"(?:^|\n)#{2,3}\s*(?:Prerequisites|Requirements|Before You Start)\s*\n(.+?)(?=\n#{2,3}|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if prereq_match:
            prereq_section = prereq_match.group(1)
            # Extract list items
            items = re.findall(r"[-*]\s*(.+?)(?=\n[-*]|\n\n|$)", prereq_section, re.DOTALL)
            prereqs = [item.strip() for item in items if item.strip()]

        return prereqs

    def get_workflow(self, name: str) -> WorkflowDefinition | None:
        """Get a loaded workflow by name.

        Args:
            name: The workflow name.

        Returns:
            Workflow definition if found, None otherwise.
        """
        return self._workflows.get(name)

    def list_workflows(self) -> list[WorkflowDefinition]:
        """List all loaded workflows.

        Returns:
            List of all workflow definitions.
        """
        return list(self._workflows.values())

    def list_workflows_by_category(self, category: str) -> list[WorkflowDefinition]:
        """List workflows filtered by category.

        Args:
            category: Category to filter by.

        Returns:
            List of matching workflow definitions.
        """
        return [w for w in self._workflows.values() if w.category == category]

    async def execute_workflow(
        self,
        workflow_name: str,
        tool_registry: ToolRegistry | None = None,
        initial_context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute a workflow step by step.

        Args:
            workflow_name: Name of the workflow to execute.
            tool_registry: Tool registry for executing tools in steps.
            initial_context: Optional initial context variables.

        Yields:
            AgentEvent for each step and progress update.
        """
        workflow = self._workflows.get(workflow_name)
        if not workflow:
            yield AgentEvent.agent_error(f"Workflow not found: {workflow_name}")
            return

        # Initialize state
        state = WorkflowState(
            workflow_name=workflow_name,
            context={"_workflow": workflow, **(initial_context or {})},
        )

        yield AgentEvent(
            type=AgentEventType.TOOL_CALL_START,
            data={
                "name": "workflow_start",
                "workflow": workflow_name,
                "steps": len(workflow.steps),
                "description": workflow.description,
            },
        )

        # Execute each step
        while state.current_step_index < len(workflow.steps):
            step = workflow.steps[state.current_step_index]
            step_num = state.current_step_index + 1

            yield AgentEvent(
                type=AgentEventType.TOOL_CALL_START,
                data={
                    "name": "workflow_step",
                    "step_number": step_num,
                    "total_steps": len(workflow.steps),
                    "step_name": step.name,
                    "description": step.description,
                },
            )

            # Execute the step
            try:
                result = await self._execute_step(step, state, tool_registry)

                state.completed_steps.append(state.current_step_index)
                state.context[f"step_{step_num}_result"] = result

                yield AgentEvent(
                    type=AgentEventType.TOOL_CALL_COMPLETE,
                    data={
                        "name": "workflow_step",
                        "step_number": step_num,
                        "success": True,
                        "result": result,
                    },
                )

            except Exception as e:
                error_msg = str(e)
                state.errors.append(error_msg)

                yield AgentEvent(
                    type=AgentEventType.TOOL_CALL_COMPLETE,
                    data={
                        "name": "workflow_step",
                        "step_number": step_num,
                        "success": False,
                        "error": error_msg,
                    },
                )

            state.current_step_index += 1

        # Workflow complete
        yield AgentEvent(
            type=AgentEventType.TOOL_CALL_COMPLETE,
            data={
                "name": "workflow_complete",
                "workflow": workflow_name,
                "completed_steps": len(state.completed_steps),
                "total_steps": len(workflow.steps),
                "errors": state.errors,
                "duration": __import__("time").time() - state.started_at,
            },
        )

    async def _execute_step(
        self,
        step: WorkflowStep,
        state: WorkflowState,
        tool_registry: ToolRegistry | None = None,
    ) -> str:
        """Execute a single workflow step.

        Executes agents and tools as specified in the step definition.

        Args:
            step: The step to execute.
            state: Current workflow state.
            tool_registry: Tool registry for tool execution.

        Returns:
            Step execution result.
        """
        # If step has an agent, invoke it
        if step.agent:
            agent_result = await self._invoke_agent(
                step.agent, step.prompt, state, tool_registry
            )
            return agent_result

        # If step has tools, execute them
        if step.tools and tool_registry:
            tool_results = []

            for tool_name in step.tools:
                tool_result = await self._invoke_tool(
                    tool_name, step.prompt, state, tool_registry
                )
                tool_results.append(tool_result)

            return "\n\n".join(tool_results)

        # If no agent or tools, return the prompt/description
        result_parts = [f"Step: {step.name}"]

        if step.description:
            result_parts.append(f"Description: {step.description}")

        if step.prompt:
            result_parts.append(f"Instruction: {step.prompt}")

        return "\n".join(result_parts)

    async def _invoke_agent(
        self,
        agent_name: str,
        prompt: str,
        state: WorkflowState,
        tool_registry: ToolRegistry | None = None,
    ) -> str:
        """Invoke an agent for workflow step execution.

        Args:
            agent_name: Name of the agent to invoke.
            prompt: Prompt/instruction for the agent.
            state: Current workflow state.
            tool_registry: Tool registry for agent execution.

        Returns:
            Agent execution result.
        """
        # Try to get subagent tool from registry
        if not tool_registry:
            return f"Error: No tool registry available to invoke agent '{agent_name}'"

        subagent_tool = self._get_subagent_tool(agent_name, tool_registry)
        if not subagent_tool:
            return f"Error: Agent '{agent_name}' not found in tool registry"

        try:
            # Execute the subagent with the prompt
            from pathlib import Path
            from friday_ai.tools.base import ToolInvocation

            # Add workflow context to prompt
            context_info = self._format_context(state)
            full_prompt = f"{prompt}\n\nWorkflow Context:\n{context_info}"

            invocation = ToolInvocation(
                params={"goal": full_prompt},
                cwd=Path.cwd(),
            )

            result = await subagent_tool.execute(invocation)

            if result.success:
                return result.output or "Agent completed successfully"
            else:
                return f"Agent execution failed: {result.error}"

        except Exception as e:
            logger.exception(f"Error invoking agent '{agent_name}'")
            return f"Error invoking agent '{agent_name}': {str(e)}"

    async def _invoke_tool(
        self,
        tool_name: str,
        prompt: str,
        state: WorkflowState,
        tool_registry: ToolRegistry,
    ) -> str:
        """Invoke a tool for workflow step execution.

        Args:
            tool_name: Name of the tool to invoke.
            prompt: Prompt/instruction for the tool.
            state: Current workflow state.
            tool_registry: Tool registry for tool execution.

        Returns:
            Tool execution result.
        """
        # Get tool from registry
        tool = tool_registry.get(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found in registry"

        try:
            from pathlib import Path
            from friday_ai.tools.base import ToolInvocation

            # Parse tool parameters from prompt if it's a shell tool
            if tool_name == "shell" and "Execute:" in prompt:
                # Extract command from prompt
                command_match = re.search(r'Execute:\s*(.+?)(?:\n|$)', prompt, re.DOTALL)
                if command_match:
                    command = command_match.group(1).strip()
                    params = {"command": command}
                else:
                    params = {"command": prompt}
            else:
                # For other tools, pass prompt as parameter
                params = {"prompt": prompt}

            invocation = ToolInvocation(
                params=params,
                cwd=Path.cwd(),
            )

            result = await tool.execute(invocation)

            if result.success:
                return result.output or f"Tool '{tool_name}' executed successfully"
            else:
                return f"Tool '{tool_name}' execution failed: {result.error}"

        except Exception as e:
            logger.exception(f"Error invoking tool '{tool_name}'")
            return f"Error invoking tool '{tool_name}': {str(e)}"

    def _get_subagent_tool(
        self,
        agent_name: str,
        tool_registry: ToolRegistry,
    ) -> Tool | None:
        """Get a subagent tool by name from the registry.

        Args:
            agent_name: Name of the agent/subagent.
            tool_registry: Tool registry to search.

        Returns:
            Tool object if found, None otherwise.
        """
        # Subagent tools are typically named like 'subagent:agent_name'
        # Try different naming patterns
        possible_names = [
            f"subagent:{agent_name}",
            agent_name,
            f"agent_{agent_name}",
        ]

        for name in possible_names:
            tool = tool_registry.get(name)
            if tool:
                return tool

        return None

    def _format_context(self, state: WorkflowState) -> str:
        """Format workflow state context for display.

        Args:
            state: Current workflow state.

        Returns:
            Formatted context string.
        """
        context_lines = []

        for key, value in state.context.items():
            # Skip internal keys
            if key.startswith("_"):
                continue

            # Format value
            if isinstance(value, str):
                context_lines.append(f"  {key}: {value}")
            elif isinstance(value, (list, dict)):
                import json
                context_lines.append(f"  {key}: {json.dumps(value, indent=2)}")
            else:
                context_lines.append(f"  {key}: {str(value)}")

        return "\n".join(context_lines) if context_lines else "No context available"
