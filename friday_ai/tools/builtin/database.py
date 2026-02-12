"""Database tool for executing SQL queries against configured databases."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from friday_ai.tools.base import Tool, ToolInvocation, ToolResult

logger = logging.getLogger(__name__)


def _is_safe_table_name(name: str) -> bool:
    """Validate table name is safe from SQL injection.

    Args:
        name: Table name to validate

    Returns:
        True if safe, False otherwise
    """
    # Allow alphanumeric, underscore, and single dash between alphanumerics
    # Prevents SQL metacharacters and injection attempts
    # Pattern: start with alphanumeric, end with alphanumeric
    # Middle can contain: alphanumeric, underscore, single dash between alphanumerics
    if not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9_\-]?[a-zA-Z0-9])*$", name):
        return False

    # Must be 1-64 characters
    if len(name) < 1 or len(name) > 64:
        return False

    # Block SQL keywords
    sql_keywords = {
        "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
        "TRUNCATE", "UNION", "OR", "AND", "WHERE", "JOIN", "FROM"
    }
    if name.upper() in sql_keywords:
        return False

    return True


class DatabaseTool(Tool):
    """Tool for executing SQL queries against databases.

    Supports PostgreSQL, MySQL, and SQLite databases.
    Connection can be configured via environment variables or config.
    """

    name = "database"
    description = "Execute SQL queries against configured databases (PostgreSQL, MySQL, SQLite)"

    schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL query to execute",
            },
            "database": {
                "type": "string",
                "description": "Database name or connection key (default: 'default')",
            },
            "action": {
                "type": "string",
                "enum": ["query", "execute", "schema", "tables"],
                "description": "Action type: query (SELECT), execute (INSERT/UPDATE/DELETE), schema (table structure), tables (list tables)",
            },
            "table": {
                "type": "string",
                "description": "Table name (for schema action)",
            },
        },
        "required": ["action"],
    }

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """Check if the database operation mutates state."""
        action = params.get("action", "query")
        if action in ("execute",):
            return True
        if action == "query":
            query = params.get("query", "").strip().upper()
            mutating_keywords = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER")
            return query.startswith(mutating_keywords)
        return False

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute database operation."""
        params = invocation.params
        action = params.get("action")

        if not action:
            return ToolResult.error_result("No action specified")

        try:
            if action == "query":
                return await self._execute_query(params)
            elif action == "execute":
                return await self._execute_command(params)
            elif action == "schema":
                return await self._get_schema(params)
            elif action == "tables":
                return await self._list_tables(params)
            else:
                return ToolResult.error_result(f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"Database {action} failed")
            return ToolResult.error_result(f"Database operation failed: {e}")

    async def _execute_query(self, params: dict[str, Any]) -> ToolResult:
        """Execute a SELECT query."""
        query = params.get("query")
        if not query:
            return ToolResult.error_result("Query is required")

        db_type, connection = self._get_connection(params.get("database", "default"))

        try:
            if db_type == "sqlite":
                return await self._sqlite_query(connection, query)
            elif db_type == "postgresql":
                return await self._postgresql_query(connection, query)
            elif db_type == "mysql":
                return await self._mysql_query(connection, query)
            else:
                return ToolResult.error_result(f"Unsupported database type: {db_type}")
        except Exception as e:
            return ToolResult.error_result(f"Query failed: {e}")

    async def _execute_command(self, params: dict[str, Any]) -> ToolResult:
        """Execute a mutating SQL command."""
        query = params.get("query")
        if not query:
            return ToolResult.error_result("Query is required")

        db_type, connection = self._get_connection(params.get("database", "default"))

        try:
            if db_type == "sqlite":
                return await self._sqlite_execute(connection, query)
            elif db_type == "postgresql":
                return await self._postgresql_execute(connection, query)
            elif db_type == "mysql":
                return await self._mysql_execute(connection, query)
            else:
                return ToolResult.error_result(f"Unsupported database type: {db_type}")
        except Exception as e:
            return ToolResult.error_result(f"Execute failed: {e}")

    async def _get_schema(self, params: dict[str, Any]) -> ToolResult:
        """Get table schema."""
        table = params.get("table")
        if not table:
            return ToolResult.error_result("Table name is required")

        # Validate table name to prevent SQL injection
        if not self._is_safe_table_name(table):
            return ToolResult.error_result(
                f"Invalid table name: {table}",
                metadata={"error": "Table name contains unsafe characters"}
            )

        db_type, connection = self._get_connection(params.get("database", "default"))

        try:
            if db_type == "sqlite":
                # Use parameterized query for PRAGMA with table name validation
                query = "PRAGMA table_info(?)"
                return await self._sqlite_query(connection, query, (table,))
            elif db_type == "postgresql":
                query = """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """
                return await self._postgresql_query(connection, query, (table,))
            elif db_type == "mysql":
                # Use parameterized query for DESCRIBE with table name validation
                query = "DESCRIBE ?"
                return await self._mysql_query(connection, query, (table,))
            else:
                return ToolResult.error_result(f"Unsupported database type: {db_type}")
        except Exception as e:
            return ToolResult.error_result(f"Schema retrieval failed: {e}")

    async def _list_tables(self, params: dict[str, Any]) -> ToolResult:
        """List all tables in the database."""
        db_type, connection = self._get_connection(params.get("database", "default"))

        try:
            if db_type == "sqlite":
                query = "SELECT name FROM sqlite_master WHERE type='table'"
                return await self._sqlite_query(connection, query)
            elif db_type == "postgresql":
                query = """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """
                return await self._postgresql_query(connection, query)
            elif db_type == "mysql":
                query = "SHOW TABLES"
                return await self._mysql_query(connection, query)
            else:
                return ToolResult.error_result(f"Unsupported database type: {db_type}")
        except Exception as e:
            return ToolResult.error_result(f"Table listing failed: {e}")

    def _get_connection(self, database: str) -> tuple[str, str]:
        """Get database type and connection string.

        Looks for DATABASE_URL env var or specific db config.
        """
        # Check for DATABASE_URL first
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
                return ("postgresql", db_url)
            elif db_url.startswith("mysql://"):
                return ("mysql", db_url)
            elif db_url.startswith("sqlite://") or db_url.startswith("file:"):
                return ("sqlite", db_url.replace("sqlite://", "").replace("file:", ""))

        # Check for specific database env vars
        prefix = f"{database.upper()}_" if database != "default" else ""

        pg_url = os.environ.get(f"{prefix}DATABASE_URL") or os.environ.get("POSTGRES_URL")
        if pg_url:
            return ("postgresql", pg_url)

        mysql_url = os.environ.get(f"{prefix}MYSQL_URL")
        if mysql_url:
            return ("mysql", mysql_url)

        sqlite_path = os.environ.get(f"{prefix}SQLITE_PATH") or os.environ.get("SQLITE_DATABASE")
        if sqlite_path:
            return ("sqlite", sqlite_path)

        # Default to SQLite in current directory
        return ("sqlite", f"{database}.db" if database != "default" else "database.db")

    # SQLite implementations
    async def _sqlite_query(self, connection: str, query: str, params: tuple = ()) -> ToolResult:
        """Execute SQLite query."""
        import sqlite3

        def _run():
            with sqlite3.connect(connection) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
                results = [dict(zip(columns, row)) for row in rows]
                return columns, results

        import asyncio
        columns, results = await asyncio.get_event_loop().run_in_executor(None, _run)

        return ToolResult.success_result(
            f"Query returned {len(results)} rows",
            metadata={"columns": columns, "rows": results},
        )

    async def _sqlite_execute(self, connection: str, query: str) -> ToolResult:
        """Execute SQLite command."""
        import sqlite3

        def _run():
            with sqlite3.connect(connection) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                conn.commit()
                return cursor.rowcount

        import asyncio
        rowcount = await asyncio.get_event_loop().run_in_executor(None, _run)

        return ToolResult.success_result(
            f"Query executed successfully ({rowcount} rows affected)",
            metadata={"rowcount": rowcount},
        )

    # PostgreSQL implementations
    async def _postgresql_query(self, connection: str, query: str, params: tuple = ()) -> ToolResult:
        """Execute PostgreSQL query."""
        try:
            import asyncpg
        except ImportError:
            return ToolResult.error_result(
                "PostgreSQL support requires 'asyncpg'. Install with: pip install asyncpg"
            )

        try:
            conn = await asyncpg.connect(connection)
            try:
                rows = await conn.fetch(query, *params)
                if rows:
                    columns = list(rows[0].keys())
                    results = [dict(row) for row in rows]
                else:
                    columns = []
                    results = []

                return ToolResult.success_result(
                    f"Query returned {len(results)} rows",
                    metadata={"columns": columns, "rows": results},
                )
            finally:
                await conn.close()
        except Exception as e:
            return ToolResult.error_result(f"PostgreSQL error: {e}")

    async def _postgresql_execute(self, connection: str, query: str) -> ToolResult:
        """Execute PostgreSQL command."""
        try:
            import asyncpg
        except ImportError:
            return ToolResult.error_result(
                "PostgreSQL support requires 'asyncpg'. Install with: pip install asyncpg"
            )

        try:
            conn = await asyncpg.connect(connection)
            try:
                result = await conn.execute(query)
                return ToolResult.success_result(
                    f"Query executed successfully: {result}",
                    metadata={"result": result},
                )
            finally:
                await conn.close()
        except Exception as e:
            return ToolResult.error_result(f"PostgreSQL error: {e}")

    # MySQL implementations
    async def _mysql_query(self, connection: str, query: str, params: tuple = ()) -> ToolResult:
        """Execute MySQL query."""
        try:
            import aiomysql
        except ImportError:
            return ToolResult.error_result(
                "MySQL support requires 'aiomysql'. Install with: pip install aiomysql"
            )

        try:
            # Parse connection string (simplified)
            # Expected format: mysql://user:password@host:port/database
            conn_dict = self._parse_mysql_url(connection)

            conn = await aiomysql.connect(**conn_dict)
            try:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    rows = await cur.fetchall()
                    columns = [desc[0] for desc in cur.description] if cur.description else []
                    results = [dict(zip(columns, row)) for row in rows]

                    return ToolResult.success_result(
                        f"Query returned {len(results)} rows",
                        metadata={"columns": columns, "rows": results},
                    )
            finally:
                conn.close()
        except Exception as e:
            return ToolResult.error_result(f"MySQL error: {e}")

    async def _mysql_execute(self, connection: str, query: str) -> ToolResult:
        """Execute MySQL command."""
        try:
            import aiomysql
        except ImportError:
            return ToolResult.error_result(
                "MySQL support requires 'aiomysql'. Install with: pip install aiomysql"
            )

        try:
            conn_dict = self._parse_mysql_url(connection)

            conn = await aiomysql.connect(**conn_dict)
            try:
                async with conn.cursor() as cur:
                    await cur.execute(query)
                    await conn.commit()
                    rowcount = cur.rowcount

                    return ToolResult.success_result(
                        f"Query executed successfully ({rowcount} rows affected)",
                        metadata={"rowcount": rowcount},
                    )
            finally:
                conn.close()
        except Exception as e:
            return ToolResult.error_result(f"MySQL error: {e}")

    def _parse_mysql_url(self, url: str) -> dict[str, Any]:
        """Parse MySQL connection URL into connection parameters."""
        from urllib.parse import urlparse

        parsed = urlparse(url)

        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 3306,
            "user": parsed.username or "root",
            "password": parsed.password or "",
            "db": parsed.path.lstrip("/") if parsed.path else "",
        }
