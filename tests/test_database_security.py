"""Tests for database tool SQL injection prevention."""

import pytest

from friday_ai.tools.builtin.database import _is_safe_table_name


class TestSafeTableName:
    """Test table name validation."""

    def test_valid_table_names(self):
        """Test that valid table names pass validation."""
        valid_names = [
            "users",
            "user_profiles",
            "table-123",
            "data-2024",
            "my_table",
            "TABLE123",
        ]

        for name in valid_names:
            assert _is_safe_table_name(name), f"Table name '{name}' should be valid"

    def test_invalid_characters(self):
        """Test that table names with invalid characters are rejected."""
        invalid_names = [
            "users; DROP TABLE--",
            "users OR 1=1",
            "users' OR '1'='1",
            "users\" OR \"1\"=\"1",
            "users; SELECT * FROM--",
            "users--comment",
            "users/*comment*/",
            "users`id`",
        ]

        for name in invalid_names:
            assert not _is_safe_table_name(name), f"Table name '{name}' should be invalid"

    def test_sql_keywords(self):
        """Test that SQL keywords are blocked in table names."""
        sql_keywords = [
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "UNION",
            "WHERE",
            "OR",
            "AND",
            "FROM",
            "JOIN",
        ]

        for keyword in sql_keywords:
            assert not _is_safe_table_name(keyword), f"SQL keyword '{keyword}' should be invalid"

    def test_empty_string(self):
        """Test that empty table name is rejected."""
        assert not _is_safe_table_name("")

    def test_too_long_name(self):
        """Test that table names over 64 characters are rejected."""
        too_long = "a" * 65  # 65 characters
        assert not _is_safe_table_name(too_long)

    def test_exactly_64_characters(self):
        """Test that table names exactly 64 characters are accepted."""
        valid_64 = "a" * 64  # 64 characters
        assert _is_safe_table_name(valid_64)
