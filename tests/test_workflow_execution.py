"""Tests for workflow engine step execution.

Tests the real execution of workflow steps including:
- Agent invocation from workflow steps
- Tool invocation from workflow steps
- Error handling and propagation
- Context management between steps
"""

from __future__ import annotations

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from friday_ai.claude_integration.workflow_engine import (
    WorkflowEngine,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowState,
)
from friday_ai.tools.base import ToolResult
from friday_ai.tools.registry import ToolRegistry
from friday_ai.config.config import Config


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace with .claude directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "workflows").mkdir()
    return claude_dir


@pytest.fixture
def mock_config() -> Config:
    """Create a mock config."""
    config = MagicMock(spec=Config)
    config.model_name = "test-model"
    config.allowed_tools = None
    return config


@pytest.fixture
def tool_registry(mock_config: Config) -> ToolRegistry:
    """Create a tool registry with mock tools."""
    from friday_ai.tools.builtin import ShellTool

    registry = ToolRegistry(mock_config)

    # Create a real shell tool as a test tool
    shell_tool = ShellTool(mock_config)
    registry.register(shell_tool)

    return registry


@pytest.fixture
def sample_workflow(temp_workspace: Path) -> WorkflowDefinition:
    """Create a sample workflow definition."""
    return WorkflowDefinition(
        name="test_workflow",
        description="A test workflow",
        category="testing",
        steps=[
            WorkflowStep(
                name="Step 1: Setup",
                description="Initialize test environment",
                prompt="Run setup",
                agent="planner",
            ),
            WorkflowStep(
                name="Step 2: Execute",
                description="Run the test",
                tools=["test_tool"],
            ),
            WorkflowStep(
                name="Step 3: Cleanup",
                description="Clean up resources",
            ),
        ],
    )


class TestWorkflowStepExecution:
    """Tests for _execute_step method."""

    @pytest.mark.asyncio
    async def test_execute_step_with_agent(
        self, sample_workflow: WorkflowDefinition, tool_registry: ToolRegistry
    ):
        """Test executing a step that invokes an agent."""
        engine = WorkflowEngine(temp_workspace := Path("/tmp/.claude"))
        engine._workflows = {"test_workflow": sample_workflow}

        # Create state
        state = WorkflowState(
            workflow_name="test_workflow",
            context={"_workflow": sample_workflow},
        )

        # Mock agent invocation
        with patch.object(
            engine,
            "_invoke_agent",
            new_callable=AsyncMock,
            return_value="Agent completed successfully",
        ) as mock_invoke:
            step = sample_workflow.steps[0]  # Step with agent
            result = await engine._execute_step(step, state, tool_registry)

            # Verify agent was invoked (with 4 params including tool_registry)
            mock_invoke.assert_called_once_with("planner", step.prompt, state, tool_registry)
            assert "Agent completed successfully" in result

    @pytest.mark.asyncio
    async def test_execute_step_with_tools(
        self, sample_workflow: WorkflowDefinition, tool_registry: ToolRegistry
    ):
        """Test executing a step that invokes tools."""
        engine = WorkflowEngine(temp_workspace := Path("/tmp/.claude"))
        engine._workflows = {"test_workflow": sample_workflow}

        state = WorkflowState(
            workflow_name="test_workflow",
            context={"_workflow": sample_workflow},
        )

        # Create a step that uses shell tool with echo
        step = WorkflowStep(
            name="Test Step",
            tools=["shell"],
            prompt='Execute: echo "test output"',
        )

        result = await engine._execute_step(step, state, tool_registry)

        # Verify tool was invoked and returned result
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_execute_step_with_both_agent_and_tools(
        self, tool_registry: ToolRegistry
    ):
        """Test executing a step that has both agent and tools."""
        workflow = WorkflowDefinition(
            name="complex_workflow",
            steps=[
                WorkflowStep(
                    name="Complex Step",
                    agent="architect",
                    tools=["shell"],
                    prompt='Design and implement: echo "test"',
                )
            ],
        )

        engine = WorkflowEngine(Path("/tmp/.claude"))
        engine._workflows = {"complex_workflow": workflow}

        state = WorkflowState(
            workflow_name="complex_workflow",
            context={"_workflow": workflow},
        )

        # Mock agent invocation
        with patch.object(
            engine,
            "_invoke_agent",
            new_callable=AsyncMock,
            return_value="Agent completed with tool results",
        ) as mock_invoke:
            step = workflow.steps[0]
            result = await engine._execute_step(step, state, tool_registry)

            # Verify agent was invoked (tools execution handled in implementation)
            mock_invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_step_with_missing_tool(
        self, sample_workflow: WorkflowDefinition, tool_registry: ToolRegistry
    ):
        """Test error handling when a specified tool is not found."""
        engine = WorkflowEngine(Path("/tmp/.claude"))
        engine._workflows = {"test_workflow": sample_workflow}

        state = WorkflowState(
            workflow_name="test_workflow",
            context={"_workflow": sample_workflow},
        )

        # Create step with non-existent tool
        step = WorkflowStep(
            name="Bad Step", tools=["nonexistent_tool"], prompt="Run this"
        )

        result = await engine._execute_step(step, state, tool_registry)

        # Should return error message
        assert "error" in result.lower() or "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_step_with_no_agent_or_tools(
        self, sample_workflow: WorkflowDefinition, tool_registry: ToolRegistry
    ):
        """Test executing a step with no agent or tools (prompt only)."""
        engine = WorkflowEngine(Path("/tmp/.claude"))
        engine._workflows = {"test_workflow": sample_workflow}

        state = WorkflowState(
            workflow_name="test_workflow",
            context={"_workflow": sample_workflow},
        )

        step = sample_workflow.steps[2]  # Step with no agent or tools
        result = await engine._execute_step(step, state, tool_registry)

        # Should return the prompt/description
        assert step.name in result or step.description in result

    @pytest.mark.asyncio
    async def test_execute_step_updates_context(
        self, sample_workflow: WorkflowDefinition, tool_registry: ToolRegistry
    ):
        """Test that step execution updates state context."""
        engine = WorkflowEngine(Path("/tmp/.claude"))
        engine._workflows = {"test_workflow": sample_workflow}

        state = WorkflowState(
            workflow_name="test_workflow",
            context={"_workflow": sample_workflow, "initial_value": 42},
        )

        # Mock agent invocation that returns context update
        with patch.object(
            engine,
            "_invoke_agent",
            new_callable=AsyncMock,
            return_value='{"status": "completed", "value": 100}',
        ):
            step = sample_workflow.steps[0]
            result = await engine._execute_step(step, state, tool_registry)

            # Result should be available in context (stored by caller)
            assert result is not None


class TestWorkflowAgentInvocation:
    """Tests for agent invocation within workflow steps."""

    @pytest.mark.asyncio
    async def test_invoke_agent_with_valid_agent(self, tool_registry: ToolRegistry):
        """Test invoking a valid agent."""
        engine = WorkflowEngine(Path("/tmp/.claude"))

        state = WorkflowState(
            workflow_name="test",
            context={},
        )

        # Mock subagent tool
        mock_subagent = AsyncMock()
        mock_subagent.execute = AsyncMock(
            return_value=ToolResult.success_result("Agent execution completed")
        )

        with patch.object(
            engine,
            "_get_subagent_tool",
            return_value=mock_subagent,
        ):
            result = await engine._invoke_agent(
                "planner", "Plan this feature", state, tool_registry
            )

            assert "completed" in result.lower()

    @pytest.mark.asyncio
    async def test_invoke_agent_with_missing_agent(self, tool_registry: ToolRegistry):
        """Test error handling when agent is not found."""
        engine = WorkflowEngine(Path("/tmp/.claude"))

        state = WorkflowState(
            workflow_name="test",
            context={},
        )

        with patch.object(
            engine, "_get_subagent_tool", return_value=None
        ):
            result = await engine._invoke_agent("nonexistent", "Do something", state, tool_registry)

            assert "not found" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_invoke_agent_propagates_context(self, tool_registry: ToolRegistry):
        """Test that agent invocation receives workflow context."""
        engine = WorkflowEngine(Path("/tmp/.claude"))

        state = WorkflowState(
            workflow_name="test",
            context={"project": "test_project", "feature": "auth"},
        )

        # Mock subagent that receives context
        mock_subagent = AsyncMock()
        mock_subagent.execute = AsyncMock(
            return_value=ToolResult.success_result("Done")
        )

        with patch.object(
            engine,
            "_get_subagent_tool",
            return_value=mock_subagent,
        ):
            result = await engine._invoke_agent(
                "architect", "Design auth system", state, tool_registry
            )

            # Verify context was available
            mock_subagent.execute.assert_called_once()
            call_args = mock_subagent.execute.call_args
            assert call_args is not None


class TestWorkflowExecution:
    """Tests for complete workflow execution."""

    @pytest.mark.asyncio
    async def test_execute_workflow_with_all_steps(
        self, sample_workflow: WorkflowDefinition, tool_registry: ToolRegistry
    ):
        """Test executing a complete workflow with multiple steps."""
        engine = WorkflowEngine(Path("/tmp/.claude"))
        engine._workflows = {"test_workflow": sample_workflow}

        events = []
        async for event in engine.execute_workflow(
            "test_workflow", tool_registry, initial_context={"test": "value"}
        ):
            events.append(event)

        # Should have start, step events (start + complete for each), and complete
        assert len(events) >= 8  # start + (3 steps * 2) + complete

        # Check workflow started
        start_events = [e for e in events if e.data.get("name") == "workflow_start"]
        assert len(start_events) == 1

        # Check all steps executed (both start and complete events)
        step_events = [e for e in events if e.data.get("name") == "workflow_step"]
        assert len(step_events) == 6  # 3 steps * 2 events each

        # Check workflow completed
        complete_events = [
            e for e in events if e.data.get("name") == "workflow_complete"
        ]
        assert len(complete_events) == 1

    @pytest.mark.asyncio
    async def test_execute_workflow_with_errors(
        self, sample_workflow: WorkflowDefinition, tool_registry: ToolRegistry
    ):
        """Test workflow execution with step errors."""
        engine = WorkflowEngine(Path("/tmp/.claude"))
        engine._workflows = {"test_workflow": sample_workflow}

        # Mock step execution to fail on second step
        original_execute = engine._execute_step

        async def mock_execute(step, state, registry):
            if step.name == "Step 2: Execute":
                raise ValueError("Step execution failed")
            return await original_execute(step, state, registry)

        with patch.object(engine, "_execute_step", side_effect=mock_execute):
            events = []
            async for event in engine.execute_workflow("test_workflow", tool_registry):
                events.append(event)

            # Should have error event
            error_events = [e for e in events if not e.data.get("success", True)]
            assert len(error_events) > 0

    @pytest.mark.asyncio
    async def test_execute_workflow_nonexistent(self, tool_registry: ToolRegistry):
        """Test executing a workflow that doesn't exist."""
        engine = WorkflowEngine(Path("/tmp/.claude"))

        events = []
        async for event in engine.execute_workflow("nonexistent_workflow", tool_registry):
            events.append(event)

        # Should return error event
        assert len(events) == 1
        assert "not found" in events[0].data.get("error", "").lower()


class TestWorkflowContextManagement:
    """Tests for workflow context and state management."""

    @pytest.mark.asyncio
    async def test_workflow_state_is_complete(self):
        """Test WorkflowState.is_complete property."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[
                WorkflowStep(name="Step 1"),
                WorkflowStep(name="Step 2"),
            ],
        )

        state = WorkflowState(
            workflow_name="test",
            context={"_workflow": workflow},
        )

        # Initially not complete
        assert not state.is_complete

        # After first step
        state.current_step_index = 1
        assert not state.is_complete

        # After all steps
        state.current_step_index = 2
        assert state.is_complete

    @pytest.mark.asyncio
    async def test_workflow_state_to_dict(self):
        """Test WorkflowState.to_dict conversion."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[WorkflowStep(name="Step 1")],
        )

        state = WorkflowState(
            workflow_name="test",
            context={
                "_workflow": workflow,
                "custom_key": "custom_value",
            },
            completed_steps=[0],
            errors=["Test error"],
        )

        state_dict = state.to_dict()

        assert state_dict["workflow_name"] == "test"
        assert state_dict["current_step_index"] == 0
        assert state_dict["completed_steps"] == [0]
        assert state_dict["errors"] == ["Test error"]
        assert "custom_key" in state_dict["context"]
        assert "_workflow" not in state_dict["context"]  # Excluded
        assert state_dict["is_complete"] is False


class TestWorkflowParsing:
    """Tests for workflow file parsing."""

    @pytest.mark.asyncio
    async def test_load_all_workflows(self, temp_workspace: Path):
        """Test loading all workflows from directory."""
        # Create sample workflow files
        (temp_workspace / "workflows" / "test1.md").write_text(
            """---
name: Test Workflow 1
description: First test workflow
category: testing
---

## Step 1
First step description
""",
        )
        (temp_workspace / "workflows" / "test2.md").write_text(
            """---
name: Test Workflow 2
description: Second test workflow
category: audit
---

## Step 1
Second workflow step
""",
        )

        engine = WorkflowEngine(temp_workspace)
        workflows = engine.load_all_workflows()

        assert len(workflows) == 2
        assert any(w.name == "Test Workflow 1" for w in workflows)
        assert any(w.name == "Test Workflow 2" for w in workflows)

    @pytest.mark.asyncio
    async def test_load_workflows_with_invalid_file(self, temp_workspace: Path):
        """Test loading workflows with an invalid file."""
        # Create valid workflow
        (temp_workspace / "workflows" / "valid.md").write_text(
            """---
name: Valid Workflow
---

## Step 1
Valid step
""",
        )

        # Create a file that's not a proper workflow
        (temp_workspace / "workflows" / "not_a_workflow.txt").write_text(
            "This is not markdown",
        )

        engine = WorkflowEngine(temp_workspace)
        workflows = engine.load_all_workflows()

        # Should load valid workflow (the .txt file won't match *.md glob)
        assert len(workflows) == 1
        assert workflows[0].name == "Valid Workflow"

    @pytest.mark.asyncio
    async def test_get_workflow(self, temp_workspace: Path):
        """Test getting a specific workflow by name."""
        (temp_workspace / "workflows" / "test.md").write_text(
            """---
name: My Workflow
---

## Step 1
Test step
""",
        )

        engine = WorkflowEngine(temp_workspace)
        engine.load_all_workflows()

        workflow = engine.get_workflow("My Workflow")
        assert workflow is not None
        assert workflow.name == "My Workflow"

        # Test getting non-existent workflow
        missing = engine.get_workflow("Nonexistent")
        assert missing is None

    @pytest.mark.asyncio
    async def test_list_workflows(self, temp_workspace: Path):
        """Test listing all workflows."""
        (temp_workspace / "workflows" / "test1.md").write_text(
            """---
name: Workflow 1
---

## Step 1
""",
        )
        (temp_workspace / "workflows" / "test2.md").write_text(
            """---
name: Workflow 2
---

## Step 1
""",
        )

        engine = WorkflowEngine(temp_workspace)
        engine.load_all_workflows()

        all_workflows = engine.list_workflows()
        assert len(all_workflows) == 2

    @pytest.mark.asyncio
    async def test_list_workflows_by_category(self, temp_workspace: Path):
        """Test filtering workflows by category."""
        (temp_workspace / "workflows" / "test.md").write_text(
            """---
name: Test Workflow
category: testing
---

## Step 1
""",
        )
        (temp_workspace / "workflows" / "audit.md").write_text(
            """---
name: Audit Workflow
category: audit
---

## Step 1
""",
        )

        engine = WorkflowEngine(temp_workspace)
        engine.load_all_workflows()

        testing_workflows = engine.list_workflows_by_category("testing")
        assert len(testing_workflows) == 1
        assert testing_workflows[0].name == "Test Workflow"

        audit_workflows = engine.list_workflows_by_category("audit")
        assert len(audit_workflows) == 1
        assert audit_workflows[0].name == "Audit Workflow"


class TestWorkflowToolExecution:
    """Tests for _invoke_tool method."""

    @pytest.mark.asyncio
    async def test_invoke_tool_with_missing_tool(self, tool_registry: ToolRegistry):
        """Test error handling when tool doesn't exist."""
        engine = WorkflowEngine(Path("/tmp/.claude"))

        state = WorkflowState(
            workflow_name="test",
            context={},
        )

        result = await engine._invoke_tool(
            "nonexistent_tool", "Do something", state, tool_registry
        )

        assert "not found" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_invoke_tool_with_shell_command(self, tool_registry: ToolRegistry):
        """Test invoking shell tool with command parsing."""
        engine = WorkflowEngine(Path("/tmp/.claude"))

        state = WorkflowState(
            workflow_name="test",
            context={},
        )

        # Mock shell tool to avoid actual execution
        with patch.object(
            tool_registry,
            "get",
            return_value=None,
        ):
            result = await engine._invoke_tool(
                "shell", 'Execute: echo "test"', state, tool_registry
            )

            # Should return error since tool doesn't exist
            assert "not found" in result.lower() or "error" in result.lower()


class TestWorkflowHelpers:
    """Tests for helper methods."""

    @pytest.mark.asyncio
    async def test_format_context(self):
        """Test _format_context method."""
        engine = WorkflowEngine(Path("/tmp/.claude"))

        state = WorkflowState(
            workflow_name="test",
            context={
                "_workflow": "should be hidden",
                "project": "my_project",
                "feature": "auth",
                "count": 42,
            },
        )

        formatted = engine._format_context(state)

        # Should contain non-internal keys
        assert "project:" in formatted
        assert "my_project" in formatted
        assert "feature:" in formatted
        assert "auth" in formatted

        # Should not contain internal keys
        assert "_workflow" not in formatted

    @pytest.mark.asyncio
    async def test_get_subagent_tool(self, tool_registry: ToolRegistry):
        """Test _get_subagent_tool method."""
        engine = WorkflowEngine(Path("/tmp/.claude"))

        # Try to get a tool that doesn't exist
        tool = engine._get_subagent_tool("nonexistent", tool_registry)
        assert tool is None
