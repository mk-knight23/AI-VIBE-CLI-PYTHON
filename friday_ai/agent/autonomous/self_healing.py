"""Self-healing module for autonomous mode - automatically fix errors."""

import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors that can be self-healed."""

    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    RUNTIME_ERROR = "runtime_error"
    TEST_FAILURE = "test_failure"
    TYPE_ERROR = "type_error"
    ATTRIBUTE_ERROR = "attribute_error"
    NAME_ERROR = "name_error"
    REFERENCE_ERROR = "reference_error"
    VALUE_ERROR = "value_error"
    PERMISSION_ERROR = "permission_error"
    FILE_NOT_FOUND = "file_not_found"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Information about an error."""

    error_type: ErrorType
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stack_trace: Optional[str] = None
    suggestion: Optional[str] = None


class SelfHealer:
    """Self-healing system for automatic error fixes."""

    # Error patterns for detection
    ERROR_PATTERNS = {
        ErrorType.SYNTAX_ERROR: [
            r"syntax error",
            r"invalid syntax",
            r"unexpected indent",
            r"expected.*token",
        ],
        ErrorType.IMPORT_ERROR: [
            r"import error",
            r"no module named",
            r"cannot import",
            r"module not found",
        ],
        ErrorType.TYPE_ERROR: [
            r"type error",
            r"unsupported operand",
            r"'.*' object is not",
        ],
        ErrorType.ATTRIBUTE_ERROR: [
            r"attribute error",
            r"module.*has no attribute",
            r"has no attribute",
        ],
        ErrorType.NAME_ERROR: [
            r"name error",
            r"name.*is not defined",
        ],
        ErrorType.VALUE_ERROR: [
            r"value error",
            r"invalid value",
        ],
        ErrorType.FILE_NOT_FOUND: [
            r"file not found",
            r"no such file",
            r"file.*does not exist",
        ],
        ErrorType.PERMISSION_ERROR: [
            r"permission denied",
            r"access denied",
        ],
    }

    # Fix strategies
    FIX_STRATEGIES = {
        ErrorType.SYNTAX_ERROR: [
            "Check for missing colons, parentheses, or brackets",
            "Ensure consistent indentation",
            "Look for typos in keywords",
        ],
        ErrorType.IMPORT_ERROR: [
            "Install the missing package",
            "Check the import statement for typos",
            "Verify the package is installed in the current environment",
            "Try importing from a different module",
        ],
        ErrorType.TYPE_ERROR: [
            "Check the types of variables being used",
            "Add type conversion if needed",
            "Ensure function arguments have correct types",
        ],
        ErrorType.ATTRIBUTE_ERROR: [
            "Check if the attribute exists on the object",
            "Verify the object is properly initialized",
            "Look for typos in attribute names",
        ],
        ErrorType.NAME_ERROR: [
            "Define the variable before using it",
            "Check for typos in variable names",
            "Import the required module",
        ],
        ErrorType.VALUE_ERROR: [
            "Validate input values are in expected ranges",
            "Check string formats and parsing",
        ],
        ErrorType.FILE_NOT_FOUND: [
            "Verify the file path is correct",
            "Check if the file was moved or deleted",
            "Create the file if it doesn't exist",
        ],
        ErrorType.PERMISSION_ERROR: [
            "Check file permissions",
            "Run with appropriate user privileges",
            "Change file ownership if needed",
        ],
    }

    def __init__(self):
        """Initialize the self-healer."""
        self._error_history: list[ErrorInfo] = []
        self._fix_count = 0
        self._max_auto_fixes = 5

    def analyze_error(self, error_output: str) -> ErrorInfo:
        """Analyze error output and extract error information.

        Args:
            error_output: The error output to analyze.

        Returns:
            ErrorInfo object with parsed details.
        """
        # Detect error type
        error_type = self._detect_error_type(error_output)

        # Extract file and line if present
        file_path, line, column = self._extract_location(error_output)

        # Generate suggestion
        suggestion = self._generate_suggestion(error_type, error_output)

        error_info = ErrorInfo(
            error_type=error_type,
            message=error_output.strip(),
            file=file_path,
            line=line,
            column=column,
            suggestion=suggestion,
        )

        self._error_history.append(error_info)
        logger.info(f"Analyzed error: {error_type.value} - {file_path}:{line}")

        return error_info

    def _detect_error_type(self, error_output: str) -> ErrorType:
        """Detect the type of error from output.

        Args:
            error_output: The error output.

        Returns:
            Detected ErrorType.
        """
        error_lower = error_output.lower()

        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_lower):
                    return error_type

        return ErrorType.UNKNOWN

    def _extract_location(self, error_output: str) -> tuple[Optional[str], Optional[int], Optional[int]]:
        """Extract file path and line number from error.

        Args:
            error_output: The error output.

        Returns:
            Tuple of (file_path, line, column).
        """
        # Pattern for Python tracebacks
        traceback_pattern = r'File "([^"]+)", line (\d+)'
        match = re.search(traceback_pattern, error_output)
        if match:
            return match.group(1), int(match.group(2)), None

        # Pattern for syntax errors
        syntax_pattern = r'([^:]+):(\d+):'
        match = re.search(syntax_pattern, error_output)
        if match:
            return match.group(1), int(match.group(2)), None

        return None, None, None

    def _generate_suggestion(self, error_type: ErrorType, error_output: str) -> str:
        """Generate a suggestion for fixing the error.

        Args:
            error_type: The type of error.
            error_output: The error output.

        Returns:
            Suggestion string.
        """
        strategies = self.FIX_STRATEGIES.get(error_type, ["Review the error message carefully"])

        # Look for specific patterns in the error
        if "python" in error_output.lower():
            if error_type == ErrorType.IMPORT_ERROR:
                return "Try running 'pip install <package-name>'"

        return strategies[0]

    def get_fix_suggestions(self, error_type: ErrorType) -> list[str]:
        """Get suggestions for fixing an error type.

        Args:
            error_type: The type of error.

        Returns:
            List of suggestion strings.
        """
        return self.FIX_STRATEGIES.get(error_type, ["Review the error message"])

    def attempt_fix(
        self,
        error_info: ErrorInfo,
        context: Optional[dict] = None,
    ) -> Optional[str]:
        """Attempt to automatically fix an error.

        Args:
            error_info: Information about the error.
            context: Additional context about the error.

        Returns:
            Description of the fix applied, or None if no fix was applied.
        """
        if self._fix_count >= self._max_auto_fixes:
            logger.warning("Max auto-fixes reached")
            return None

        # Different fix strategies based on error type
        if error_info.error_type == ErrorType.IMPORT_ERROR:
            fix = self._fix_import_error(error_info, context)
        elif error_info.error_type == ErrorType.FILE_NOT_FOUND:
            fix = self._fix_file_not_found(error_info, context)
        else:
            fix = None

        if fix:
            self._fix_count += 1
            logger.info(f"Applied fix: {fix}")

        return fix

    def _fix_import_error(
        self,
        error_info: ErrorInfo,
        context: Optional[dict] = None,
    ) -> Optional[str]:
        """Fix import errors by installing missing packages.

        Args:
            error_info: Error information.
            context: Additional context.

        Returns:
            Description of fix or None.
        """
        # Extract module name from error
        error_msg = error_info.message.lower()

        # Pattern to extract module name
        patterns = [
            r"no module named ['\"]([^'\"]+)['\"]",
            r"cannot import ['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_msg)
            if match:
                module_name = match.group(1)
                logger.info(f"Detected missing module: {module_name}")
                return f"Install package: pip install {module_name}"

        return None

    def _fix_file_not_found(
        self,
        error_info: ErrorInfo,
        context: Optional[dict] = None,
    ) -> Optional[str]:
        """Fix file not found errors.

        Args:
            error_info: Error information.
            context: Additional context.

        Returns:
            Description of fix or None.
        """
        if error_info.file:
            return f"Create missing file: {error_info.file}"

        return None

    def analyze_test_failure(
        self,
        test_output: str,
    ) -> ErrorInfo:
        """Analyze test failure output.

        Args:
            test_output: The test output.

        Returns:
            ErrorInfo with failure details.
        """
        # Check for specific test failure patterns
        if "assertionerror" in test_output.lower():
            error_type = ErrorType.TEST_FAILURE
        elif "test.*failed" in test_output.lower():
            error_type = ErrorType.TEST_FAILURE
        else:
            error_type = self._detect_error_type(test_output)

        suggestion = "Run the failing test to see detailed output"
        if "assertionerror" in test_output.lower():
            suggestion = "Check the expected vs actual values in the assertion"

        return ErrorInfo(
            error_type=error_type,
            message=test_output.strip(),
            suggestion=suggestion,
        )

    def get_error_history(self) -> list[ErrorInfo]:
        """Get the error history.

        Returns:
            List of past errors.
        """
        return self._error_history.copy()

    def get_stats(self) -> dict:
        """Get self-healing statistics.

        Returns:
            Statistics dictionary.
        """
        return {
            "total_errors": len(self._error_history),
            "auto_fixes_attempted": self._fix_count,
            "error_counts": {
                et.value: sum(1 for e in self._error_history if e.error_type == et)
                for et in ErrorType
            },
        }

    def reset(self) -> None:
        """Reset the self-healer state."""
        self._error_history.clear()
        self._fix_count = 0


class ErrorRecovery:
    """Error recovery strategies for autonomous mode."""

    def __init__(self):
        """Initialize error recovery."""
        self.healer = SelfHealer()

    async def recover_from_error(
        self,
        error_output: str,
        context: Optional[dict] = None,
    ) -> dict:
        """Attempt to recover from an error.

        Args:
            error_output: The error output.
            context: Additional context.

        Returns:
            Recovery result dictionary.
        """
        result = {
            "recovered": False,
            "error_type": None,
            "suggestions": [],
            "fix_applied": None,
            "message": "",
        }

        # Analyze the error
        error_info = self.healer.analyze_error(error_output)
        result["error_type"] = error_info.error_type.value

        # Get suggestions
        result["suggestions"] = self.healer.get_fix_suggestions(error_info.error_type)

        # Attempt auto-fix
        fix = self.healer.attempt_fix(error_info, context)
        if fix:
            result["fix_applied"] = fix
            result["recovered"] = True
            result["message"] = f"Applied fix: {fix}"
        else:
            result["message"] = "Manual intervention required"

        return result

    def get_recovery_strategies(self, error_type: ErrorType) -> list[str]:
        """Get recovery strategies for an error type.

        Args:
            error_type: The type of error.

        Returns:
            List of recovery strategy descriptions.
        """
        strategies = {
            ErrorType.SYNTAX_ERROR: [
                "Review the code around the error location",
                "Check for missing syntax elements",
                "Try running python -m py_compile to identify the exact line",
            ],
            ErrorType.IMPORT_ERROR: [
                "Verify the package is installed",
                "Check Python path and environment",
                "Try reinstalling the package",
            ],
            ErrorType.TEST_FAILURE: [
                "Run the test in isolation",
                "Check test setup and fixtures",
                "Review the assertion that failed",
            ],
        }

        return strategies.get(error_type, ["Review the error and fix accordingly"])
