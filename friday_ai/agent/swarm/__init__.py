"""Agent Orchestration - Swarm mode and hierarchical agents."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Any, Dict
import logging

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Roles for hierarchical agents."""

    ARCHITECT = "architect"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    COORDINATOR = "coordinator"


@dataclass
class Task:
    """A task to be executed by an agent."""

    id: str
    description: str
    role: AgentRole
    priority: int = 0
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Any] = None
    assigned_to: Optional[str] = None
    created_at: float = 0.0


class SwarmCoordinator:
    """Coordinator for swarm mode (multiple parallel agents)."""

    # FIX-009: Maximum results to keep in memory
    MAX_RESULTS_SIZE = 1000

    def __init__(self, max_agents: int = 4):
        """Initialize the coordinator.

        Args:
            max_agents: Maximum number of parallel agents.
        """
        self.max_agents = max_agents
        self.tasks: dict[str, Task] = {}
        self.agents: dict[str, Any] = {}  # Agent instances
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.results: dict[str, Any] = {}

    def add_task(self, task: Task) -> None:
        """Add a task to the swarm.

        Args:
            task: Task to add.
        """
        self.tasks[task.id] = task
        logger.info(f"Added task: {task.id} - {task.description}")

    async def run_swarm(self) -> dict:
        """Execute all tasks in parallel.

        Returns:
            Dictionary of task results.
        """
        # Add all tasks to queue
        for task_id, task in self.tasks.items():
            await self.task_queue.put(task)

        # Create worker tasks
        workers = []
        for i in range(min(self.max_agents, len(self.tasks))):
            worker = asyncio.create_task(self._worker(i))
            workers.append(worker)

        # Wait for all workers to complete
        await self.task_queue.join()
        for worker in workers:
            worker.cancel()

        return self.results

    async def _worker(self, worker_id: int) -> None:
        """Worker task that processes the queue.

        Args:
            worker_id: ID of this worker.
        """
        while True:
            try:
                task = await self.task_queue.get()
                logger.info(f"Worker {worker_id} processing task: {task.id}")

                # Check dependencies
                if task.dependencies:
                    await self._wait_for_dependencies(task.dependencies)

                # Execute task
                result = await self._execute_task(task)

                self.results[task.id] = result
                task.status = "completed"
                task.result = result

                # FIX-009: Limit results dictionary size to prevent unbounded growth
                if len(self.results) > self.MAX_RESULTS_SIZE:
                    # Remove oldest 20% of results
                    keys_to_remove = list(self.results.keys())[:self.MAX_RESULTS_SIZE // 5]
                    for key in keys_to_remove:
                        del self.results[key]

                logger.info(f"Worker {worker_id} completed task: {task.id}")
                self.task_queue.task_done()

            except asyncio.CancelledError:
                break

    async def _wait_for_dependencies(self, dependencies: list[str]) -> None:
        """Wait for dependent tasks to complete.

        Args:
            dependencies: List of task IDs to wait for.
        """
        for dep_id in dependencies:
            while dep_id not in self.results:
                await asyncio.sleep(0.1)

    async def _execute_task(self, task: Task) -> Any:
        """Execute a task using role-based agent delegation.

        Args:
            task: Task to execute.

        Returns:
            Task result.
        """
        # Map task role to appropriate agent execution strategy
        role_handlers = {
            AgentRole.ARCHITECT: self._execute_architect_task,
            AgentRole.CODER: self._execute_coder_task,
            AgentRole.TESTER: self._execute_tester_task,
            AgentRole.REVIEWER: self._execute_reviewer_task,
            AgentRole.RESEARCHER: self._execute_researcher_task,
            AgentRole.COORDINATOR: self._execute_coordinator_task,
        }

        handler = role_handlers.get(task.role)
        if not handler:
            logger.warning(f"No handler for role: {task.role}")
            return {
                "status": "failed",
                "task": task.id,
                "error": f"No handler for role: {task.role}"
            }

        try:
            result = await handler(task)
            return {
                "status": "completed",
                "task": task.id,
                "role": task.role.value,
                "output": result
            }
        except Exception as e:
            logger.error(f"Task {task.id} execution failed: {e}")
            return {
                "status": "failed",
                "task": task.id,
                "error": str(e)
            }

    async def _execute_architect_task(self, task: Task) -> str:
        """Execute architect-level task.

        Args:
            task: Task to execute.

        Returns:
            Task result string.
        """
        # In production, this would call architect agent
        logger.info(f"Executing architect task: {task.description}")
        return f"Architectural design for: {task.description}"

    async def _execute_coder_task(self, task: Task) -> str:
        """Execute coding task.

        Args:
            task: Task to execute.

        Returns:
            Task result string.
        """
        # In production, this would call coder agent
        logger.info(f"Executing coding task: {task.description}")
        return f"Code implementation for: {task.description}"

    async def _execute_tester_task(self, task: Task) -> str:
        """Execute testing task.

        Args:
            task: Task to execute.

        Returns:
            Task result string.
        """
        # In production, this would call tester agent
        logger.info(f"Executing testing task: {task.description}")
        return f"Tests for: {task.description}"

    async def _execute_reviewer_task(self, task: Task) -> str:
        """Execute review task.

        Args:
            task: Task to execute.

        Returns:
            Task result string.
        """
        # In production, this would call reviewer agent
        logger.info(f"Executing review task: {task.description}")
        return f"Review completed for: {task.description}"

    async def _execute_researcher_task(self, task: Task) -> str:
        """Execute research task.

        Args:
            task: Task to execute.

        Returns:
            Task result string.
        """
        # In production, this would call researcher agent
        logger.info(f"Executing research task: {task.description}")
        return f"Research results for: {task.description}"

    async def _execute_coordinator_task(self, task: Task) -> str:
        """Execute coordination task.

        Args:
            task: Task to execute.

        Returns:
            Task result string.
        """
        # In production, this would call coordinator agent
        logger.info(f"Executing coordination task: {task.description}")
        return f"Coordination completed for: {task.description}"


class HierarchicalAgent:
    """Hierarchical agent with specialized sub-agents."""

    def __init__(self):
        """Initialize the hierarchical agent."""
        self.role = AgentRole.COORDINATOR
        self.sub_agents: dict[AgentRole, Any] = {}

    def register_sub_agent(self, role: AgentRole, agent: Any) -> None:
        """Register a sub-agent for a specific role.

        Args:
            role: Agent role.
            agent: Agent instance.
        """
        self.sub_agents[role] = agent
        logger.info(f"Registered {role.value} agent")

    async def execute(self, task: Task) -> dict:
        """Execute a task using appropriate sub-agent.

        Args:
            task: Task to execute.

        Returns:
            Task result.
        """
        agent = self.sub_agents.get(task.role)
        if not agent:
            return {"error": f"No agent registered for role: {task.role}"}

        return await agent.execute(task)


class TaskDistributor:
    """Distributes tasks among agents based on role and load."""

    def __init__(self):
        """Initialize the distributor."""
        self.agents: dict[str, dict] = {}
        self.queues: dict[AgentRole, list[str]] = {role: [] for role in AgentRole}

    def register_agent(self, agent_id: str, roles: list[AgentRole], capacity: int = 10) -> None:
        """Register an agent.

        Args:
            agent_id: Unique agent identifier.
            roles: List of roles this agent can perform.
            capacity: Maximum concurrent tasks.
        """
        self.agents[agent_id] = {
            "roles": roles,
            "capacity": capacity,
            "current_load": 0,
        }
        logger.info(f"Registered agent: {agent_id} with roles: {[r.value for r in roles]}")

    async def distribute_task(self, task: Task) -> Optional[str]:
        """Distribute a task to an available agent.

        Args:
            task: Task to distribute.

        Returns:
            Agent ID that accepted the task, or None.
        """
        # Find agents that can perform this role
        eligible = [
            (aid, info) for aid, info in self.agents.items()
            if task.role in info["roles"] and info["current_load"] < info["capacity"]
        ]

        if not eligible:
            return None

        # Select agent with lowest load
        eligible.sort(key=lambda x: x[1]["current_load"])
        agent_id, info = eligible[0]

        # Assign task
        info["current_load"] += 1
        self.queues[task.role].append(agent_id)

        logger.info(f"Distributed task {task.id} to agent {agent_id}")
        return agent_id

    def complete_task(self, agent_id: str) -> None:
        """Mark a task as complete for an agent.

        Args:
            agent_id: Agent that completed a task.
        """
        if agent_id in self.agents:
            self.agents[agent_id]["current_load"] = max(0, self.agents[agent_id]["current_load"] - 1)

    def get_status(self) -> dict:
        """Get status of all agents.

        Returns:
            Status dictionary.
        """
        return {
            "total_agents": len(self.agents),
            "agents": {
                aid: {
                    "roles": [r.value for r in info["roles"]],
                    "capacity": info["capacity"],
                    "current_load": info["current_load"],
                    "available": info["current_load"] < info["capacity"],
                }
                for aid, info in self.agents.items()
            },
        }


class AgentSwarmManager:
    """Manager for coordinating agent swarms."""

    def __init__(self, max_parallel: int = 4):
        """Initialize the swarm manager.

        Args:
            max_parallel: Maximum parallel tasks.
        """
        self.coordinator = SwarmCoordinator(max_agents=max_parallel)
        self.distributor = TaskDistributor()
        self.hierarchical = HierarchicalAgent()

    async def create_swarm_from_task(
        self,
        description: str,
        sub_tasks: list[dict],
    ) -> dict:
        """Create a swarm to execute subtasks in parallel.

        Args:
            description: Overall task description.
            sub_tasks: List of subtask definitions.

        Returns:
            Swarm execution results.
        """
        # Create tasks from subtask definitions
        for i, st in enumerate(sub_tasks):
            task = Task(
                id=f"swarm_task_{i}",
                description=st.get("description", f"Subtask {i}"),
                role=AgentRole(st.get("role", "coder")),
                priority=st.get("priority", 0),
                dependencies=st.get("dependencies", []),
            )
            self.coordinator.add_task(task)

        # Run swarm
        results = await self.coordinator.run_swarm()

        return {
            "description": description,
            "total_tasks": len(sub_tasks),
            "results": results,
        }

    def setup_hierarchical_team(
        self,
        architect: Optional[Any] = None,
        coder: Optional[Any] = None,
        tester: Optional[Any] = None,
        reviewer: Optional[Any] = None,
    ) -> None:
        """Set up a hierarchical team of agents.

        Args:
            architect: Architecture agent.
            coder: Coding agent.
            tester: Testing agent.
            reviewer: Review agent.
        """
        if architect:
            self.hierarchical.register_sub_agent(AgentRole.ARCHITECT, architect)
        if coder:
            self.hierarchical.register_sub_agent(AgentRole.CODER, coder)
        if tester:
            self.hierarchical.register_sub_agent(AgentRole.TESTER, tester)
        if reviewer:
            self.hierarchical.register_sub_agent(AgentRole.REVIEWER, reviewer)

    async def execute_hierarchical(
        self,
        task: dict,
    ) -> dict:
        """Execute task using hierarchical agents.

        Args:
            task: Task definition.

        Returns:
            Task result.
        """
        # Create task
        t = Task(
            id=task.get("id", "hierarchical_task"),
            description=task.get("description", ""),
            role=AgentRole(task.get("role", "coder")),
        )

        # Execute through hierarchical agent
        return await self.hierarchical.execute(t)

    def get_swarm_status(self) -> dict:
        """Get overall swarm status.

        Returns:
            Status dictionary.
        """
        return {
            "coordinator": {
                "total_tasks": len(self.coordinator.tasks),
                "completed_tasks": len(self.coordinator.results),
                "max_agents": self.coordinator.max_agents,
            },
            "distributor": self.distributor.get_status(),
            "hierarchical": {
                "registered_roles": [r.value for r in self.hierarchical.sub_agents.keys()],
            },
        }
