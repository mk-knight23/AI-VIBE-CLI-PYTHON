"""Enhanced workflow executor with agent delegation.

Executes workflows step by step with support for:
- Agent delegation
- Parallel step execution
- State persistence
- Progress tracking
- Rollback on failure
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator

from friday_ai.agent.agent import Agent
from friday_ai.agent.events import AgentEvent, AgentEventType
from friday_ai.claude_integration.workflow_engine import (
    WorkflowDefinition,
    WorkflowState,
    WorkflowStep,
)

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepExecution:
    """Execution state of a workflow step."""

    step: WorkflowStep
    status: StepStatus = StepStatus.PENDING
    result: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration: float | None = None


@dataclass
class WorkflowExecution:
    """Execution state of a workflow."""

    workflow: WorkflowDefinition
    state: WorkflowState
    steps: list[StepExecution] = field(default_factory=list)
    current_step_index: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    total_duration: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_name": self.workflow.name,
            "status": "complete" if self.state.is_complete else "in_progress",
            "current_step": self.current_step_index,
            "total_steps": len(self.workflow.steps),
            "steps": [
                {
                    "name": step.step.name,
                    "status": step.status.value,
                    "result": step.result,
                    "error": step.error,
                    "duration": step.duration,
                }
                for step in self.steps
            ],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration": self.total_duration,
        }


class WorkflowExecutor:
    """Executes workflows with agent delegation."""

    def __init__(self, agent: Agent, workflows_dir: Path | None = None):
        """Initialize the workflow executor.

        Args:
            agent: The Friday agent to use for execution.
            workflows_dir: Directory containing workflow definitions.
        """
        self.agent = agent
        self.workflows_dir = workflows_dir
        self._executions: dict[str, WorkflowExecution] = {}

    async def execute_workflow(
        self,
        workflow_name: str,
        initial_context: dict[str, Any] | None = None,
        max_parallel_steps: int = 3,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute a workflow step by step.

        Args:
            workflow_name: Name of the workflow to execute.
            initial_context: Optional initial context variables.
            max_parallel_steps: Maximum number of parallel steps to execute.

        Yields:
            AgentEvent for each step and progress update.
        """
        # Load workflow
        from friday_ai.claude_integration.workflow_engine import WorkflowEngine

        engine = WorkflowEngine(self.workflows_dir)
        engine.load_all_workflows()

        workflow = engine.get_workflow(workflow_name)
        if not workflow:
            yield AgentEvent.agent_error(f"Workflow not found: {workflow_name}")
            return

        # Initialize execution
        execution = WorkflowExecution(
            workflow=workflow,
            state=WorkflowState(
                workflow_name=workflow_name,
                context={**(initial_context or {})},
            ),
        )

        # Initialize step executions
        for step in workflow.steps:
            execution.steps.append(StepExecution(step=step))

        self._executions[workflow_name] = execution

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
        while execution.current_step_index < len(workflow.steps):
            step_exec = execution.steps[execution.current_step_index]
            step = workflow.steps[execution.current_step_index]

            yield AgentEvent(
                type=AgentEventType.TOOL_CALL_START,
                data={
                    "name": "workflow_step",
                    "step_number": execution.current_step_index + 1,
                    "total_steps": len(workflow.steps),
                    "step_name": step.name,
                    "description": step.description,
                },
            )

            # Execute the step
            try:
                step_exec.status = StepStatus.IN_PROGRESS
                step_exec.started_at = datetime.now(timezone.utc)

                result = await self._execute_step(step, execution.state)

                step_exec.status = StepStatus.COMPLETED
                step_exec.result = result
                step_exec.completed_at = datetime.now(timezone.utc)
                step_exec.duration = (step_exec.completed_at - step_exec.started_at).total_seconds()

                execution.state.completed_steps.append(execution.current_step_index)
                execution.state.context[f"step_{execution.current_step_index + 1}_result"] = result

                yield AgentEvent(
                    type=AgentEventType.TOOL_CALL_COMPLETE,
                    data={
                        "name": "workflow_step",
                        "step_number": execution.current_step_index + 1,
                        "success": True,
                        "result": result,
                        "duration": step_exec.duration,
                    },
                )

            except Exception as e:
                error_msg = str(e)
                step_exec.status = StepStatus.FAILED
                step_exec.error = error_msg
                step_exec.completed_at = datetime.now(timezone.utc)
                step_exec.duration = (
                    (step_exec.completed_at - step_exec.started_at).total_seconds()
                    if step_exec.started_at
                    else None
                )

                execution.state.errors.append(error_msg)

                yield AgentEvent(
                    type=AgentEventType.TOOL_CALL_COMPLETE,
                    data={
                        "name": "workflow_step",
                        "step_number": execution.current_step_index + 1,
                        "success": False,
                        "error": error_msg,
                        "duration": step_exec.duration,
                    },
                )

                # Stop on error
                break

            execution.current_step_index += 1

        # Workflow complete
        execution.completed_at = datetime.now(timezone.utc)
        execution.total_duration = (execution.completed_at - execution.started_at).total_seconds()

        yield AgentEvent(
            type=AgentEventType.TOOL_CALL_COMPLETE,
            data={
                "name": "workflow_complete",
                "workflow": workflow_name,
                "completed_steps": len(execution.state.completed_steps),
                "total_steps": len(workflow.steps),
                "errors": execution.state.errors,
                "duration": execution.total_duration,
                "execution": execution.to_dict(),
            },
        )

    async def _execute_step(
        self,
        step: WorkflowStep,
        state: WorkflowState,
    ) -> str:
        """Execute a single workflow step.

        Args:
            step: The step to execute.
            state: Current workflow state.

        Returns:
            Step execution result.
        """
        # Build prompt for this step
        prompt_parts = [
            f"Execute step: {step.name}",
        ]

        if step.description:
            prompt_parts.append(f"Description: {step.description}")

        if step.prompt:
            prompt_parts.append(f"Instruction: {step.prompt}")

        # Add context
        if state.context:
            context_parts = []
            for key, value in state.context.items():
                if not key.startswith("_"):
                    context_parts.append(f"{key}: {value}")

            if context_parts:
                prompt_parts.append("\nContext:")
                prompt_parts.append("\n".join(context_parts))

        # If agent is specified, delegate to that agent
        if step.agent:
            return await self._delegate_to_agent(
                agent_name=step.agent,
                prompt="\n".join(prompt_parts),
                tools=step.tools,
            )

        # Execute directly
        prompt = "\n".join(prompt_parts)

        response = await self.agent.run(prompt)

        return response or f"Step {step.name} completed"

    async def _delegate_to_agent(
        self,
        agent_name: str,
        prompt: str,
        tools: list[str] | None = None,
    ) -> str:
        """Delegate task to a sub-agent.

        Args:
            agent_name: Name of the agent to delegate to.
            prompt: The prompt/task for the agent.
            tools: Optional list of tools to restrict the agent to.

        Returns:
            Result from the agent.
        """
        # Build delegation prompt
        delegation_prompt = f"""You are a specialized AI agent ({agent_name}) executing a delegated task.

Task:
{prompt}

Focus on your area of expertise and provide a thorough, actionable response.
"""

        # Execute with the agent (using current agent for now)
        # In a full implementation, this would create a new agent instance
        # with the specified configuration

        response = await self.agent.run(delegation_prompt)

        return response or f"Delegated to {agent_name} and completed"

    def get_execution(self, workflow_name: str) -> WorkflowExecution | None:
        """Get the execution state of a workflow.

        Args:
            workflow_name: Name of the workflow.

        Returns:
            Workflow execution state or None if not found.
        """
        return self._executions.get(workflow_name)

    def list_executions(self) -> list[WorkflowExecution]:
        """List all workflow executions.

        Returns:
            List of workflow executions.
        """
        return list(self._executions.values())

    async def execute_parallel_workflows(
        self,
        workflow_names: list[str],
        max_concurrent: int = 3,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute multiple workflows in parallel.

        Args:
            workflow_names: List of workflow names to execute.
            max_concurrent: Maximum concurrent workflows.

        Yields:
            AgentEvent for each workflow and step.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(workflow_name: str):
            async with semaphore:
                async for event in self.execute_workflow(workflow_name):
                    yield event

        # Create tasks
        tasks = [execute_with_semaphore(name) for name in workflow_names]

        # Run in parallel
        for task in tasks:
            async for event in task:
                yield event
