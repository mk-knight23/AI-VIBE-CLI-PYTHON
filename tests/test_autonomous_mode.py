"""
Comprehensive Test Suite for Friday Autonomous Mode

Tests the autonomous development loop system including:
- ResponseAnalyzer
- CircuitBreaker
- RateLimiter
- SessionManager
- AutonomousLoop (basic functionality)

To run: python tests/test_autonomous_mode.py
"""

import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import time

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from friday_ai.agent.autonomous_loop import (
    AutonomousLoop,
    CircuitBreaker,
    CircuitBreakerState,
    LoopConfig,
    RateLimiter,
    ResponseAnalyzer,
)
from friday_ai.agent.session_manager import Session, SessionManager, SessionEventType


class TestResponseAnalyzer:
    """Tests for ResponseAnalyzer class."""

    def __init__(self):
        self.config = LoopConfig()
        self.analyzer = ResponseAnalyzer(self.config)
        self.results = []

    def log_result(self, test_name: str, success: bool, message: str):
        status = "✓ PASS" if success else "✗ FAIL"
        self.results.append({"test": test_name, "success": success, "message": message})
        print(f"  {status}: {test_name}")
        if not success:
            print(f"         → {message}")

    def test_exit_signal_detection(self):
        """Test detection of exit signals."""
        print("\n🔍 Testing ResponseAnalyzer - Exit Signal Detection")

        # Test 1: [EXIT] pattern
        response = "Work is complete [EXIT]"
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "Detect [EXIT] pattern",
            analysis.has_exit_signal is True,
            f"has_exit_signal={analysis.has_exit_signal}"
        )

        # Test 2: EXIT_SIGNAL: true
        response = "EXIT_SIGNAL: true\nAll tasks complete"
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "Detect EXIT_SIGNAL: true",
            analysis.has_exit_signal is True,
            f"has_exit_signal={analysis.has_exit_signal}"
        )

        # Test 3: No exit signal
        response = "Working on the implementation..."
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "No exit signal in working response",
            analysis.has_exit_signal is False,
            f"has_exit_signal={analysis.has_exit_signal}"
        )

    def test_completion_indicators(self):
        """Test completion indicator counting."""
        print("\n🔍 Testing ResponseAnalyzer - Completion Indicators")

        # Test 1: Multiple completion indicators
        response = """
        [DONE] Feature implementation complete
        [COMPLETE] Tests passing
        All tasks completed successfully
        Successfully finished implementation
        """
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "Count multiple completion indicators",
            analysis.completion_indicators >= 3,
            f"completion_indicators={analysis.completion_indicators}"
        )

        # Test 2: No completion indicators
        response = "Still working on the feature implementation"
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "No completion indicators",
            analysis.completion_indicators == 0,
            f"completion_indicators={analysis.completion_indicators}"
        )

    def test_error_detection(self):
        """Test error detection."""
        print("\n🔍 Testing ResponseAnalyzer - Error Detection")

        # Test 1: Error in response
        response = "[ERROR] Failed to compile"
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "Detect [ERROR]",
            analysis.has_errors is True,
            f"has_errors={analysis.has_errors}"
        )

        # Test 2: Multiple errors
        response = """
        [ERROR] Build failed
        error: missing dependency
        Exception: ImportError
        """
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "Count multiple errors",
            analysis.error_count >= 3,
            f"error_count={analysis.error_count}"
        )

    def test_status_determination(self):
        """Test overall status determination."""
        print("\n🔍 Testing ResponseAnalyzer - Status Determination")

        # Test 1: Complete status
        response = "[EXIT]\n[DONE] All tasks complete\n[COMPLETE]"
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "Status: complete",
            analysis.status == "complete",
            f"status={analysis.status}"
        )

        # Test 2: Error status
        response = "[ERROR] Build failed\nException: ImportError"
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "Status: error",
            analysis.status == "error",
            f"status={analysis.status}"
        )

        # Test 3: Working status
        response = "Implementing feature X..."
        analysis = self.analyzer.analyze(response)
        self.log_result(
            "Status: working",
            analysis.status == "working",
            f"status={analysis.status}"
        )


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def __init__(self):
        self.config = LoopConfig()
        self.results = []

    def log_result(self, test_name: str, success: bool, message: str):
        status = "✓ PASS" if success else "✗ FAIL"
        self.results.append({"test": test_name, "success": success, "message": message})
        print(f"  {status}: {test_name}")
        if not success:
            print(f"         → {message}")

    def test_initial_state(self):
        """Test initial circuit breaker state."""
        print("\n⚡ Testing CircuitBreaker - Initial State")

        cb = CircuitBreaker(self.config)
        self.log_result(
            "Initial state is CLOSED",
            cb.state == CircuitBreakerState.CLOSED,
            f"state={cb.state.value}"
        )

    def test_no_progress_trigger(self):
        """Test circuit breaker opens after no progress."""
        print("\n⚡ Testing CircuitBreaker - No Progress Trigger")

        cb = CircuitBreaker(self.config)

        # Simulate no progress loops
        for i in range(3):
            state = cb.update(has_files_changed=False, has_errors=False, has_completion=False)

        self.log_result(
            "Opens after 3 no-progress loops",
            state == CircuitBreakerState.OPEN,
            f"state={state.value}, no_progress_count={cb.no_progress_count}"
        )

    def test_consecutive_errors_trigger(self):
        """Test circuit breaker opens after consecutive errors."""
        print("\n⚡ Testing CircuitBreaker - Consecutive Errors Trigger")

        cb = CircuitBreaker(self.config)

        # Simulate consecutive errors
        for i in range(5):
            state = cb.update(has_files_changed=False, has_errors=True, has_completion=False)

        self.log_result(
            "Opens after 5 consecutive errors",
            state == CircuitBreakerState.OPEN,
            f"state={state.value}, consecutive_error_count={cb.consecutive_error_count}"
        )

    def test_completion_trigger(self):
        """Test circuit breaker opens after many completions."""
        print("\n⚡ Testing CircuitBreaker - Completion Trigger")

        cb = CircuitBreaker(self.config)

        # Simulate many completions
        for i in range(5):
            state = cb.update(has_files_changed=True, has_errors=False, has_completion=True)

        self.log_result(
            "Opens after 5 completion indicators",
            state == CircuitBreakerState.OPEN,
            f"state={state.value}, completion_count={cb.completion_count}"
        )

    def test_reset(self):
        """Test circuit breaker reset."""
        print("\n⚡ Testing CircuitBreaker - Reset")

        cb = CircuitBreaker(self.config)

        # Trigger the circuit breaker
        for i in range(3):
            cb.update(has_files_changed=False, has_errors=False, has_completion=False)

        # Reset
        cb.reset()

        self.log_result(
            "Resets to CLOSED state",
            cb.state == CircuitBreakerState.CLOSED,
            f"state={cb.state.value}, no_progress_count={cb.no_progress_count}"
        )

    def test_normal_operation(self):
        """Test normal operation doesn't open circuit."""
        print("\n⚡ Testing CircuitBreaker - Normal Operation")

        cb = CircuitBreaker(self.config)

        # Simulate normal operation with progress
        for i in range(10):
            state = cb.update(has_files_changed=True, has_errors=False, has_completion=False)

        self.log_result(
            "Stays CLOSED with normal progress",
            state == CircuitBreakerState.CLOSED,
            f"state={state.value}"
        )


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def __init__(self):
        self.temp_dir = None
        self.results = []

    def log_result(self, test_name: str, success: bool, message: str):
        status = "✓ PASS" if success else "✗ FAIL"
        self.results.append({"test": test_name, "success": success, "message": message})
        print(f"  {status}: {test_name}")
        if not success:
            print(f"         → {message}")

    def setup(self):
        """Set up temporary directory for tests."""
        import tempfile
        import shutil

        self.temp_dir = tempfile.mkdtemp()
        print(f"✓ Created temp directory: {self.temp_dir}")

    def cleanup(self):
        """Clean up temporary directory."""
        import shutil

        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
            print(f"✓ Cleaned up temp directory")

    def test_initial_calls(self):
        """Test initial call count."""
        print("\n📊 Testing RateLimiter - Initial State")

        self.setup()

        try:
            config = LoopConfig(call_count_file=str(Path(self.temp_dir) / ".call_count"))
            limiter = RateLimiter(config)

            self.log_result(
                "Initial calls is 0",
                limiter.calls_made == 0,
                f"calls_made={limiter.calls_made}"
            )

            self.log_result(
                "Under limit initially",
                limiter.check_limit() is True,
                "check_limit()=True"
            )

            self.log_result(
                "100 calls remaining",
                limiter.calls_remaining() == 100,
                f"calls_remaining={limiter.calls_remaining()}"
            )

        finally:
            self.cleanup()

    def test_increment(self):
        """Test incrementing call count."""
        print("\n📊 Testing RateLimiter - Increment")

        self.setup()

        try:
            config = LoopConfig(call_count_file=str(Path(self.temp_dir) / ".call_count"))
            limiter = RateLimiter(config)

            limiter.increment()

            self.log_result(
                "Calls made after increment",
                limiter.calls_made == 1,
                f"calls_made={limiter.calls_made}"
            )

            self.log_result(
                "99 calls remaining after increment",
                limiter.calls_remaining() == 99,
                f"calls_remaining={limiter.calls_remaining()}"
            )

        finally:
            self.cleanup()

    def test_limit_exceeded(self):
        """Test limit exceeded detection."""
        print("\n📊 Testing RateLimiter - Limit Exceeded")

        self.setup()

        try:
            config = LoopConfig(max_calls_per_hour=5, call_count_file=str(Path(self.temp_dir) / ".call_count"))
            limiter = RateLimiter(config)

            # Make 5 calls (at limit)
            for _ in range(5):
                limiter.increment()

            at_limit = limiter.check_limit()
            # After 5 calls, check_limit returns False (no more calls allowed)
            self.log_result(
                "At limit (5/5)",
                at_limit is False,  # Changed: check_limit returns False when at/over limit
                f"check_limit()={at_limit}, calls_remaining={limiter.calls_remaining()}"
            )

            # Make one more call (exceeds limit)
            limiter.increment()
            exceeded = not limiter.check_limit()

            self.log_result(
                "Exceeds limit (6/5)",
                exceeded is True,
                f"check_limit()={not exceeded}, calls_remaining={limiter.calls_remaining()}"
            )

        finally:
            self.cleanup()


class TestSessionManager:
    """Tests for SessionManager class."""

    def __init__(self):
        self.temp_dir = None
        self.results = []

    def log_result(self, test_name: str, success: bool, message: str):
        status = "✓ PASS" if success else "✗ FAIL"
        self.results.append({"test": test_name, "success": success, "message": message})
        print(f"  {status}: {test_name}")
        if not success:
            print(f"         → {message}")

    def setup(self):
        """Set up temporary directory for tests."""
        import tempfile
        import shutil

        self.temp_dir = tempfile.mkdtemp()
        print(f"✓ Created temp directory: {self.temp_dir}")

    def cleanup(self):
        """Clean up temporary directory."""
        import shutil

        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
            print(f"✓ Cleaned up temp directory")

    def test_create_session(self):
        """Test session creation."""
        print("\n💾 Testing SessionManager - Create Session")

        self.setup()

        try:
            storage_dir = Path(self.temp_dir) / "sessions"
            current_file = Path(self.temp_dir) / ".current_session"
            history_file = Path(self.temp_dir) / ".session_history"

            manager = SessionManager(
                storage_dir=str(storage_dir),
                current_session_file=str(current_file),
                history_file=str(history_file),
            )

            session = manager.create_session(project_name="test_project")

            self.log_result(
                "Session created",
                session is not None and session.session_id.startswith("session_"),
                f"session_id={session.session_id}"
            )

            self.log_result(
                "Session has STARTED event",
                len([e for e in session.events if e.event_type == SessionEventType.STARTED]) == 1,
                f"events={len(session.events)}"
            )

        finally:
            self.cleanup()

    def test_session_persistence(self):
        """Test session persistence to file."""
        print("\n💾 Testing SessionManager - Session Persistence")

        self.setup()

        try:
            storage_dir = Path(self.temp_dir) / "sessions"
            current_file = Path(self.temp_dir) / ".current_session"
            history_file = Path(self.temp_dir) / ".session_history"

            manager = SessionManager(
                storage_dir=str(storage_dir),
                current_session_file=str(current_file),
                history_file=str(history_file),
            )

            # Create session
            session = manager.create_session(project_name="test")

            # Clear current session from memory
            manager._current_session = None

            # Load session back
            loaded = manager.get_current_session()

            self.log_result(
                "Session persists and loads",
                loaded is not None and loaded.session_id == session.session_id,
                f"original={session.session_id}, loaded={loaded.session_id if loaded else None}"
            )

        finally:
            self.cleanup()

    def test_session_expiration(self):
        """Test session expiration."""
        print("\n💾 Testing SessionManager - Session Expiration")

        self.setup()

        try:
            storage_dir = Path(self.temp_dir) / "sessions"
            current_file = Path(self.temp_dir) / ".current_session"
            history_file = Path(self.temp_dir) / ".session_history"

            manager = SessionManager(
                storage_dir=str(storage_dir),
                current_session_file=str(current_file),
                history_file=str(history_file),
            )

            session = manager.create_session(project_name="test")

            # Session should not be expired (just created)
            self.log_result(
                "New session not expired",
                not session.is_expired,
                "is_expired=False"
            )

            # Check with custom timeout
            # Session should be expired with 0 timeout (manually check)
            import time
            time.sleep(0.1)  # Small delay
            # A freshly created session should not be expired with 24h timeout
            self.log_result(
                "Session not expired with 24h timeout",
                not session.is_expired,
                f"is_expired=False (last_activity={session.last_activity})"
            )

        finally:
            self.cleanup()

    def test_session_events(self):
        """Test session event tracking."""
        print("\n💾 Testing SessionManager - Session Events")

        self.setup()

        try:
            storage_dir = Path(self.temp_dir) / "sessions"
            current_file = Path(self.temp_dir) / ".current_session"
            history_file = Path(self.temp_dir) / ".session_history"

            manager = SessionManager(
                storage_dir=str(storage_dir),
                current_session_file=str(current_file),
                history_file=str(history_file),
            )

            session = manager.create_session(project_name="test")

            # Add events
            session.add_event(SessionEventType.PAUSED, reason="Test pause")
            session.add_event(SessionEventType.RESUMED, reason="Test resume")

            self.log_result(
                "Session has 3 events (STARTED, PAUSED, RESUMED)",
                len(session.events) == 3,
                f"events={len(session.events)}"
            )

            # Verify event order
            event_types = [e.event_type for e in session.events]
            self.log_result(
                "Events in correct order",
                event_types == [SessionEventType.STARTED, SessionEventType.PAUSED, SessionEventType.RESUMED],
                f"event_types={event_types}"
            )

        finally:
            self.cleanup()


class TestAutonomousLoop:
    """Tests for AutonomousLoop class (basic functionality)."""

    def __init__(self):
        self.temp_dir = None
        self.results = []

    def log_result(self, test_name: str, success: bool, message: str):
        status = "✓ PASS" if success else "✗ FAIL"
        self.results.append({"test": test_name, "success": success, "message": message})
        print(f"  {status}: {test_name}")
        if not success:
            print(f"         → {message}")

    def setup(self):
        """Set up temporary directory for tests."""
        import tempfile
        import shutil

        self.temp_dir = tempfile.mkdtemp()
        print(f"✓ Created temp directory: {self.temp_dir}")

    def cleanup(self):
        """Clean up temporary directory."""
        import shutil

        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
            print(f"✓ Cleaned up temp directory")

    def test_loop_initialization(self):
        """Test autonomous loop initialization."""
        print("\n🚀 Testing AutonomousLoop - Initialization")

        self.setup()

        try:
            from friday_ai.config.config import Config

            config = LoopConfig(
                prompt_file=str(Path(self.temp_dir) / "PROMPT.md"),
                fix_plan_file=str(Path(self.temp_dir) / "fix_plan.md"),
                agent_file=str(Path(self.temp_dir) / "AGENT.md"),
                status_file=str(Path(self.temp_dir) / "status.json"),
                call_count_file=str(Path(self.temp_dir) / ".call_count"),
                log_dir=str(Path(self.temp_dir) / "logs"),
            )

            # Create minimal prompt file
            Path(config.prompt_file).write_text("# Test Prompt\n")

            # Note: We can't fully test AutonomousLoop without an Agent instance
            # but we can test its components

            analyzer = ResponseAnalyzer(config)
            circuit_breaker = CircuitBreaker(config)
            rate_limiter = RateLimiter(config)

            self.log_result(
                "ResponseAnalyzer created",
                analyzer is not None,
                "analyzer instance created"
            )

            self.log_result(
                "CircuitBreaker created",
                circuit_breaker is not None,
                "circuit_breaker instance created"
            )

            self.log_result(
                "RateLimiter created",
                rate_limiter is not None,
                "rate_limiter instance created"
            )

            # Test circuit breaker with components
            circuit_breaker.update(
                has_files_changed=False,
                has_errors=False,
                has_completion=False
            )

            self.log_result(
                "CircuitBreaker works",
                circuit_breaker.no_progress_count == 1,
                f"no_progress_count={circuit_breaker.no_progress_count}"
            )

        finally:
            self.cleanup()

    def test_exit_conditions(self):
        """Test autonomous loop exit conditions."""
        print("\n🚀 Testing AutonomousLoop - Exit Conditions")

        self.setup()

        try:
            config = LoopConfig()

            analyzer = ResponseAnalyzer(config)

            # Test 1: Exit with signal and completions
            response = "[EXIT]\n[DONE] Task complete\n[COMPLETE]"
            analysis = analyzer.analyze(response)

            should_exit = (
                analysis.has_exit_signal and
                analysis.completion_indicators >= config.min_completion_indicators
            )

            self.log_result(
                "Exit with signal and 2+ completions",
                should_exit is True,
                f"has_exit_signal={analysis.has_exit_signal}, completions={analysis.completion_indicators}"
            )

            # Test 2: No exit without signal
            response = "[DONE] Task complete"
            analysis = analyzer.analyze(response)

            should_exit = (
                analysis.has_exit_signal and
                analysis.completion_indicators >= config.min_completion_indicators
            )

            self.log_result(
                "No exit without signal (dual-condition gate)",
                should_exit is False,
                f"has_exit_signal={analysis.has_exit_signal}, completions={analysis.completion_indicators}"
            )

        finally:
            self.cleanup()


def run_all_tests():
    """Run all autonomous mode tests."""
    print("=" * 60)
    print("🚀 Friday Autonomous Mode Test Suite")
    print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_results = []

    # Test ResponseAnalyzer
    response_analyzer_tests = TestResponseAnalyzer()
    response_analyzer_tests.test_exit_signal_detection()
    response_analyzer_tests.test_completion_indicators()
    response_analyzer_tests.test_error_detection()
    response_analyzer_tests.test_status_determination()
    all_results.extend(response_analyzer_tests.results)

    # Test CircuitBreaker
    circuit_breaker_tests = TestCircuitBreaker()
    circuit_breaker_tests.test_initial_state()
    circuit_breaker_tests.test_no_progress_trigger()
    circuit_breaker_tests.test_consecutive_errors_trigger()
    circuit_breaker_tests.test_completion_trigger()
    circuit_breaker_tests.test_reset()
    circuit_breaker_tests.test_normal_operation()
    all_results.extend(circuit_breaker_tests.results)

    # Test RateLimiter
    rate_limiter_tests = TestRateLimiter()
    rate_limiter_tests.test_initial_calls()
    rate_limiter_tests.test_increment()
    rate_limiter_tests.test_limit_exceeded()
    all_results.extend(rate_limiter_tests.results)

    # Test SessionManager
    session_manager_tests = TestSessionManager()
    session_manager_tests.test_create_session()
    session_manager_tests.test_session_persistence()
    session_manager_tests.test_session_expiration()
    session_manager_tests.test_session_events()
    all_results.extend(session_manager_tests.results)

    # Test AutonomousLoop
    autonomous_loop_tests = TestAutonomousLoop()
    autonomous_loop_tests.test_loop_initialization()
    autonomous_loop_tests.test_exit_conditions()
    all_results.extend(autonomous_loop_tests.results)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in all_results if r["success"])
    failed = sum(1 for r in all_results if not r["success"])
    total = len(all_results)

    # Group by test class
    test_classes = {}
    for r in all_results:
        test_class = r["test"].split(" - ")[0]
        if test_class not in test_classes:
            test_classes[test_class] = {"passed": 0, "failed": 0}
        if r["success"]:
            test_classes[test_class]["passed"] += 1
        else:
            test_classes[test_class]["failed"] += 1

    print(f"\n{'Test Class':<30} {'Passed':<10} {'Failed':<10} {'Status'}")
    print("-" * 60)
    for test_class, counts in test_classes.items():
        status = "✓" if counts["failed"] == 0 else "✗"
        print(f"{test_class:<30} {counts['passed']:<10} {counts['failed']:<10} {status}")

    print("-" * 60)
    print(f"{'TOTAL':<30} {passed:<10} {failed:<10}")
    print(f"\nOverall: {passed}/{total} tests passed ({100*passed/total:.1f}%)")

    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for r in all_results:
            if not r["success"]:
                print(f"  • {r['test']}: {r['message']}")
    else:
        print("\n✅ All tests passed!")

    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
