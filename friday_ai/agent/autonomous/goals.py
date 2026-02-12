"""Goal Parser and Tracker for autonomous mode."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GoalStatus(Enum):
    """Status of a goal."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class GoalType(Enum):
    """Types of goals."""

    CODING = "coding"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    ARCHITECTURE = "architecture"
    DEPLOYMENT = "deployment"
    ANALYSIS = "analysis"


@dataclass
class Goal:
    """A single goal in an autonomous session."""

    id: str
    description: str
    goal_type: GoalType
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 0  # 0 = highest, 10 = lowest
    subtasks: list["Goal"] = field(default_factory=list)
    parent_id: Optional[str] = None
    success_criteria: list[str] = field(default_factory=list)
    completion_signals: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    notes: str = ""
    iterations: int = 0
    max_iterations: int = 50


@dataclass
class GoalProgress:
    """Progress information for a goal."""

    goal_id: str
    status: GoalStatus
    completed_steps: int = 0
    total_steps: int = 0
    percentage: float = 0.0
    last_action: str = ""
    blockers: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class GoalParser:
    """Parser for natural language goals."""

    # Goal type patterns
    GOAL_TYPE_PATTERNS = {
        GoalType.CODING: [
            r"(?:create|build|implement|write|add|develop)\s+(?:a\s+)?(?:new\s+)?(?:feature|function|method|class|module|component|api|endpoint|service)",
            r"(?:write|create)\s+code",
            r"(?:implement|build)\s+.*(?:functionality|feature|module)",
        ],
        GoalType.REFACTORING: [
            r"(?:refactor|restructure|reorganize|rewrite)\s+(?:the\s+)?(?:code|class|function|module)",
            r"(?:improve|optimize|clean)\s+(?:up\s+)?(?:the\s+)?(?:code|structure)",
            r"(?:make|keep).*?clean",
        ],
        GoalType.DEBUGGING: [
            r"(?:debug|fix|resolve|troubleshoot|investigate)\s+(?:the\s+)?(?:bug|issue|error|problem|failure|crash)",
            r"(?:find|identify|locate)\s+(?:the\s+)?(?:bug|issue|error|problem)",
            r"(?:something.*?wrong|not.*?working|broken)",
        ],
        GoalType.TESTING: [
            r"(?:write|create|add|implement)\s+(?:unit|integration|e2e|end-to-end|test|tests)",
            r"(?:test|verify|validate|check)\s+(?:the\s+)?(?:code|functionality|feature|behavior)",
            r"(?:run|execute)\s+(?:the\s+)?tests",
        ],
        GoalType.DOCUMENTATION: [
            r"(?:write|create|add|update|generate|document)\s+(?:the\s+)?(?:docs?|documentation|readme|comments)",
            r"(?:document|explain|describe)\s+(?:the\s+)?(?:code|function|feature|api)",
        ],
        GoalType.RESEARCH: [
            r"(?:research|investigate|explore|look\s+up|find\s+out|learn\s+about)",
            r"(?:look\s+for|search\s+for|find)\s+(?:information|docs?|tutorials?|examples?|best\s+practices?)",
            r"(?:how\s+to|what\s+is|what\s+are|explain)",
        ],
        GoalType.ARCHITECTURE: [
            r"(?:design|plan|architect|structure)\s+(?:the\s+)?(?:system|application|architecture|structure|layout)",
            r"(?:create|define)\s+(?:the\s+)?(?:architecture|design|structure|blueprint)",
        ],
        GoalType.DEPLOYMENT: [
            r"(?:deploy|release|ship|publish|push)\s+(?:to|on|into)",
            r"(?:set\s+up|configure|provision)\s+(?:the\s+)?(?:infrastructure|environment|ci/cd|pipeline)",
        ],
        GoalType.ANALYSIS: [
            r"(?:analyze|review|audit|assess|evaluate|examine|inspect|check)\s+(?:the\s+)?(?:code|security|performance|quality|structure)",
            r"(?:code\s+review|security\s+audit|performance\s+analysis)",
        ],
    }

    # Priority indicators
    PRIORITY_PATTERNS = {
        0: [r"urgent|critical|must\s+have|immediately"],
        1: [r"high\s+priority|important|asap"],
        3: [r"normal|regular|standard"],
        7: [r"low\s+priority|optional|nice\s+to\s+have"],
        10: [r"whenever|future|later"],
    }

    def __init__(self):
        """Initialize the goal parser."""
        self._compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        for goal_type, patterns in self.GOAL_TYPE_PATTERNS.items():
            compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
            self._compiled_patterns[goal_type] = compiled

        for priority, patterns in self.PRIORITY_PATTERNS.items():
            compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
            self._compiled_patterns[f"priority_{priority}"] = compiled

    def parse_goal(self, description: str) -> Goal:
        """Parse a natural language goal description.

        Args:
            description: Natural language description.

        Returns:
            Parsed Goal object.
        """
        # Detect goal type
        goal_type = self._detect_goal_type(description)

        # Detect priority
        priority = self._detect_priority(description)

        # Generate goal ID
        goal_id = self._generate_goal_id(description)

        # Extract success criteria
        success_criteria = self._extract_success_criteria(description)

        # Detect completion signals
        completion_signals = self._detect_completion_signals(description)

        return Goal(
            id=goal_id,
            description=description,
            goal_type=goal_type,
            priority=priority,
            success_criteria=success_criteria,
            completion_signals=completion_signals,
        )

    def _detect_goal_type(self, description: str) -> GoalType:
        """Detect the type of goal from description.

        Args:
            description: Goal description.

        Returns:
            Detected goal type.
        """
        for goal_type, patterns in self._compiled_patterns.items():
            if goal_type.startswith("priority_"):
                continue
            for pattern in patterns:
                if pattern.search(description):
                    return goal_type
        return GoalType.CODING  # Default to coding

    def _detect_priority(self, description: str) -> int:
        """Detect priority from description.

        Args:
            description: Goal description.

        Returns:
            Priority level (0-10).
        """
        for priority in range(11):
            patterns = self._compiled_patterns.get(f"priority_{priority}", [])
            for pattern in patterns:
                if pattern.search(description):
                    return priority
        return 3  # Default priority

    def _generate_goal_id(self, description: str) -> str:
        """Generate a unique goal ID.

        Args:
            description: Goal description.

        Returns:
            Unique goal ID.
        """
        # Create a short hash from the description
        words = description.lower()[:20].split()[:5]
        base_id = "_".join(words)
        # Add a timestamp-based suffix
        import time
        suffix = str(int(time.time()))[-6:]
        return f"goal_{base_id}_{suffix}"

    def _extract_success_criteria(self, description: str) -> list[str]:
        """Extract success criteria from description.

        Args:
            description: Goal description.

        Returns:
            List of success criteria.
        """
        criteria = []

        # Look for "should", "must", "needs to" patterns
        patterns = [
            r"(?:should|must|needs?\.?)\s+(?:be\s+)?(.+?)(?:\.|$)",
            r"(?:so\s+that|to\s+ensure|make\s+sure)\s+(.+?)(?:\.|$)",
            r"(?:the\s+)?(?:goal|objective|result)\s+(?:is|should|is\s+to)\s+(.+?)(?:\.|$)",
        ]

        import re
        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            criteria.extend(matches)

        return criteria

    def _detect_completion_signals(self, description: str) -> list[str]:
        """Detect completion signals for the goal.

        Args:
            description: Goal description.

        Returns:
            List of completion signal patterns.
        """
        signals = []

        # Common completion indicators based on goal type
        goal_type = self._detect_goal_type(description)

        if goal_type == GoalType.CODING:
            signals = [
                "code.*(?:written|created|implemented|added)",
                "feature.*(?:working|complete|done)",
                "function.*(?:implemented|working)",
                "tests?.*(?:passing|written)",
            ]
        elif goal_type == GoalType.DEBUGGING:
            signals = [
                "bug.*(?:fixed|resolved|found)",
                "error.*(?:resolved|gone|fixed)",
                "issue.*(?:fixed|resolved)",
                "working.*(?:again|properly)",
            ]
        elif goal_type == GoalType.TESTING:
            signals = [
                "test.*(?:passing|written|created)",
                "coverage.*(?:increased|improved)",
                "test.*(?:pass|passing)",
            ]
        elif goal_type == GoalType.REFACTORING:
            signals = [
                "code.*(?:cleaner|better|improved)",
                "refactor.*(?:complete|done)",
                "structure.*(?:improved|better)",
            ]

        return signals


class GoalTracker:
    """Tracker for managing goals during autonomous sessions."""

    def __init__(self):
        """Initialize the goal tracker."""
        self.goals: dict[str, Goal] = {}
        self.completed_goals: list[str] = []
        self.goal_stack: list[str] = []  # For hierarchical goals
        self.parser = GoalParser()

    def add_goal(self, description: str) -> Goal:
        """Add a new goal from description.

        Args:
            description: Natural language description.

        Returns:
            Created Goal.
        """
        goal = self.parser.parse_goal(description)

        # Handle hierarchical goals
        if self.goal_stack:
            goal.parent_id = self.goal_stack[-1]
            parent = self.goals.get(goal.parent_id)
            if parent:
                parent.subtasks.append(goal)

        self.goals[goal.id] = goal
        logger.info(f"Added goal: {goal.id} - {goal.description}")
        return goal

    def get_current_goal(self) -> Optional[Goal]:
        """Get the current active goal.

        Returns:
            Current goal or None.
        """
        for goal_id in reversed(self.goal_stack):
            goal = self.goals.get(goal_id)
            if goal and goal.status in (GoalStatus.PENDING, GoalStatus.IN_PROGRESS):
                return goal

        # Find first pending/in-progress goal
        for goal in self.goals.values():
            if goal.status in (GoalStatus.PENDING, GoalStatus.IN_PROGRESS):
                return goal

        return None

    def update_goal_status(
        self,
        goal_id: str,
        status: GoalStatus,
        notes: Optional[str] = None,
    ) -> bool:
        """Update the status of a goal.

        Args:
            goal_id: ID of the goal.
            status: New status.
            notes: Optional notes.

        Returns:
            True if successful.
        """
        goal = self.goals.get(goal_id)
        if not goal:
            return False

        goal.status = status
        if notes:
            goal.notes = notes

        if status == GoalStatus.COMPLETED:
            self.completed_goals.append(goal_id)

        logger.info(f"Goal {goal_id} status updated to {status.value}")
        return True

    def increment_iterations(self, goal_id: str) -> bool:
        """Increment the iteration count for a goal.

        Args:
            goal_id: ID of the goal.

        Returns:
            True if within max iterations.
        """
        goal = self.goals.get(goal_id)
        if not goal:
            return False

        goal.iterations += 1

        if goal.iterations >= goal.max_iterations:
            goal.status = GoalStatus.FAILED
            return False

        return True

    def check_completion(self, goal_id: str, response: str) -> bool:
        """Check if a goal is complete based on response.

        Args:
            goal_id: ID of the goal.
            response: Last agent response.

        Returns:
            True if goal appears complete.
        """
        goal = self.goals.get(goal_id)
        if not goal:
            return False

        # Check completion signals
        import re
        for signal in goal.completion_signals:
            if re.search(signal, response, re.IGNORECASE):
                return True

        # Check success criteria
        for criteria in goal.success_criteria:
            if criteria.lower() in response.lower():
                return True

        return False

    def get_progress(self, goal_id: str) -> GoalProgress:
        """Get progress information for a goal.

        Args:
            goal_id: ID of the goal.

        Returns:
            GoalProgress object.
        """
        goal = self.goals.get(goal_id)
        if not goal:
            return GoalProgress(goal_id=goal_id, status=GoalStatus.FAILED)

        # Calculate subtask progress
        total_subtasks = len(goal.subtasks)
        completed_subtasks = sum(1 for s in goal.subtasks if s.status == GoalStatus.COMPLETED)

        # Calculate percentage
        if total_subtasks > 0:
            percentage = (completed_subtasks / total_subtasks) * 100
        elif goal.iterations > 0:
            percentage = min(goal.iterations / goal.max_iterations * 100, 99)
        else:
            percentage = 0

        # Determine status
        status = goal.status
        if goal.status == GoalStatus.IN_PROGRESS and percentage >= 100:
            status = GoalStatus.COMPLETED

        return GoalProgress(
            goal_id=goal_id,
            status=status,
            completed_steps=completed_subtasks,
            total_steps=total_subtasks,
            percentage=percentage,
            blockers=goal.blocked_by,
            suggestions=self._generate_suggestions(goal),
        )

    def _generate_suggestions(self, goal: Goal) -> list[str]:
        """Generate suggestions for completing a goal.

        Args:
            goal: The goal.

        Returns:
            List of suggestions.
        """
        suggestions = []

        if goal.goal_type == GoalType.CODING:
            suggestions = [
                "Start by understanding the existing codebase structure",
                "write_to_file tests first to define the expected behavior",
                "Implement the core functionality first",
                "Run tests to verify your implementation",
            ]
        elif goal.goal_type == GoalType.DEBUGGING:
            suggestions = [
                "Gather more information about the error",
                "Check logs and stack traces",
                "Reproduce the issue in a minimal way",
                "Fix the root cause, not just symptoms",
            ]
        elif goal.goal_type == GoalType.REFACTORING:
            suggestions = [
                "Make sure you have good test coverage first",
                "Take one small step at a time",
                "Run tests after each change",
                "Commit frequently so you can rollback if needed",
            ]

        return suggestions

    def get_all_goals(self) -> list[Goal]:
        """Get all goals sorted by priority.

        Returns:
            List of all goals.
        """
        return sorted(
            self.goals.values(),
            key=lambda g: (g.priority, g.status.value),
        )

    def get_goals_by_status(self, status: GoalStatus) -> list[Goal]:
        """Get goals filtered by status.

        Args:
            status: Goal status to filter by.

        Returns:
            List of goals with the status.
        """
        return [g for g in self.goals.values() if g.status == status]

    def get_summary(self) -> dict:
        """Get a summary of all goals.

        Returns:
            Summary dictionary.
        """
        return {
            "total": len(self.goals),
            "completed": len(self.completed_goals),
            "pending": len(self.get_goals_by_status(GoalStatus.PENDING)),
            "in_progress": len(self.get_goals_by_status(GoalStatus.IN_PROGRESS)),
            "failed": len(self.get_goals_by_status(GoalStatus.FAILED)),
            "current_goal": self.get_current_goal().id if self.get_current_goal() else None,
        }
