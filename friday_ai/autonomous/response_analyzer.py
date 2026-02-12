"""Response analysis for autonomous mode.

Analyzes LLM responses to detect completion, exit signals, and errors.
"""

import logging
from friday_ai.agent.autonomous_loop import CircuitBreakerState

logger = logging.getLogger(__name__)


class ResponseAnalyzer:
    """Analyzes responses to detect completion and exit signals."""

    def __init__(self, config):
        """Initialize response analyzer.

        Args:
            config: Configuration
        """
        self.config = config

    def has_permission_denials(self, error_message: str) -> bool:
        """Check if response contains permission denial messages.

        Args:
            error_message: Error message from API

        Returns:
            True if permission denial detected
        """
        permission_keywords = [
            "permission denied", "forbidden", "not authorized",
            "authentication required", "access denied", "quota exceeded",
            "rate limit", "invalid api key", "authorization error",
        ]
        error_lower = error_message.lower()
        return any(keyword in error_lower for keyword in permission_keywords)

    def has_exit_signal(self, response: str) -> bool:
        """Check if response contains exit signal.

        Args:
            response: Response text from LLM

        Returns:
            True if exit signal detected
        """
        exit_indicators = [
            "task completed", "goal completed", "objective achieved",
            "operation successful", "operation complete", "all goals met",
            "session complete", "loop finished", "autonomous loop complete",
            "EXIT", "EXIT_SIGNAL", "exit signal", "stop loop",
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in exit_indicators)

    def check_completion_indicators(
        self,
        messages: list[dict],
        required: int,
    ) -> int:
        """Check for completion indicators in message history.

        Args:
            messages: List of message dictionaries
            required: Number of completion indicators required

        Returns:
            Number of completion indicators found
        """
        completion_count = 0
        completion_indicators = [
            "task completed", "goal completed", "objective achieved",
            "operation successful", "operation complete", "all goals met",
            "session complete", "loop finished", "autonomous loop complete",
        ]

        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if not content:
                continue
            for indicator in completion_indicators:
                if indicator in content.lower():
                    completion_count += 1
        return completion_count

    def analyze(
        self,
        response: str,
        circuit_breaker_state: CircuitBreakerState,
    ) -> dict[str, Any]:
        """Analyze response and determine if loop should continue.

        Args:
            response: Response text from LLM
            circuit_breaker_state: Current circuit breaker state

        Returns:
            Analysis dictionary with:
                - has_permission_denials
                - has_exit_signal
                - completion_indicators
                - should_exit
        """
        # Check for permission denials
        has_permission_denials = self.has_permission_denials(response)

        # Check for exit signal
        has_exit_signal = self.has_exit_signal(response)

        # Check completion indicators
        completion_indicators = self.check_completion_indicators(
            [],  # will be populated by call site
            self.config.max_completion_indicators,
        )

        # Determine if loop should continue
        should_exit = False
        if has_permission_denials:
            should_exit = True
            self.exit_reason = "permission_denial"
        elif has_exit_signal:
            should_exit = True
            self.exit_reason = "exit_signal"
        elif completion_indicators >= self.config.min_completion_indicators:
            should_exit = True
            self.exit_reason = "complete"
        elif circuit_breaker_state == CircuitBreakerState.OPEN:
            should_exit = True
            self.exit_reason = "circuit_breaker_open"

        return {
            "has_permission_denials": has_permission_denials,
            "has_exit_signal": has_exit_signal,
            "completion_indicators": completion_indicators,
            "should_exit": should_exit,
            "exit_reason": getattr(self, "exit_reason", "unknown"),
        }
