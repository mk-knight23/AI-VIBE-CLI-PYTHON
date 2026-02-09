"""Rules engine for .claude/rules/ directory.

Loads and manages coding standards and rules from rule markdown files,
supporting context-aware rule selection based on file types and operations.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RuleSet:
    """A set of coding rules from a .claude/rules/*.md file.

    Attributes:
        name: Name of the rule set (from filename or H1 title)
        category: Category of rules (e.g., "coding-style", "security", "testing")
        content: The full rule content (markdown)
        priority: Priority for ordering (higher = more important)
        file_patterns: List of file patterns these rules apply to
    """

    name: str
    category: str = "general"
    content: str = ""
    priority: int = 0
    file_patterns: list[str] = field(default_factory=list)

    def applies_to_file(self, file_path: Path) -> bool:
        """Check if these rules apply to a given file path.

        Args:
            file_path: The file to check.

        Returns:
            True if rules apply to this file.
        """
        if not self.file_patterns:
            return True  # Applies to all files by default

        import fnmatch

        file_name = file_path.name
        file_ext = file_path.suffix.lstrip(".")
        file_path_str = str(file_path)

        for pattern in self.file_patterns:
            # Exact filename match
            if file_name == pattern:
                return True
            # Extension match
            if pattern.startswith("*.") and file_name.endswith(pattern[1:]):
                return True
            if file_ext == pattern.lstrip("*."):
                return True
            # Glob pattern
            if "*" in pattern or "?" in pattern:
                if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(
                    file_path_str, pattern
                ):
                    return True
            # Path substring
            if pattern in file_path_str:
                return True

        return False


class RulesEngine:
    """Engine for loading and applying coding rules from .claude/rules/."""

    # Category mappings based on filename patterns
    CATEGORY_MAPPINGS = {
        "coding-style": ["coding", "style", "formatting"],
        "security": ["security", "auth", "safe"],
        "testing": ["test", "testing", "coverage", "tdd"],
        "performance": ["perf", "performance", "optimize"],
        "git": ["git", "commit", "branch", "merge"],
        "agents": ["agent", "subagent", "orchestration"],
    }

    def __init__(self, claude_dir: Path | None):
        """Initialize the rules engine.

        Args:
            claude_dir: Path to the .claude directory. If None, no rules will be loaded.
        """
        self.claude_dir = claude_dir
        self.rules_dir = claude_dir / "rules" if claude_dir else None
        self._rules: list[RuleSet] = []

    def load_all_rules(self) -> list[RuleSet]:
        """Load all rule definitions from the rules directory.

        Returns:
            List of loaded rule sets.
        """
        if not self.rules_dir or not self.rules_dir.exists():
            logger.debug("No .claude/rules directory found")
            return []

        rules = []
        for md_file in sorted(self.rules_dir.glob("*.md")):
            try:
                rule_set = self._parse_rule_file(md_file)
                if rule_set:
                    rules.append(rule_set)
                    logger.debug(f"Loaded rules: {rule_set.name} ({rule_set.category})")
            except Exception as e:
                logger.warning(f"Failed to parse rule file {md_file}: {e}")
                continue

        # Sort by priority (higher first)
        self._rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        return self._rules

    def _parse_rule_file(self, path: Path) -> RuleSet | None:
        """Parse a single rule markdown file.

        Args:
            path: Path to the .md file.

        Returns:
            Parsed rule set or None if parsing failed.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except (IOError, OSError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read rule file {path}: {e}")
            return None

        # Extract name from H1 title or filename
        name = path.stem
        category = self._infer_category(path.stem)

        # Try to extract H1 title
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1_match:
            name = h1_match.group(1).strip()

        # Try to infer category from content sections
        category_from_content = self._extract_category_from_content(content)
        if category_from_content:
            category = category_from_content

        # Extract file patterns if specified
        file_patterns = self._extract_file_patterns(content)

        # Determine priority based on category
        priority = self._calculate_priority(category, content)

        return RuleSet(
            name=name,
            category=category,
            content=content,
            priority=priority,
            file_patterns=file_patterns,
        )

    def _infer_category(self, filename: str) -> str:
        """Infer rule category from filename."""
        filename_lower = filename.lower()

        for category, keywords in self.CATEGORY_MAPPINGS.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    return category

        return "general"

    def _extract_category_from_content(self, content: str) -> str | None:
        """Try to extract category from content metadata or structure."""
        # Look for category in comments or frontmatter-like sections
        category_match = re.search(
            r"(?:category|type):\s*(\w+)", content, re.IGNORECASE
        )
        if category_match:
            return category_match.group(1).lower()

        return None

    def _extract_file_patterns(self, content: str) -> list[str]:
        """Extract file patterns that these rules apply to."""
        patterns = []

        # Look for patterns like "Applies to: *.ts, *.tsx" or "Files: *.py"
        applies_match = re.search(
            r"(?:applies?\s*to|files?|patterns?):\s*([\w\s,.*\-/]+)",
            content,
            re.IGNORECASE,
        )
        if applies_match:
            pattern_text = applies_match.group(1)
            patterns = [p.strip() for p in pattern_text.split(",") if p.strip()]

        return patterns

    def _calculate_priority(self, category: str, content: str) -> int:
        """Calculate priority based on category and content."""
        # Security rules are highest priority
        priority = 0

        if category == "security":
            priority = 100
        elif category == "testing":
            priority = 80
        elif category == "performance":
            priority = 60
        elif category == "coding-style":
            priority = 40
        elif category == "git":
            priority = 20

        # Boost priority for critical/important rules
        if re.search(r"\(CRITICAL\)|\(MANDATORY\)|\(REQUIRED\)", content, re.IGNORECASE):
            priority += 50
        elif re.search(r"\(IMPORTANT\)|\(HIGH\)", content, re.IGNORECASE):
            priority += 25

        return priority

    def get_all_rules(self) -> list[RuleSet]:
        """Get all loaded rules.

        Returns:
            List of all rule sets in priority order.
        """
        return self._rules.copy()

    def get_rules_for_context(
        self,
        file_path: Path | None = None,
        operation: str | None = None,
        category: str | None = None,
    ) -> list[RuleSet]:
        """Get rules relevant to the current context.

        Args:
            file_path: Optional file path to filter by.
            operation: Optional operation type.
            category: Optional category filter.

        Returns:
            List of relevant rule sets in priority order.
        """
        relevant = []

        for rule in self._rules:
            # Filter by category if specified
            if category and rule.category != category:
                continue

            # Filter by file path if specified
            if file_path and not rule.applies_to_file(file_path):
                continue

            # Filter by operation if specified (match against category or name)
            if operation:
                op_lower = operation.lower()
                if op_lower not in rule.category.lower() and op_lower not in rule.name.lower():
                    # Check if operation matches file patterns
                    if file_path and not rule.applies_to_file(file_path):
                        continue

            relevant.append(rule)

        return relevant

    def format_rules_for_prompt(
        self,
        rules: list[RuleSet] | None = None,
        include_categories: list[str] | None = None,
        exclude_categories: list[str] | None = None,
    ) -> str:
        """Format rules for system prompt injection.

        Args:
            rules: Optional list of rules to format. If None, uses all loaded rules.
            include_categories: Optional list of categories to include.
            exclude_categories: Optional list of categories to exclude.

        Returns:
            Formatted rules content for prompt.
        """
        if rules is None:
            rules = self._rules

        # Apply category filters
        if include_categories:
            include_set = {c.lower() for c in include_categories}
            rules = [r for r in rules if r.category.lower() in include_set]

        if exclude_categories:
            exclude_set = {c.lower() for c in exclude_categories}
            rules = [r for r in rules if r.category.lower() not in exclude_set]

        if not rules:
            return ""

        lines = ["# Coding Standards and Rules\n"]

        # Group by category
        by_category: dict[str, list[RuleSet]] = {}
        for rule in rules:
            if rule.category not in by_category:
                by_category[rule.category] = []
            by_category[rule.category].append(rule)

        # Output grouped by category
        for category in sorted(by_category.keys()):
            category_rules = sorted(
                by_category[category], key=lambda r: r.priority, reverse=True
            )

            lines.append(f"## {category.replace('-', ' ').title()} Rules")
            lines.append("")

            for rule in category_rules:
                lines.append(f"### {rule.name}")
                lines.append(rule.content)
                lines.append("")

        return "\n".join(lines)

    def get_rules_by_category(self, category: str) -> list[RuleSet]:
        """Get all rules for a specific category.

        Args:
            category: The category to filter by.

        Returns:
            List of rules in that category.
        """
        return [r for r in self._rules if r.category.lower() == category.lower()]
