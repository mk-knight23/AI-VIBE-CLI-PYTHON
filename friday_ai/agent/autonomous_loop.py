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
    """Analyzes AI responses for exit signals and completion indicators.

    Implements Ralph-style response analysis with:
    - JSON response parsing
    - Two-stage error filtering (eliminates false positives)
    - Permission denial detection
    - Session ID extraction
    """

    # Exit signal patterns
    EXIT_PATTERNS = [
        r"\[EXIT\]",
        r"EXIT_SIGNAL:\s*true",
        r"(?:^|[.!?]\s+)(?:project|task|implementation)(?:\s+is)?\s+complete(?:\s|$|[.!?])",
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

    # Permission denial patterns (Issue #101 from Ralph)
    PERMISSION_DENIAL_PATTERNS = [
        r"permission\s+denied",
        r"access\s+denied",
        r"not\s+authorized",
        r"forbidden",
        r"403",
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

        # Try to parse as JSON first (Ralph-style)
        json_data = self._try_parse_json(response)
        if json_data:
            self._analyze_json_response(json_data, analysis)
        else:
            self._analyze_text_response(response, analysis)

        # Calculate confidence
        if analysis.has_exit_signal:
            analysis.confidence += 50
        analysis.confidence += min(analysis.completion_indicators * 20, 30)
        if json_data:
            analysis.confidence += 20  # JSON format increases confidence

        # Determine status
        if analysis.has_permission_denials:
            analysis.status = "permission_denied"
        elif analysis.has_exit_signal and analysis.completion_indicators >= self.config.min_completion_indicators:
            analysis.status = "complete"
        elif analysis.has_errors:
            analysis.status = "error"
        elif analysis.completion_indicators > 0:
            analysis.status = "in_progress"
        else:
            analysis.status = "working"

        return analysis

    def _try_parse_json(self, response: str) -> dict[str, Any] | None:
        """Try to parse response as JSON.

        Args:
            response: Response text to parse.

        Returns:
            Parsed JSON data or None if not valid JSON.
        """
        # Look for JSON block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to parse entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Look for RALPH_STATUS block
        status_match = re.search(r'RALPH_STATUS\s*```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if status_match:
            try:
                return json.loads(status_match.group(1))
            except json.JSONDecodeError:
                pass

        return None

    def _analyze_json_response(self, data: dict[str, Any], analysis: ResponseAnalysis) -> None:
        """Analyze JSON response data.

        Args:
            data: Parsed JSON data.
            analysis: ResponseAnalysis to update.
        """
        # Check for exit signal
        exit_signal = data.get('exit_signal') or data.get('EXIT_SIGNAL')
        if exit_signal is True or exit_signal == 'true' or exit_signal == 'True':
            analysis.has_exit_signal = True

        # Check completion status
        status = data.get('status', '').lower()
        if status in ['complete', 'completed', 'done', 'success']:
            analysis.completion_indicators += 1

        # Get completion indicators from metadata
        completion_status = data.get('metadata', {}).get('completion_status', '')
        if completion_status:
            analysis.completion_indicators += 1

        # Check for progress indicators
        progress_indicators = data.get('metadata', {}).get('progress_indicators', [])
        analysis.completion_indicators += len(progress_indicators)

        # Check for errors
        has_errors = data.get('has_errors') or data.get('metadata', {}).get('has_errors')
        if has_errors:
            analysis.has_errors = True

        error_count = data.get('error_count') or data.get('metadata', {}).get('error_count', 0)
        analysis.error_count = error_count

        # Check for permission denials (Issue #101)
        permission_denials = data.get('permission_denials') or data.get('metadata', {}).get('permission_denials', [])
        if permission_denials:
            analysis.has_permission_denials = True

        # Get files modified
        files_modified = data.get('files_modified') or data.get('metadata', {}).get('files_modified', [])
        analysis.files_modified = files_modified

        # Get exit reason
        analysis.exit_reason = data.get('exit_reason')

    def _analyze_text_response(self, response: str, analysis: ResponseAnalysis) -> None:
        """Analyze text response.

        Args:
            response: Response text.
            analysis: ResponseAnalysis to update.
        """
        # Check for exit signal
        for pattern in self.EXIT_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                analysis.has_exit_signal = True
                break

        # Count completion indicators
        for pattern in self.COMPLETION_PATTERNS:
            matches = len(re.findall(pattern, response, re.IGNORECASE))
            analysis.completion_indicators += matches

        # Check for errors with two-stage filtering
        analysis.has_errors, analysis.error_count = self._detect_errors(response)

        # Check for permission denials
        for pattern in self.PERMISSION_DENIAL_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                analysis.has_permission_denials = True
                break

    def _detect_errors(self, response: str) -> tuple[bool, int]:
        """Detect errors with two-stage filtering to eliminate false positives.

        Stage 1: Filter out JSON field patterns like "is_error": false
        Stage 2: Detect actual error messages

        Args:
            response: Response text to analyze.

        Returns:
            Tuple of (has_errors, error_count).
        """
        # Stage 1: Filter out JSON field patterns
        # Remove lines that look like JSON fields with "error" in the key
        filtered_lines = []
        for line in response.split('\n'):
            # Skip JSON field definitions like "is_error": false
            if re.search(r'"[^"]*error[^"]*":\s*false', line, re.IGNORECASE):
                continue
            filtered_lines.append(line)

        filtered_response = '\n'.join(filtered_lines)

        # Stage 2: Detect actual errors
        error_patterns = [
            r'^\s*Error:',
            r'^\s*ERROR:',
            r'^\s*error:',
            r'\[ERROR\]',
            r'\]: error',
            r'Link: error',
            r'Error occurred',
            r'failed with error',
            r'[Ee]xception',
            r'Fatal',
            r'FATAL',
            r'Traceback',
        ]

        error_count = 0
        for pattern in error_patterns:
            matches = len(re.findall(pattern, filtered_response, re.MULTILINE | re.IGNORECASE))
            error_count += matches

        return error_count > 0, error_count

    def extract_session_id(self, response: str) -> str | None:
        """Extract session ID from response.

        Args:
            response: Response text.

        Returns:
            Session ID if found, None otherwise.
        """
        # Try JSON first
        data = self._try_parse_json(response)
        if data:
            session_id = data.get('sessionId') or data.get('session_id')
            if session_id:
                return str(session_id)

        # Try text patterns
        session_patterns = [
            r'session[_-]id[:\s]+([\w-]+)',
            r'SessionId[:\s]+([\w-]+)',
            r'session[:\s]+([\w-]+)',
        ]

        for pattern in session_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1)

        return None


class CircuitBreaker:
    """Prevents runaway loops by detecting stagnation.

    Implements Ralph-style circuit breaker with:
    - Three states: CLOSED, HALF_OPEN, OPEN
    - Permission denial detection (Issue #101)
    - Output decline detection
    - State history tracking
    """

    def __init__(self, config: LoopConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.no_progress_count = 0
        self.consecutive_error_count = 0
        self.completion_count = 0
        self.permission_denial_count = 0
        self.last_output_length = 0
        self.output_decline_count = 0
        self.last_files_modified: set[str] = set()
        self.state_history: list[dict[str, Any]] = []

    def update(
        self,
        has_files_changed: bool,
        has_errors: bool,
        has_completion: bool,
        has_permission_denials: bool = False,
        output_length: int = 0,
    ) -> CircuitBreakerState:
        """Update circuit breaker state based on loop progress.

        Args:
            has_files_changed: Whether files were modified in this loop.
            has_errors: Whether errors occurred.
            has_completion: Whether completion indicators were seen.
            has_permission_denials: Whether permission was denied.
            output_length: Length of the output for decline detection.

        Returns:
            Current circuit breaker state.
        """
        # Log state transition if changed
        old_state = self.state

        if self.state == CircuitBreakerState.OPEN:
            # Stay open, won't update until manually reset
            return self.state

        if self.state == CircuitBreakerState.HALF_OPEN:
            # In half-open state, we're monitoring for recovery
            if has_errors or has_permission_denials:
                # Failed recovery test, go back to open
                self.state = CircuitBreakerState.OPEN
                self._log_state_change(old_state, "recovery_failed")
            elif has_files_changed or has_completion:
                # Recovery successful, close the circuit
                self.state = CircuitBreakerState.CLOSED
                self._reset_counters()
                self._log_state_change(old_state, "recovery_success")
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

        # Check for permission denials (Issue #101 from Ralph)
        if has_permission_denials:
            self.permission_denial_count += 1
            logger.warning(f"Permission denial detected: {self.permission_denial_count}")
        else:
            self.permission_denial_count = 0

        # Check for output decline (Ralph pattern)
        if output_length > 0 and self.last_output_length > 0:
            if output_length < self.last_output_length * 0.3:  # 70% decline
                self.output_decline_count += 1
            else:
                self.output_decline_count = 0
        self.last_output_length = output_length

        # Determine if we should open the circuit
        if self.no_progress_count >= self.config.max_no_progress_loops:
            self.state = CircuitBreakerState.OPEN
            self._log_state_change(old_state, f"no_progress_{self.no_progress_count}")
            logger.warning(f"Circuit breaker OPEN: {self.no_progress_count} loops with no progress")

        elif self.consecutive_error_count >= self.config.max_consecutive_errors:
            self.state = CircuitBreakerState.OPEN
            self._log_state_change(old_state, f"errors_{self.consecutive_error_count}")
            logger.warning(f"Circuit breaker OPEN: {self.consecutive_error_count} consecutive errors")

        elif self.completion_count >= self.config.max_completion_indicators:
            self.state = CircuitBreakerState.OPEN
            self._log_state_change(old_state, f"completion_{self.completion_count}")
            logger.warning(f"Circuit breaker OPEN: {self.completion_count} completion indicators")

        elif self.permission_denial_count >= 2:  # Issue #101: halt on permission denials
            self.state = CircuitBreakerState.OPEN
            self._log_state_change(old_state, f"permission_denied_{self.permission_denial_count}")
            logger.warning(f"Circuit breaker OPEN: {self.permission_denial_count} permission denials")

        return self.state

    def reset(self) -> None:
        """Reset the circuit breaker to CLOSED state."""
        old_state = self.state
        self.state = CircuitBreakerState.CLOSED
        self._reset_counters()
        self._log_state_change(old_state, "manual_reset")

    def _reset_counters(self) -> None:
        """Reset all counters."""
        self.no_progress_count = 0
        self.consecutive_error_count = 0
        self.completion_count = 0
        self.permission_denial_count = 0
        self.output_decline_count = 0

    def _log_state_change(self, from_state: CircuitBreakerState, reason: str) -> None:
        """Log a state change to history.

        Args:
            from_state: Previous state.
            reason: Reason for the change.
        """
        self.state_history.append({
            "timestamp": datetime.now().isoformat(),
            "from_state": from_state.value,
            "to_state": self.state.value,
            "reason": reason,
        })
        # Keep only last 50 entries
        if len(self.state_history) > 50:
            self.state_history = self.state_history[-50:]

    def get_history(self) -> list[dict[str, Any]]:
        """Get circuit breaker state history.

        Returns:
            List of state change records.
        """
        return self.state_history.copy()


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
    """Main autonomous development loop.

    Implements Ralph-style autonomous development with:
    - Session continuity across iterations
    - Real-time status file updates
    - Permission denial handling
    - Proper log generation per iteration
    """

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
        self.session_id: str | None = None
        self._iteration_logs: list[Path] = []

        # Ensure directories exist
        Path(self.config.log_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.call_count_file).parent.mkdir(parents=True, exist_ok=True)

        # Load session if session continuity is enabled
        if self.config.enable_session_continuity:
            self._load_session()

    def _load_session(self) -> None:
        """Load existing session if available and not expired."""
        session_file = Path(self.config.session_file)
        if not session_file.exists():
            return

        try:
            data = json.loads(session_file.read_text())
            last_activity = datetime.fromisoformat(data.get("last_activity", "2000-01-01"))
            age = datetime.now() - last_activity

            if age < timedelta(hours=self.config.session_timeout_hours):
                self.session_id = data.get("session_id")
                self.loop_number = data.get("loop_number", 0)
                logger.info(f"Resumed session: {self.session_id}")
            else:
                logger.info("Session expired, starting fresh")
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")

    def _save_session(self) -> None:
        """Save current session state."""
        if not self.config.enable_session_continuity:
            return

        session_file = Path(self.config.session_file)
        session_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "session_id": self.session_id,
            "loop_number": self.loop_number,
            "last_activity": datetime.now().isoformat(),
        }

        try:
            session_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")

    def _update_status_file(self, state: str, extra: dict[str, Any] | None = None) -> None:
        """Update the status.json file.

        Args:
            state: Current state (running, paused, stopped, error).
            extra: Extra data to include in status.
        """
        status_file = Path(self.config.status_file)
        status_file.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            "state": state,
            "loop_number": self.loop_number,
            "timestamp": datetime.now().isoformat(),
            "circuit_breaker": {
                "state": self.circuit_breaker.state.value,
                "no_progress_count": self.circuit_breaker.no_progress_count,
                "consecutive_errors": self.circuit_breaker.consecutive_error_count,
            },
            "rate_limit": {
                "calls_remaining": self.rate_limiter.calls_remaining(),
                "max_calls": self.config.max_calls_per_hour,
            },
        }

        if extra:
            data.update(extra)

        try:
            status_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to update status file: {e}")

    async def run(self, max_loops: int = 100) -> dict[str, Any]:
        """Run the autonomous development loop.

        Args:
            max_loops: Maximum number of loops to run.

        Returns:
            Dictionary with loop results.
        """
        self.is_running = True

        # Generate secure session ID with sufficient entropy
        if not self.session_id:
            import uuid
            # Use full UUID for security (128-bit entropy)
            self.session_id = str(uuid.uuid4())

        results = {
            "loops_run": 0,
            "exit_reason": "",
            "files_modified": [],
            "errors_encountered": [],
            "session_id": self.session_id,
        }

        logger.info(f"Starting autonomous development loop (session: {self.session_id})")
        self._update_status_file("running", {"max_loops": max_loops, "session_id": self.session_id})

        try:
            while self.loop_number < max_loops and self.is_running:
                # Check rate limit
                if not self.rate_limiter.check_limit():
                    logger.warning("Rate limit exceeded, stopping loop")
                    results["exit_reason"] = "rate_limit_exceeded"
                    self._update_status_file("rate_limited")
                    break

                # Check circuit breaker
                if self.circuit_breaker.state == CircuitBreakerState.OPEN:
                    logger.warning("Circuit breaker is open, stopping loop")
                    results["exit_reason"] = "circuit_breaker_open"
                    self._update_status_file("circuit_breaker_open")
                    break

                # Run a single loop iteration
                result = await self._run_iteration()

                # Update results
                results["loops_run"] += 1
                results["files_modified"].extend(result.get("files_modified", []))
                if result.get("error"):
                    results["errors_encountered"].append(result["error"])

                # Analyze response
                response_text = result.get("response", "")
                analysis = self.response_analyzer.analyze(response_text)

                # Extract and update session ID if present
                extracted_session = self.response_analyzer.extract_session_id(response_text)
                if extracted_session:
                    self.session_id = extracted_session
                    results["session_id"] = self.session_id

                # Update circuit breaker with enhanced tracking
                self.circuit_breaker.update(
                    has_files_changed=len(result.get("files_modified", [])) > 0,
                    has_errors=analysis.has_errors,
                    has_completion=analysis.completion_indicators > 0,
                    has_permission_denials=analysis.has_permission_denials,
                    output_length=len(response_text),
                )

                # Check for permission denial exit (Issue #101)
                if analysis.has_permission_denials and self.circuit_breaker.permission_denial_count >= 2:
                    results["exit_reason"] = "permission_denied"
                    self.exit_reason = "permission_denied"
                    self._update_status_file("permission_denied", {"analysis": analysis.to_dict()})
                    break

                # Update status file
                self._update_status_file("running", {
                    "last_analysis": analysis.to_dict(),
                    "files_modified_count": len(result.get("files_modified", [])),
                })

                # Check for exit conditions
                if self._should_exit(analysis):
                    results["exit_reason"] = self.exit_reason
                    self._update_status_file("complete", {"exit_reason": self.exit_reason})
                    break

                self.loop_number += 1
                self.rate_limiter.increment()
                self._save_session()

        except Exception as e:
            logger.error(f"Loop error: {e}")
            results["exit_reason"] = f"error: {e}"
            self._update_status_file("error", {"error": str(e)})

        finally:
            self.is_running = False
            self._save_session()

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
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = loop_dir / f"loop_{self.loop_number + 1:04d}_{timestamp}.log"
        self._iteration_logs.append(log_file)

        # Load prompt and context
        prompt = self._build_loop_prompt()

        # Execute agent - the agent.run returns an async generator of events
        # We need to collect the full response
        response_parts = []
        files_modified = []

        try:
            # For event-based agent, collect all text deltas
            async for event in self.agent.run(prompt):
                from friday_ai.agent.events import AgentEventType
                if event.type == AgentEventType.TEXT_DELTA:
                    response_parts.append(event.data.get("content", ""))
                elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                    # Track file modifications from tool calls
                    tool_name = event.data.get("name", "")
                    if tool_name in ["write_file", "edit_file"]:
                        metadata = event.data.get("metadata", {})
                        file_path = metadata.get("file_path") or metadata.get("path")
                        if file_path:
                            files_modified.append(file_path)

            response = "".join(response_parts)

            # Log response with metadata
            log_data = {
                "timestamp": timestamp,
                "loop_number": self.loop_number + 1,
                "session_id": self.session_id,
                "response": response,
                "files_modified": files_modified,
            }
            log_file.write_text(json.dumps(log_data, indent=2))

            return {
                "response": response,
                "files_modified": files_modified,
                "success": True,
            }

        except Exception as e:
            error_msg = str(e)
            log_data = {
                "timestamp": timestamp,
                "loop_number": self.loop_number + 1,
                "session_id": self.session_id,
                "error": error_msg,
            }
            log_file.write_text(json.dumps(log_data, indent=2))
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

        # Load fix plan if exists
        fix_plan = ""
        fix_plan_file = Path(self.config.fix_plan_file)
        if fix_plan_file.exists():
            fix_plan_content = fix_plan_file.read_text()
            # Extract unchecked tasks
            unchecked_tasks = []
            for line in fix_plan_content.split('\n'):
                if line.strip().startswith('- [ ]') or line.strip().startswith('* [ ]'):
                    unchecked_tasks.append(line.strip())
            if unchecked_tasks:
                fix_plan = "\n\nRemaining Tasks:\n" + '\n'.join(unchecked_tasks[:10])  # Show first 10

        # Add loop context (Ralph-style)
        context = f"""

---
Loop Context (Iteration {self.loop_number + 1})
---

Session ID: {self.session_id}
Rate Limit: {self.rate_limiter.calls_remaining()} calls remaining this hour
Circuit Breaker: {self.circuit_breaker.state.value}
No Progress Count: {self.circuit_breaker.no_progress_count}/{self.config.max_no_progress_loops}
Consecutive Errors: {self.circuit_breaker.consecutive_error_count}/{self.config.max_consecutive_errors}
{fix_plan}

---
Instructions
---

Analyze the current state and make improvements.
When complete, output a RALPH_STATUS block:

```json
{{
  "exit_signal": true|false,
  "status": "complete|in_progress|error",
  "summary": "Brief description of what was done"
}}
```

"""

        return prompt + context

    def _should_exit(self, analysis: ResponseAnalysis) -> bool:
        """Determine if the loop should exit.

        Implements Ralph's dual-condition exit gate:
        - Requires BOTH exit signal AND completion indicators

        Args:
            analysis: The response analysis.

        Returns:
            True if loop should exit.
        """
        # Permission denial check (Issue #101)
        if analysis.has_permission_denials and self.circuit_breaker.permission_denial_count >= 2:
            self.exit_reason = "permission_denied"
            return True

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
        self._update_status_file("stopped")
        logger.info("Loop stopped by user")

    def get_iteration_logs(self) -> list[Path]:
        """Get list of iteration log files.

        Returns:
            List of log file paths.
        """
        return self._iteration_logs.copy()
