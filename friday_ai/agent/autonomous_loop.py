"""Autonomous development loop for Friday AI.

Implements an autonomous development cycle similar to Ralph, where
Friday can iteratively improve a project until completion with
built-in safeguards to prevent infinite loops.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from friday_ai.agent.agent import Agent

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    HALF_OPEN = "half_open"  # Monitoring after recovery
    OPEN = "open"  # Halted due to failure


@dataclass
class LoopConfig:
    """Configuration for autonomous loop."""

    # Rate limiting
    max_calls_per_hour: int = 100
    call_count_file: str = ".friday/.call_count"

    # Circuit breaker thresholds
    max_no_progress_loops: int = 3
    max_consecutive_errors: int = 5
    max_completion_indicators: int = 5

    # Exit detection
    require_exit_signal: bool = True  # Require explicit EXIT_SIGNAL
    min_completion_indicators: int = 2

    # Session
    enable_session_continuity: bool = True
    session_timeout_hours: int = 24
    session_file: str = ".friday/.session_id"

    # Monitoring
    enable_tmux: bool = False
    log_dir: str = ".friday/logs"

    # Project files
    prompt_file: str = ".friday/PROMPT.md"
    fix_plan_file: str = ".friday/fix_plan.md"
    agent_file: str = ".friday/AGENT.md"
    status_file: str = ".friday/status.json"


@dataclass
class ResponseAnalysis:
    """Analysis of Claude's response."""

    has_exit_signal: bool = False
    completion_indicators: int = 0
    has_errors: bool = False
    error_count: int = 0
    has_permission_denials: bool = False
    files_modified: list[str] = field(default_factory=list)
    confidence: int = 0
    exit_reason: str | None = None
    status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_exit_signal": self.has_exit_signal,
            "completion_indicators": self.completion_indicators,
            "has_errors": self.has_errors,
            "error_count": self.error_count,
            "has_permission_denials": self.has_permission_denials,
            "files_modified": self.files_modified,
            "confidence": self.confidence,
            "exit_reason": self.exit_reason,
            "status": self.status,
        }


class ResponseAnalyzer:
    """Analyzes AI responses for exit signals and completion indicators."""

    # Exit signal patterns
    EXIT_PATTERNS = [
        r"\[EXIT\]",
        r"EXIT_SIGNAL:\s*true",
        r"(?:project|task|implementation)(?:\s+is)?\s+complete",
        r"all\s+(?:tasks|features|requirements)\s+complete",
        r"no\s+(?:further|more)\s+(?:work|changes|modifications)\s+(?:needed|required)",
    ]

    # Completion indicator patterns
    COMPLETION_PATTERNS = [
        r"\[DONE\]",
        r"\[COMPLETE\]",
        r"(?:feature|task|phase)\s+complete",
        r"successfully\s+(?:implemented|completed|finished)",
        r"all\s+tests?\s+passing?",
    ]

    # Error patterns
    ERROR_PATTERNS = [
        r"\[ERROR\]",
        r"(?:error|exception|failed|failure):",
        r"traceback",
        r"warning",
    ]

    def __init__(self, config: LoopConfig):
        self.config = config

    def analyze(self, response: str) -> ResponseAnalysis:
        """Analyze a response for exit signals and completion status.

        Args:
            response: The AI's response text.

        Returns:
            ResponseAnalysis with findings.
        """
        analysis = ResponseAnalysis()

        # Check for exit signal
        for pattern in self.EXIT_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                analysis.has_exit_signal = True
                break

        # Count completion indicators
        for pattern in self.COMPLETION_PATTERNS:
            matches = len(re.findall(pattern, response, re.IGNORECASE))
            analysis.completion_indicators += matches

        # Check for errors
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                analysis.has_errors = True
                analysis.error_count += len(re.findall(pattern, response, re.IGNORECASE))

        # Calculate confidence
        if analysis.has_exit_signal:
            analysis.confidence += 50
        analysis.confidence += min(analysis.completion_indicators * 20, 30)

        # Determine status
        if analysis.has_exit_signal and analysis.completion_indicators >= self.config.min_completion_indicators:
            analysis.status = "complete"
        elif analysis.has_errors:
            analysis.status = "error"
        elif analysis.completion_indicators > 0:
            analysis.status = "in_progress"
        else:
            analysis.status = "working"

        return analysis


class CircuitBreaker:
    """Prevents runaway loops by detecting stagnation."""

    def __init__(self, config: LoopConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.no_progress_count = 0
        self.consecutive_error_count = 0
        self.completion_count = 0
        self.last_files_modified: set[str] = set()

    def update(
        self,
        has_files_changed: bool,
        has_errors: bool,
        has_completion: bool,
    ) -> CircuitBreakerState:
        """Update circuit breaker state based on loop progress.

        Args:
            has_files_changed: Whether files were modified in this loop.
            has_errors: Whether errors occurred.
            has_completion: Whether completion indicators were seen.

        Returns:
            Current circuit breaker state.
        """
        if self.state == CircuitBreakerState.OPEN:
            # Stay open, won't update until manually reset
            return self.state

        # Check for no progress
        if not has_files_changed and not has_errors:
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0

        # Check for errors
        if has_errors:
            self.consecutive_error_count += 1
        else:
            self.consecutive_error_count = 0

        # Check for completion
        if has_completion:
            self.completion_count += 1

        # Determine if we should open the circuit
        if self.no_progress_count >= self.config.max_no_progress_loops:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker OPEN: {self.no_progress_count} loops with no progress")

        elif self.consecutive_error_count >= self.config.max_consecutive_errors:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker OPEN: {self.consecutive_error_count} consecutive errors")

        elif self.completion_count >= self.config.max_completion_indicators:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker OPEN: {self.completion_count} completion indicators")

        return self.state

    def reset(self) -> None:
        """Reset the circuit breaker to CLOSED state."""
        self.state = CircuitBreakerState.CLOSED
        self.no_progress_count = 0
        self.consecutive_error_count = 0
        self.completion_count = 0


class RateLimiter:
    """Manages API call rate limiting."""

    def __init__(self, config: LoopConfig):
        self.config = config
        self.call_count_file = Path(config.call_count_file)
        self.calls_made = self._load_call_count()
        self.last_reset = self._get_last_reset()

    def _load_call_count(self) -> int:
        """Load call count from file."""
        try:
            if self.call_count_file.exists():
                data = json.loads(self.call_count_file.read_text())
                return data.get("count", 0)
        except Exception:
            pass
        return 0

    def _get_last_reset(self) -> datetime:
        """Get last reset time."""
        try:
            if self.call_count_file.exists():
                data = json.loads(self.call_count_file.read_text())
                last_reset = data.get("last_reset")
                if last_reset:
                    return datetime.fromisoformat(last_reset)
        except Exception:
            pass
        return datetime.now()

    def _save_call_count(self) -> None:
        """Save call count to file."""
        self.call_count_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "count": self.calls_made,
            "last_reset": self.last_reset.isoformat(),
        }
        self.call_count_file.write_text(json.dumps(data, indent=2))

    def check_limit(self) -> bool:
        """Check if rate limit has been exceeded.

        Returns:
            True if under limit, False if exceeded.
        """
        now = datetime.now()

        # Reset if hour has passed
        if now - self.last_reset >= timedelta(hours=1):
            self.calls_made = 0
            self.last_reset = now
            self._save_call_count()
            return True

        return self.calls_made < self.config.max_calls_per_hour

    def increment(self) -> None:
        """Increment call count."""
        self.calls_made += 1
        self._save_call_count()

    def calls_remaining(self) -> int:
        """Get number of calls remaining this hour."""
        now = datetime.now()

        # Reset if hour has passed
        if now - self.last_reset >= timedelta(hours=1):
            return self.config.max_calls_per_hour

        return max(0, self.config.max_calls_per_hour - self.calls_made)


class AutonomousLoop:
    """Main autonomous development loop."""

    def __init__(self, agent: Agent, config: LoopConfig | None = None):
        """Initialize the autonomous loop.

        Args:
            agent: The Friday agent to use.
            config: Optional loop configuration.
        """
        self.agent = agent
        self.config = config or LoopConfig()

        self.response_analyzer = ResponseAnalyzer(self.config)
        self.circuit_breaker = CircuitBreaker(self.config)
        self.rate_limiter = RateLimiter(self.config)

        self.loop_number = 0
        self.is_running = False
        self.exit_reason = ""

        # Ensure directories exist
        Path(self.config.log_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.call_count_file).parent.mkdir(parents=True, exist_ok=True)

    async def run(self, max_loops: int = 100) -> dict[str, Any]:
        """Run the autonomous development loop.

        Args:
            max_loops: Maximum number of loops to run.

        Returns:
            Dictionary with loop results.
        """
        self.is_running = True
        results = {
            "loops_run": 0,
            "exit_reason": "",
            "files_modified": [],
            "errors_encountered": [],
        }

        logger.info("Starting autonomous development loop")

        try:
            while self.loop_number < max_loops and self.is_running:
                # Check rate limit
                if not self.rate_limiter.check_limit():
                    logger.warning("Rate limit exceeded, stopping loop")
                    results["exit_reason"] = "rate_limit_exceeded"
                    break

                # Check circuit breaker
                if self.circuit_breaker.state == CircuitBreakerState.OPEN:
                    logger.warning("Circuit breaker is open, stopping loop")
                    results["exit_reason"] = "circuit_breaker_open"
                    break

                # Run a single loop iteration
                result = await self._run_iteration()

                # Update results
                results["loops_run"] += 1
                results["files_modified"].extend(result.get("files_modified", []))
                if result.get("error"):
                    results["errors_encountered"].append(result["error"])

                # Analyze response
                analysis = self.response_analyzer.analyze(result.get("response", ""))

                # Update circuit breaker
                self.circuit_breaker.update(
                    has_files_changed=len(result.get("files_modified", [])) > 0,
                    has_errors=analysis.has_errors,
                    has_completion=analysis.completion_indicators > 0,
                )

                # Check for exit conditions
                if self._should_exit(analysis):
                    results["exit_reason"] = self.exit_reason
                    break

                self.loop_number += 1
                self.rate_limiter.increment()

        except Exception as e:
            logger.error(f"Loop error: {e}")
            results["exit_reason"] = f"error: {e}"

        finally:
            self.is_running = False

        logger.info(f"Loop completed: {results['loops_run']} iterations, reason: {results['exit_reason']}")
        return results

    async def _run_iteration(self) -> dict[str, Any]:
        """Run a single loop iteration.

        Returns:
            Dictionary with iteration results.
        """
        loop_dir = Path(self.config.log_dir)
        loop_dir.mkdir(parents=True, exist_ok=True)

        # Log file for this iteration
        log_file = loop_dir / f"loop_{self.loop_number + 1:04d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # Load prompt and context
        prompt = self._build_loop_prompt()

        # Execute agent
        try:
            response = await self.agent.run(prompt)

            # Log response
            log_file.write_text(response)

            # Check for file modifications (would need to be tracked by agent)
            files_modified = []  # TODO: Implement file tracking

            return {
                "response": response,
                "files_modified": files_modified,
                "success": True,
            }

        except Exception as e:
            error_msg = str(e)
            log_file.write_text(f"ERROR: {error_msg}")
            return {
                "response": "",
                "files_modified": [],
                "error": error_msg,
                "success": False,
            }

    def _build_loop_prompt(self) -> str:
        """Build the prompt for this loop iteration.

        Returns:
            The prompt to send to the agent.
        """
        # Load main prompt
        prompt_file = Path(self.config.prompt_file)
        if prompt_file.exists():
            prompt = prompt_file.read_text()
        else:
            prompt = "Continue improving the project."

        # Add loop context
        context = f"""

---
Loop Context (Iteration {self.loop_number + 1})
---

Rate Limit: {self.rate_limiter.calls_remaining()} calls remaining this hour.
Circuit Breaker: {self.circuit_breaker.state.value}
No Progress Count: {self.circuit_breaker.no_progress_count}/{self.config.max_no_progress_loops}
Consecutive Errors: {self.circuit_breaker.consecutive_error_count}/{self.config.max_consecutive_errors}

---
Instructions
-

"""

        return prompt + context

    def _should_exit(self, analysis: ResponseAnalysis) -> bool:
        """Determine if the loop should exit.

        Args:
            analysis: The response analysis.

        Returns:
            True if loop should exit.
        """
        # Exit signal + completion indicators (dual-condition gate)
        if self.config.require_exit_signal:
            if analysis.has_exit_signal and analysis.completion_indicators >= self.config.min_completion_indicators:
                self.exit_reason = "complete_with_signal"
                return True

        # Completion without signal (if not required)
        if not self.config.require_exit_signal and analysis.completion_indicators >= self.config.min_completion_indicators:
            self.exit_reason = "complete_without_signal"
            return True

        return False

    def stop(self) -> None:
        """Stop the autonomous loop."""
        self.is_running = False
        logger.info("Loop stopped by user")
