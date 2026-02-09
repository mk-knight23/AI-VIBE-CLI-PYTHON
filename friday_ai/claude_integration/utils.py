"""Utility functions for .claude folder integration."""

from __future__ import annotations

import os
from pathlib import Path


def find_claude_dir(start_path: Path | None = None) -> Path | None:
    """Find .claude directory by walking up from start_path.

    Searches in this order:
    1. Walk up from start_path looking for .claude/
    2. Check CLAUDE_DIR environment variable
    3. Check ~/.claude/ in home directory

    Args:
        start_path: Starting directory for search. Defaults to current working directory.

    Returns:
        Path to .claude directory if found, None otherwise.
    """
    # Search from start_path upward
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()
    while current != current.parent:
        claude_dir = current / ".claude"
        if claude_dir.exists() and claude_dir.is_dir():
            return claude_dir
        current = current.parent

    # Check environment variable
    env_claude_dir = os.environ.get("CLAUDE_DIR")
    if env_claude_dir:
        path = Path(env_claude_dir)
        if path.exists() and path.is_dir():
            return path

    # Fallback to home directory
    home_claude = Path.home() / ".claude"
    if home_claude.exists() and home_claude.is_dir():
        return home_claude

    return None


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and markdown content from a file.

    Frontmatter is defined as YAML between triple dashes at the start:
    ---
    key: value
    ---
    markdown content here

    Args:
        content: The file content to parse.

    Returns:
        Tuple of (frontmatter dict, markdown content string).
        If no frontmatter found, returns ({}, content).
    """
    import re

    # First, handle the empty frontmatter case: ---\n---\n...
    if content.startswith("---\n---\n"):
        return {}, content[8:].strip()  # Skip the first 8 chars "---\n---\n"

    # Pattern for non-empty frontmatter
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)"
    match = re.match(pattern, content, re.DOTALL)

    if match:
        import yaml

        frontmatter_text = match.group(1)
        markdown = match.group(2)

        try:
            frontmatter = yaml.safe_load(frontmatter_text) if frontmatter_text.strip() else {}
        except yaml.YAMLError:
            frontmatter = {}

        return frontmatter, markdown.strip()

    return {}, content.strip()


def load_markdown_file(path: Path) -> tuple[dict, str] | None:
    """Load and parse a markdown file with YAML frontmatter.

    Args:
        path: Path to the markdown file.

    Returns:
        Tuple of (frontmatter dict, markdown content) or None if file cannot be read.
    """
    try:
        content = path.read_text(encoding="utf-8")
        return parse_frontmatter(content)
    except (IOError, OSError, UnicodeDecodeError):
        return None


def ensure_claude_structure(claude_dir: Path) -> dict[str, Path]:
    """Ensure required .claude directory structure exists.

    Args:
        claude_dir: Path to the .claude directory.

    Returns:
        Dictionary mapping structure names to paths.
    """
    structure = {
        "agents": claude_dir / "agents",
        "commands": claude_dir / "commands",
        "skills": claude_dir / "skills",
        "workflows": claude_dir / "workflows",
        "rules": claude_dir / "rules",
        "scripts": claude_dir / "scripts",
        "templates": claude_dir / "templates",
    }

    # Create directories that don't exist (for future use)
    for path in structure.values():
        path.mkdir(parents=True, exist_ok=True)

    return structure
