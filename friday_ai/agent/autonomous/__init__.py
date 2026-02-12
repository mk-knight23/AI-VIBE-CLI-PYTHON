"""Friday AI Autonomous Mode package."""

from friday_ai.agent.autonomous.goals import (
    Goal,
    GoalStatus,
    GoalType,
    GoalProgress,
    GoalParser,
    GoalTracker,
)
from friday_ai.agent.autonomous.self_healing import (
    ErrorType,
    ErrorInfo,
    SelfHealer,
    ErrorRecovery,
)

__all__ = [
    # Goals
    "Goal",
    "GoalStatus",
    "GoalType",
    "GoalProgress",
    "GoalParser",
    "GoalTracker",
    # Self-healing
    "ErrorType",
    "ErrorInfo",
    "SelfHealer",
    "ErrorRecovery",
]
