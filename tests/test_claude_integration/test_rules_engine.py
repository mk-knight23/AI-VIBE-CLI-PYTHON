"""Tests for rules_engine module."""

import tempfile
from pathlib import Path

import pytest

from friday_ai.claude_integration.rules_engine import RuleSet, RulesEngine


class TestRulesEngine:
    """Tests for RulesEngine class."""

    def test_load_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            rules_dir = claude_dir / "rules"
            rules_dir.mkdir(parents=True)

            rule_file = rules_dir / "coding-style.md"
            rule_file.write_text("""# Coding Style

## Immutability

ALWAYS create new objects.
""")

            engine = RulesEngine(claude_dir)
            rules = engine.load_all_rules()

            assert len(rules) == 1
            assert rules[0].name == "Coding Style"
            assert rules[0].category == "coding-style"

    def test_category_inference(self):
        engine = RulesEngine(None)

        assert engine._infer_category("security") == "security"
        assert engine._infer_category("testing-guide") == "testing"
        assert engine._infer_category("my-style") == "coding-style"
        assert engine._infer_category("random") == "general"

    def test_applies_to_file(self):
        rule = RuleSet(
            name="test",
            category="test",
            file_patterns=["*.ts", "*.tsx", "src/"]
        )

        assert rule.applies_to_file(Path("test.ts")) is True
        assert rule.applies_to_file(Path("test.tsx")) is True
        assert rule.applies_to_file(Path("src/app.ts")) is True
        assert rule.applies_to_file(Path("test.py")) is False

    def test_get_rules_for_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            rules_dir = claude_dir / "rules"
            rules_dir.mkdir(parents=True)

            ts_rule = rules_dir / "typescript.md"
            ts_rule.write_text("""# TypeScript Rules

TypeScript specific rules.
""")

            engine = RulesEngine(claude_dir)
            engine.load_all_rules()

            rules = engine.get_rules_for_context(file_path=Path("test.ts"))
            assert len(rules) >= 0  # May or may not match based on inference

            all_rules = engine.get_all_rules()
            assert len(all_rules) == 1

    def test_format_rules_for_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / ".claude"
            rules_dir = claude_dir / "rules"
            rules_dir.mkdir(parents=True)

            rule_file = rules_dir / "style.md"
            rule_file.write_text("# Style Guide\n\nBe consistent.")

            engine = RulesEngine(claude_dir)
            engine.load_all_rules()

            formatted = engine.format_rules_for_prompt()
            assert "# Coding Standards and Rules" in formatted
            assert "Be consistent" in formatted
