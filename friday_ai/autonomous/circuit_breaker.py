"""Circuit breaker control for autonomous mode.

Provides circuit breaker state management and status display.
"""

import logging

from friday_ai.agent.autonomous_loop import CircuitBreakerState, CircuitBreaker

logger = logging.getLogger(__name__)


class CircuitBreakerControl:
    """Manages circuit breaker state and status display."""

    def __init__(self, circuit_breaker: CircuitBreaker):
        """Initialize circuit breaker control.

        Args:
            circuit_breaker: Circuit breaker instance
        """
        self.circuit_breaker = circuit_breaker

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state.

        Returns:
            Current circuit breaker state
        """
        return self.circuit_breaker.state

    def is_open(self) -> bool:
        """Check if circuit breaker is open.

        Returns:
            True if circuit breaker is OPEN or HALF_OPEN
        """
        return self.circuit_breaker.state in [
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN,
        ]

    def display_status(
        self,
        consecutive_errors: int,
        consecutive_no_progress: int,
        completion_indicators: int,
    ) -> None:
        """Display circuit breaker status with colored output.

        Args:
            consecutive_errors: Number of consecutive errors
            consecutive_no_progress: Number of loops with no progress
            completion_indicators: Number of completion indicators found
        """
        state = self.circuit_breaker.state
        state_colors = {
            CircuitBreakerState.CLOSED: "green",
            CircuitBreakerState.HALF_OPEN: "yellow",
            CircuitBreakerState.OPEN: "red",
        }
        state_color = state_colors.get(state, "white")

        console.print(f"\n[bold]Circuit Breaker:[/bold]")
        console.print(f"  State: [{state_color}]{state.value}[/{state_color}]")
        console.print(f"  Consecutive errors: {consecutive_errors}/{self.circuit_breaker.config.max_consecutive_errors}")
        console.print(f"  No progress loops: {consecutive_no_progress}/{self.circuit_breaker.config.max_no_progress_loops}")
        console.print(f"  Completion indicators: {completion_indicators}/{self.circuit_breaker.config.max_completion_indicators}")
