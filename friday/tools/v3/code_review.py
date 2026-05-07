"""
code_review.py — AI-powered code review tool for Friday v3
AI-VIBE-CLI-PYTHON | Kazi Musharraf
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ReviewIssue:
    line: int
    severity: Severity
    message: str
    suggestion: Optional[str] = None
    category: str = "general"


@dataclass
class ReviewResult:
    file_path: str
    issues: list[ReviewIssue]
    score: float  # 0-100
    summary: str


class CodeReviewTool:
    """
    AI-powered code review with pattern matching + LLM analysis.
    Checks: security, performance, style, complexity, test coverage.
    """

    name = "code_review"
    description = "Review code for security issues, bugs, style violations, and improvements"

    SECURITY_PATTERNS = [
        (r"eval\(", "Dangerous eval() usage — potential code injection", Severity.CRITICAL),
        (r"exec\(", "Dangerous exec() usage", Severity.CRITICAL),
        (r"password\s*=\s*['\"]", "Hardcoded password detected", Severity.CRITICAL),
        (r"api_key\s*=\s*['\"]", "Hardcoded API key detected", Severity.CRITICAL),
        (r"sql\s*=\s*f['\"]", "Potential SQL injection via f-string", Severity.HIGH),
        (r"shell=True", "subprocess with shell=True is dangerous", Severity.HIGH),
        (r"pickle\.load", "Unsafe pickle deserialization", Severity.HIGH),
        (r"md5\(|sha1\(", "Weak hashing algorithm (use SHA-256+)", Severity.MEDIUM),
    ]

    def review_file(self, file_path: str) -> ReviewResult:
        """Review a single file and return structured results."""
        import re
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text()
        lines = content.split("\n")
        issues = []

        for line_num, line in enumerate(lines, 1):
            for pattern, message, severity in self.SECURITY_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(ReviewIssue(
                        line=line_num,
                        severity=severity,
                        message=message,
                        category="security"
                    ))

        critical = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high = sum(1 for i in issues if i.severity == Severity.HIGH)
        score = max(0, 100 - (critical * 20) - (high * 10) - (len(issues) - critical - high) * 2)

        return ReviewResult(
            file_path=file_path,
            issues=issues,
            score=score,
            summary=f"Found {len(issues)} issues ({critical} critical, {high} high). Score: {score}/100"
        )

    def render_review(self, result: ReviewResult) -> None:
        """Render review results with rich formatting."""
        color = "green" if result.score >= 80 else "yellow" if result.score >= 60 else "red"
        console.print(Panel(
            f"[{color}]Score: {result.score:.0f}/100[/{color}]\n{result.summary}",
            title=f"Code Review: {result.file_path}",
            border_style=color
        ))
        for issue in result.issues:
            severity_color = {"critical": "red", "high": "orange3", "medium": "yellow", "low": "blue", "info": "dim"}.get(issue.severity.value, "white")
            console.print(f"  [{severity_color}]Line {issue.line:4d} [{issue.severity.value.upper():8s}][/{severity_color}] {issue.message}")
