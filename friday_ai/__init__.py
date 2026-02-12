"""Friday AI Teammate - Your AI coding assistant in the terminal."""

__version__ = "2.0.0"
__author__ = "mk-knight23"

# Core exports
from friday_ai.client import (
    LLMClient,
    ProviderRouter,
    ProviderManager,
    TaskComplexity,
    ProviderType,
    StreamEvent,
    TokenUsage,
)

from friday_ai.agent.autonomous import (
    Goal,
    GoalStatus,
    GoalType,
    GoalTracker,
    SelfHealer,
    ErrorRecovery,
)

from friday_ai.agent.swarm import (
    SwarmCoordinator,
    HierarchicalAgent,
    TaskDistributor,
    AgentSwarmManager,
    AgentRole,
)

from friday_ai.intelligence import (
    CodebaseRAG,
    CodebaseQA,
)

from friday_ai.devops import (
    K8sClient,
    K8sConfig,
)

__all__ = [
    # Version
    "__version__",
    # Client
    "LLMClient",
    "ProviderRouter",
    "ProviderManager",
    "TaskComplexity",
    "ProviderType",
    # Autonomous
    "Goal",
    "GoalStatus",
    "GoalType",
    "GoalTracker",
    "SelfHealer",
    "ErrorRecovery",
    # Swarm
    "SwarmCoordinator",
    "HierarchicalAgent",
    "TaskDistributor",
    "AgentSwarmManager",
    "AgentRole",
    # Intelligence
    "CodebaseRAG",
    "CodebaseQA",
    # DevOps
    "K8sClient",
    "K8sConfig",
]
