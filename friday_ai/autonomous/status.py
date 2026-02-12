"""Status display for autonomous mode.

Provides formatted status output for autonomous operations.
"""

import logging

from friday_ai.agent.autonomous_loop import CircuitBreakerState

logger = logging.getLogger(__name__)


class StatusDisplay:
    """Manages status display for autonomous mode."""

    def __init__(self):
        """Initialize status display."""
        pass

    def show_loop_start(self, max_loops: int) -> None:
        """Show loop start message.

        Args:
            max_loops: Maximum number of iterations
        """
        console.print(f"\n[bold]Starting autonomous loop (max {max_loops} iterations)[/bold]")
        console.print(f"  Goal: Improve this project incrementally\n")

    def show_loop_progress(
        self,
        current_loop: int,
        total_errors: int,
        consecutive_errors: int,
        no_progress_loops: int,
        completion_indicators: int,
    ) -> None:
        """Show loop progress.

        Args:
            current_loop: Current iteration number
            total_errors: Total error count
            consecutive_errors: Consecutive errors
            no_progress_loops: Loops with no progress
            completion_indicators: Completion indicators seen
        """
        console.print(f"\n[bold]Loop {current_loop}/{max_loops}[/bold]")
        console.print(f"  Errors: {total_errors} | Consecutive: {consecutive_errors}")
        console.print(f"  No progress: {no_progress_loops} | Completions: {completion_indicators}")

    def show_circuit_breaker_status(self, state: CircuitBreakerState) -> None:
        """Show circuit breaker status with color coding.

        Args:
            state: Current circuit breaker state
        """
        state_colors = {
            CircuitBreakerState.CLOSED: "green",
            CircuitBreakerState.HALF_OPEN: "yellow",
            CircuitBreakerState.OPEN: "red",
        }
        state_color = state_colors.get(state, "white")

        console.print(f"  Circuit Breaker: [{state_color}]{state.value.upper()}[/{state_color}]")

    def show_completion(self, success: bool, message: str) -> None:
        """Show completion or failure message.

        Args:
            success: Whether operation succeeded
            message: Completion message
        """
        if success:
            console.print(f"[success]✓ {message}[/success]")
        else:
            console.print(f"[error]✗ {message}[/error]")
