"""Tests for claude_integration utilities."""

import tempfile
from pathlib import Path

import pytest

from friday_ai.claude_integration.utils import (
    ensure_claude_structure,
    find_claude_dir,
    load_markdown_file,
    parse_frontmatter,
)


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_simple_frontmatter(self):
        content = """---
name: test-agent
description: A test agent
---
# Content here
Some markdown content.
"""
        frontmatter, markdown = parse_frontmatter(content)
        assert frontmatter == {"name": "test-agent", "description": "A test agent"}
        assert markdown == "# Content here\nSome markdown content."

    def test_no_frontmatter(self):
        content = "# Just markdown\nNo frontmatter here."
        frontmatter, markdown = parse_frontmatter(content)
        assert frontmatter == {}
        assert markdown == "# Just markdown\nNo frontmatter here."

    def test_empty_frontmatter(self):
        content = """---
---
# Content here
"""
        frontmatter, markdown = parse_frontmatter(content)
        assert frontmatter == {}
        assert markdown == "# Content here"

    def test_multiline_frontmatter(self):
        content = """---
name: test
tools:
  - read_file
  - edit_file
---
Content
"""
        frontmatter, markdown = parse_frontmatter(content)
        assert frontmatter["name"] == "test"
        assert frontmatter["tools"] == ["read_file", "edit_file"]
        assert markdown == "Content"


class TestFindClaudeDir:
    """Tests for find_claude_dir function."""

    def test_find_in_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Save and restore original working directory
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(tmp)
                claude_dir = Path(tmp) / ".claude"
                claude_dir.mkdir()
                found = find_claude_dir(Path(tmp))
                assert found is not None and found.exists()
            finally:
                os.chdir(original_cwd)

    def test_find_in_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Save and restore original working directory
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(tmp)
                claude_dir = Path(tmp) / ".claude"
                claude_dir.mkdir()
                subdir = Path(tmp) / "subdir" / "nested"
                subdir.mkdir(parents=True)

                found = find_claude_dir(subdir)
                assert found is not None and found.exists()
            finally:
                os.chdir(original_cwd)

    def test_not_found(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            # Clear CLAUDE_DIR env var to avoid finding ~/.claude
            monkeypatch.delenv("CLAUDE_DIR", raising=False)
            # Save and restore original working directory
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(tmp)
                # Also unset HOME to avoid finding ~/.claude
                monkeypatch.setenv("HOME", tmp)
                found = find_claude_dir(Path(tmp))
                # Should not find any .claude directory
                assert found is None or tmp not in str(found)
            finally:
                os.chdir(original_cwd)

    def test_env_variable(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / "custom_claude"
            claude_dir.mkdir()
            monkeypatch.setenv("CLAUDE_DIR", str(claude_dir))

            found = find_claude_dir(Path(tmp) / "somewhere")
            assert found == claude_dir


class TestLoadMarkdownFile:
    """Tests for load_markdown_file function."""

    def test_load_valid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "test.md"
            file_path.write_text("---\nname: test\n---\n# Hello")

            result = load_markdown_file(file_path)
            assert result is not None
            frontmatter, content = result
            assert frontmatter["name"] == "test"
            assert content == "# Hello"

    def test_load_nonexistent_file(self):
        result = load_markdown_file(Path("/nonexistent/file.md"))
        assert result is None


class TestEnsureClaudeStructure:
    """Tests for ensure_claude_structure function."""

    def test_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            structure = ensure_claude_structure(claude_dir)

            assert (claude_dir / "agents").exists()
            assert (claude_dir / "commands").exists()
            assert (claude_dir / "skills").exists()
            assert (claude_dir / "workflows").exists()
            assert (claude_dir / "rules").exists()
            assert (claude_dir / "scripts").exists()
            assert (claude_dir / "templates").exists()

    def test_returns_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            claude_dir.mkdir()

            structure = ensure_claude_structure(claude_dir)

            assert "agents" in structure
            assert "commands" in structure
            assert structure["agents"] == claude_dir / "agents"
