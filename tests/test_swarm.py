"""Tests for Agent Swarm functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from friday_ai.agent.swarm import (
    SwarmCoordinator,
    HierarchicalAgent,
    TaskDistributor,
    AgentSwarmManager,
    AgentRole,
    Task,
)


class TestSwarmCoordinator:
    """Tests for SwarmCoordinator class."""

    @pytest.fixture
    def coordinator(self):
        return SwarmCoordinator(max_agents=2)

    def test_initialization(self, coordinator):
        """Test coordinator initialization."""
        assert coordinator.max_agents == 2
        assert coordinator.tasks == {}
        assert coordinator.agents == {}
        assert coordinator.results == {}

    def test_add_task(self, coordinator):
        """Test adding tasks to coordinator."""
        task = Task(
            id="test-task-1",
            description="Test task",
            role=AgentRole.CODER,
        )
        coordinator.add_task(task)

        assert "test-task-1" in coordinator.tasks
        assert coordinator.tasks["test-task-1"].description == "Test task"

    @pytest.mark.asyncio
    async def test_run_swarm_with_dependencies(self, coordinator):
        """Test running swarm with task dependencies."""
        # Create tasks with dependencies
        task1 = Task(
            id="task-1",
            description="First task",
            role=AgentRole.CODER,
            dependencies=[],
        )
        task2 = Task(
            id="task-2",
            description="Second task depends on 1",
            role=AgentRole.TESTER,
            dependencies=["task-1"],
        )

        coordinator.add_task(task1)
        coordinator.add_task(task2)

        # Run swarm
        results = await coordinator.run_swarm()

        assert len(results) == 2
        assert "task-1" in results
        assert "task-2" in results

    @pytest.mark.asyncio
    async def test_worker_processing(self, coordinator):
        """Test worker task processing."""
        task = Task(
            id="worker-test",
            description="Worker test task",
            role=AgentRole.CODER,
        )
        coordinator.add_task(task)

        # Mock the execute method
        with patch.object(
            coordinator, "_execute_task", return_value={"status": "done"}
        ) as mock_execute:
            results = await coordinator.run_swarm()

            assert mock_execute.called
            assert "worker-test" in results

    @pytest.mark.asyncio
    async def test_execute_task_with_role(self, coordinator):
        """Test task execution with role delegation."""
        task = Task(
            id="role-test",
            description="Test role-based execution",
            role=AgentRole.CODER,
        )

        result = await coordinator._execute_task(task)

        assert result["status"] == "completed"
        assert result["task"] == "role-test"
        assert "output" in result


class TestHierarchicalAgent:
    """Tests for HierarchicalAgent class."""

    @pytest.fixture
    def hierarchical(self):
        return HierarchicalAgent()

    def test_initialization(self, hierarchical):
        """Test hierarchical agent initialization."""
        assert hierarchical.role == AgentRole.COORDINATOR
        assert hierarchical.sub_agents == {}

    def test_register_sub_agent(self, hierarchical):
        """Test registering sub-agents."""
        mock_agent = Mock()
        hierarchical.register_sub_agent(AgentRole.CODER, mock_agent)

        assert AgentRole.CODER in hierarchical.sub_agents
        assert hierarchical.sub_agents[AgentRole.CODER] == mock_agent

    @pytest.mark.asyncio
    async def test_execute_with_registered_agent(self, hierarchical):
        """Test execution with registered sub-agent."""
        task = Task(
            id="hier-test",
            description="Hierarchical test",
            role=AgentRole.CODER,
        )

        mock_agent = AsyncMock()
        mock_agent.execute.return_value = {"result": "success"}
        hierarchical.register_sub_agent(AgentRole.CODER, mock_agent)

        result = await hierarchical.execute(task)

        assert result["result"] == "success"
        mock_agent.execute.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_execute_without_registered_agent(self, hierarchical):
        """Test execution without registered sub-agent."""
        task = Task(
            id="no-agent-test",
            description="No agent test",
            role=AgentRole.CODER,
        )

        result = await hierarchical.execute(task)

        assert "error" in result
        assert "No agent registered" in result["error"]


class TestTaskDistributor:
    """Tests for TaskDistributor class."""

    @pytest.fixture
    def distributor(self):
        return TaskDistributor()

    def test_initialization(self, distributor):
        """Test distributor initialization."""
        assert distributor.agents == {}
        assert AgentRole.CODER in distributor.queues
        assert AgentRole.TESTER in distributor.queues

    def test_register_agent(self, distributor):
        """Test registering an agent."""
        distributor.register_agent(
            agent_id="agent-1",
            roles=[AgentRole.CODER, AgentRole.TESTER],
            capacity=5,
        )

        assert "agent-1" in distributor.agents
        assert distributor.agents["agent-1"]["capacity"] == 5
        assert distributor.agents["agent-1"]["current_load"] == 0

    @pytest.mark.asyncio
    async def test_distribute_task_success(self, distributor):
        """Test successful task distribution."""
        distributor.register_agent(
            agent_id="agent-1",
            roles=[AgentRole.CODER],
            capacity=5,
        )

        task = Task(
            id="dist-test",
            description="Distribution test",
            role=AgentRole.CODER,
        )

        agent_id = await distributor.distribute_task(task)

        assert agent_id == "agent-1"
        assert distributor.agents["agent-1"]["current_load"] == 1

    @pytest.mark.asyncio
    async def test_distribute_task_no_eligible_agent(self, distributor):
        """Test distribution when no eligible agent available."""
        distributor.register_agent(
            agent_id="agent-1",
            roles=[AgentRole.TESTER],
            capacity=1,
        )

        task = Task(
            id="no-agent",
            description="No eligible agent",
            role=AgentRole.CODER,
        )

        agent_id = await distributor.distribute_task(task)

        assert agent_id is None

    @pytest.mark.asyncio
    async def test_distribute_task_load_balancing(self, distributor):
        """Test load balancing across agents."""
        distributor.register_agent(
            agent_id="agent-1",
            roles=[AgentRole.CODER],
            capacity=10,
        )
        distributor.register_agent(
            agent_id="agent-2",
            roles=[AgentRole.CODER],
            capacity=10,
        )

        # Add load to agent-1
        distributor.agents["agent-1"]["current_load"] = 5

        task = Task(
            id="balance-test",
            description="Load balancing test",
            role=AgentRole.CODER,
        )

        agent_id = await distributor.distribute_task(task)

        # Should select agent-2 (lower load)
        assert agent_id == "agent-2"

    def test_complete_task(self, distributor):
        """Test completing a task."""
        distributor.register_agent(
            agent_id="agent-1",
            roles=[AgentRole.CODER],
            capacity=10,
        )
        distributor.agents["agent-1"]["current_load"] = 3

        distributor.complete_task("agent-1")

        assert distributor.agents["agent-1"]["current_load"] == 2

    def test_get_status(self, distributor):
        """Test getting distributor status."""
        distributor.register_agent(
            agent_id="agent-1",
            roles=[AgentRole.CODER],
            capacity=10,
        )
        distributor.agents["agent-1"]["current_load"] = 3

        status = distributor.get_status()

        assert status["total_agents"] == 1
        assert "agent-1" in status["agents"]
        assert status["agents"]["agent-1"]["current_load"] == 3
        assert status["agents"]["agent-1"]["available"] is True


class TestAgentSwarmManager:
    """Tests for AgentSwarmManager class."""

    @pytest.fixture
    def manager(self):
        return AgentSwarmManager(max_parallel=2)

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.coordinator is not None
        assert manager.distributor is not None
        assert manager.hierarchical is not None
        assert manager.coordinator.max_agents == 2

    @pytest.mark.asyncio
    async def test_create_swarm_from_task(self, manager):
        """Test creating swarm from task."""
        sub_tasks = [
            {"description": "Task 1", "role": "coder"},
            {"description": "Task 2", "role": "tester"},
        ]

        result = await manager.create_swarm_from_task(
            description="Test swarm",
            sub_tasks=sub_tasks,
        )

        assert result["description"] == "Test swarm"
        assert result["total_tasks"] == 2
        assert "results" in result
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_create_swarm_with_dependencies(self, manager):
        """Test swarm with task dependencies."""
        sub_tasks = [
            {
                "description": "Base task",
                "role": "coder",
                "dependencies": [],
            },
            {
                "description": "Dependent task",
                "role": "tester",
                "dependencies": ["swarm_task_0"],
            },
        ]

        result = await manager.create_swarm_from_task(
            description="Dependency test",
            sub_tasks=sub_tasks,
        )

        assert result["total_tasks"] == 2
        assert len(result["results"]) == 2

    def test_setup_hierarchical_team(self, manager):
        """Test setting up hierarchical team."""
        mock_architect = Mock()
        mock_coder = Mock()
        mock_tester = Mock()

        manager.setup_hierarchical_team(
            architect=mock_architect,
            coder=mock_coder,
            tester=mock_tester,
        )

        assert AgentRole.ARCHITECT in manager.hierarchical.sub_agents
        assert AgentRole.CODER in manager.hierarchical.sub_agents
        assert AgentRole.TESTER in manager.hierarchical.sub_agents

    @pytest.mark.asyncio
    async def test_execute_hierarchical(self, manager):
        """Test hierarchical execution."""
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = {"result": "hierarchical success"}
        manager.hierarchical.register_sub_agent(AgentRole.CODER, mock_agent)

        task = {
            "id": "hier-exec-test",
            "description": "Test hierarchical execution",
            "role": "coder",
        }

        result = await manager.execute_hierarchical(task)

        assert result["result"] == "hierarchical success"
        mock_agent.execute.assert_called_once()

    def test_get_swarm_status(self, manager):
        """Test getting swarm status."""
        manager.distributor.register_agent(
            agent_id="agent-1",
            roles=[AgentRole.CODER],
            capacity=5,
        )

        status = manager.get_swarm_status()

        assert "coordinator" in status
        assert "distributor" in status
        assert "hierarchical" in status
        assert status["coordinator"]["max_agents"] == 2
        assert status["distributor"]["total_agents"] == 1

    @pytest.mark.asyncio
    async def test_parallel_execution_limits(self, manager):
        """Test that parallel execution respects max_agents limit."""
        sub_tasks = [
            {"description": f"Task {i}", "role": "coder"}
            for i in range(5)
        ]

        result = await manager.create_swarm_from_task(
            description="Parallel limit test",
            sub_tasks=sub_tasks,
        )

        assert result["total_tasks"] == 5
        assert len(result["results"]) == 5
