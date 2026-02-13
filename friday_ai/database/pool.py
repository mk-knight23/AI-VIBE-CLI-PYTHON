"""Database connection pooling for Friday AI.

Provides production-grade connection pooling with health checks,
timeout handling, and transaction support.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncContextManager

from friday_ai.utils.errors import DatabaseError, ResourceExhaustedError, TimeoutError

logger = logging.getLogger(__name__)


@dataclass
class PoolStats:
    """Connection pool statistics."""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    max_connections: int = 0
    wait_time_ms: float = 0.0
    queries_executed: int = 0
    errors: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "max_connections": self.max_connections,
            "wait_time_ms": round(self.wait_time_ms, 2),
            "queries_executed": self.queries_executed,
            "errors": self.errors,
            "uptime_seconds": round(time.time() - self.created_at, 2),
        }


class ConnectionPool:
    """Generic async connection pool.

    Features:
    - Min/max connection limits
    - Connection timeout
    - Idle timeout
    - Health checks
    - Async context manager support

    Example:
        pool = ConnectionPool(
            connector=asyncpg.connect,
            min_size=2,
            max_size=10,
        )

        async with pool.acquire() as conn:
            result = await conn.fetch("SELECT 1")
    """

    def __init__(
        self,
        connector: Any,
        min_size: int = 2,
        max_size: int = 10,
        connection_timeout: float = 5.0,
        query_timeout: float = 30.0,
        idle_timeout: float = 300.0,
        max_overflow: int = 0,
    ):
        self.connector = connector
        self.min_size = min_size
        self.max_size = max_size
        self.connection_timeout = connection_timeout
        self.query_timeout = query_timeout
        self.idle_timeout = idle_timeout
        self.max_overflow = max_overflow

        self._pool: asyncio.Queue[Any] = asyncio.Queue(maxsize=max_size)
        self._active: set[Any] = set()
        self._overflow: int = 0
        self._semaphore = asyncio.Semaphore(max_size + max_overflow)
        self._stats = PoolStats(max_connections=max_size)
        self._closed = False
        self._health_check_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()  # FIX-006: Lock for thread-safe stats updates

    async def initialize(self) -> None:
        """Initialize the pool with minimum connections."""
        logger.info(f"Initializing connection pool (min={self.min_size}, max={self.max_size})")

        for _ in range(self.min_size):
            try:
                conn = await self._create_connection()
                await self._pool.put(conn)
                async with self._lock:
                    self._stats.total_connections += 1
                    self._stats.idle_connections += 1
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
                raise DatabaseError(
                    f"Failed to initialize connection pool: {e}",
                ) from e

        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info(f"Connection pool initialized with {self.min_size} connections")

    async def _create_connection(self) -> Any:
        """Create a new connection."""
        return await asyncio.wait_for(
            self.connector(),
            timeout=self.connection_timeout,
        )

    async def _health_check_loop(self) -> None:
        """Background task for health checks."""
        while not self._closed:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                if self._closed:
                    break

                # FIX-076: Batch health check using asyncio.gather() to avoid N+1 query pattern
                # Collect all idle connections first
                connections_to_check = []
                while not self._pool.empty():
                    try:
                        conn = self._pool.get_nowait()
                        connections_to_check.append(conn)
                    except asyncio.QueueEmpty:
                        break

                # Check health in parallel using asyncio.gather()
                if connections_to_check:
                    health_results = await asyncio.gather(
                        *[self._is_healthy(conn) for conn in connections_to_check],
                        return_exceptions=True
                    )

                    # Separate healthy from unhealthy connections
                    healthy = []
                    for conn, is_healthy_result in zip(connections_to_check, health_results):
                        # Handle exceptions from health checks
                        if isinstance(is_healthy_result, Exception):
                            logger.debug(f"Health check failed with exception: {is_healthy_result}")
                            is_healthy_result = False

                        if is_healthy_result:
                            healthy.append(conn)
                        else:
                            await self._close_connection(conn)
                            async with self._lock:
                                self._stats.total_connections -= 1
                                self._stats.idle_connections -= 1

                    # Return healthy connections to pool
                    for conn in healthy:
                        await self._pool.put(conn)

                # Replenish to min_size
                while self._stats.total_connections < self.min_size:
                    try:
                        conn = await self._create_connection()
                        await self._pool.put(conn)
                        async with self._lock:
                            self._stats.total_connections += 1
                            self._stats.idle_connections += 1
                    except Exception as e:
                        logger.warning(f"Failed to replenish connection: {e}")
                        break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _is_healthy(self, conn: Any) -> bool:
        """Check if a connection is healthy."""
        try:
            # Try a simple query based on connection type
            if hasattr(conn, "execute"):
                await asyncio.wait_for(
                    conn.execute("SELECT 1"),
                    timeout=5.0,
                )
            return True
        except Exception:
            return False

    async def _close_connection(self, conn: Any) -> None:
        """Close a connection."""
        try:
            if hasattr(conn, "close"):
                await conn.close()
        except Exception as e:
            logger.debug(f"Error closing connection: {e}")

    async def acquire(self) -> AsyncContextManager[Any]:
        """Acquire a connection from the pool.

        Returns:
            Connection context manager
        """
        if self._closed:
            raise DatabaseError("Pool is closed")

        start_wait = time.time()

        # FIX-026: Try to acquire from pool without blocking
        # Check pool emptiness and get connection atomically
        try:
            conn = self._pool.get_nowait()
            async with self._lock:
                self._stats.idle_connections -= 1
                self._stats.wait_time_ms += (time.time() - start_wait) * 1000
            return ConnectionContext(self, conn)
        except asyncio.QueueEmpty:
            pass  # Pool is empty, continue to semaphore

        # Wait for semaphore with timeout
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.connection_timeout
            )
        except asyncio.TimeoutError:
            raise ResourceExhaustedError(
                "Connection pool exhausted",
                resource_type="database_connections",
                current_usage=self._stats.active_connections,
                limit=self.max_size + self.max_overflow,
            )

        try:
            # Try pool again after acquiring semaphore
            try:
                conn = self._pool.get_nowait()
                async with self._lock:
                    self._stats.idle_connections -= 1
                    self._stats.wait_time_ms += (time.time() - start_wait) * 1000
                return ConnectionContext(self, conn)
            except asyncio.QueueEmpty:
                # Create new connection
                conn = await self._create_connection()
                async with self._lock:
                    self._stats.total_connections += 1
                    self._stats.idle_connections -= 1
                    self._stats.wait_time_ms += (time.time() - start_wait) * 1000
                return ConnectionContext(self, conn)

        except Exception:
            self._semaphore.release()
            raise

    async def release(self, conn: Any) -> None:
        """Release a connection back to the pool."""
        if self._closed:
            await self._close_connection(conn)
            return

        async with self._lock:
            if await self._is_healthy(conn):
                await self._pool.put(conn)
                self._stats.idle_connections += 1
            else:
                await self._close_connection(conn)
                self._stats.total_connections -= 1

        self._semaphore.release()

    async def execute(self, query: str, params: tuple = (), timeout: float | None = None) -> Any:
        """Execute a query using a pooled connection.

        Args:
            query: SQL query to execute
            params: Query parameters
            timeout: Query timeout (uses default if None)

        Returns:
            Query result
        """
        async with self.acquire() as conn:
            try:
                exec_timeout = timeout or self.query_timeout
                start = time.time()

                if hasattr(conn, "fetch"):
                    # asyncpg style
                    result = await asyncio.wait_for(
                        conn.fetch(query, *params),
                        timeout=exec_timeout,
                    )
                elif hasattr(conn, "execute"):
                    # Generic execute
                    result = await asyncio.wait_for(
                        conn.execute(query, params),
                        timeout=exec_timeout,
                    )
                else:
                    raise DatabaseError("Connection does not support execute/fetch")

                # FIX-026: Protect stats update with lock
                async with self._lock:
                    self._stats.queries_executed += 1
                return result

            except asyncio.TimeoutError as e:
                async with self._lock:
                    self._stats.errors += 1
                raise TimeoutError(
                    f"Query timed out after {exec_timeout}s",
                    operation="database_query",
                    timeout=exec_timeout,
                ) from e

            except Exception as e:
                async with self._lock:
                    self._stats.errors += 1
                raise DatabaseError(
                    f"Query execution failed: {e}",
                    query=query,
                ) from e

    async def close(self) -> None:
        """Close all connections and shutdown the pool."""
        self._closed = True

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections in pool
        while not self._pool.empty():
            try:
                conn = await self._pool.get()
                await self._close_connection(conn)
            except Exception as e:
                logger.debug(f"Error closing pooled connection: {e}")

        # Close active connections
        for conn in list(self._active):
            await self._close_connection(conn)

        logger.info("Connection pool closed")

    def get_stats(self) -> PoolStats:
        """Get pool statistics.

        Returns a snapshot of current pool statistics. The active_connections
        count is calculated from the current _active set.
        """
        # Create a copy to avoid race conditions with concurrent updates
        stats_snapshot = PoolStats(
            total_connections=self._stats.total_connections,
            active_connections=len(self._active),
            idle_connections=self._stats.idle_connections,
            max_connections=self._stats.max_connections,
            wait_time_ms=self._stats.wait_time_ms,
            queries_executed=self._stats.queries_executed,
            errors=self._stats.errors,
            created_at=self._stats.created_at,
        )
        return stats_snapshot


class ConnectionContext:
    """Async context manager for pooled connections."""

    def __init__(self, pool: ConnectionPool, conn: Any):
        self.pool = pool
        self.conn = conn

    async def __aenter__(self) -> Any:
        self.pool._active.add(self.conn)
        return self.conn

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.pool._active.discard(self.conn)
        await self.pool.release(self.conn)


class DatabaseConnectionPool:
    """High-level database connection pool with backend support.

    Supports PostgreSQL, MySQL, and SQLite backends.

    Example:
        pool = DatabaseConnectionPool(
            backend="postgresql",
            host="localhost",
            database="mydb",
            user="user",
            password="pass",
        )

        await pool.initialize()

        async with pool.transaction() as txn:
            result = await txn.execute("SELECT * FROM users")
    """

    SUPPORTED_BACKENDS = {"postgresql", "mysql", "sqlite"}

    def __init__(
        self,
        backend: str,
        host: str = "localhost",
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        min_connections: int = 2,
        max_connections: int = 10,
        connection_timeout: float = 5.0,
        query_timeout: float = 30.0,
    ):
        if backend not in self.SUPPORTED_BACKENDS:
            raise ValueError(f"Unsupported backend: {backend}. Use: {self.SUPPORTED_BACKENDS}")

        self.backend = backend
        self.host = host
        self.port = port or self._default_port(backend)
        self.database = database
        self.user = user
        self.password = password

        self._pool: ConnectionPool | None = None
        self._config = {
            "min_size": min_connections,
            "max_size": max_connections,
            "connection_timeout": connection_timeout,
            "query_timeout": query_timeout,
        }

    def _default_port(self, backend: str) -> int:
        """Get default port for backend."""
        ports = {
            "postgresql": 5432,
            "mysql": 3306,
            "sqlite": 0,  # N/A for SQLite
        }
        return ports.get(backend, 0)

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        connector = self._create_connector()

        self._pool = ConnectionPool(
            connector=connector,
            **self._config,
        )

        await self._pool.initialize()

    def _create_connector(self) -> Any:
        """Create connection function for the backend."""
        if self.backend == "postgresql":
            try:
                import asyncpg
            except ImportError:
                raise DatabaseError("asyncpg not installed. Run: pip install asyncpg")

            return lambda: asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )

        elif self.backend == "mysql":
            try:
                import aiomysql
            except ImportError:
                raise DatabaseError("aiomysql not installed. Run: pip install aiomysql")

            return lambda: aiomysql.connect(
                host=self.host,
                port=self.port,
                db=self.database,
                user=self.user,
                password=self.password,
            )

        elif self.backend == "sqlite":
            try:
                import aiosqlite
            except ImportError:
                raise DatabaseError("aiosqlite not installed. Run: pip install aiosqlite")

            db_path = self.database or ":memory:"
            return lambda: aiosqlite.connect(db_path)

        raise DatabaseError(f"Unsupported backend: {self.backend}")

    async def execute(self, query: str, params: tuple = (), timeout: float | None = None) -> Any:
        """Execute a query."""
        if not self._pool:
            raise DatabaseError("Pool not initialized. Call initialize() first.")
        return await self._pool.execute(query, params, timeout)

    async def fetch(self, query: str, params: tuple = (), timeout: float | None = None) -> list[dict]:
        """Fetch results from a query."""
        result = await self.execute(query, params, timeout)

        # Convert to list of dicts
        if isinstance(result, list):
            return [dict(row) for row in result]
        return []

    def transaction(self) -> TransactionContext:
        """Get a transaction context manager."""
        if not self._pool:
            raise DatabaseError("Pool not initialized")
        return TransactionContext(self._pool)

    def get_pool_stats(self) -> PoolStats:
        """Get pool statistics."""
        if not self._pool:
            return PoolStats()
        return self._pool.get_stats()

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            await self.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the pool."""
        if self._pool:
            await self._pool.close()


class TransactionContext:
    """Async context manager for database transactions."""

    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.conn: Any = None
        self._acquired = False

    async def __aenter__(self) -> TransactionContext:
        context = await self.pool.acquire()
        self.conn = await context.__aenter__()
        self._acquired = True

        # Start transaction
        if hasattr(self.conn, "execute"):
            await self.conn.execute("BEGIN")

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if not self._acquired:
            return

        try:
            if exc_type is None:
                # Commit on success
                if hasattr(self.conn, "execute"):
                    await self.conn.execute("COMMIT")
            else:
                # Rollback on error
                if hasattr(self.conn, "execute"):
                    await self.conn.execute("ROLLBACK")
        finally:
            # Release connection
            context = ConnectionContext(self.pool, self.conn)
            await context.__aexit__(exc_type, exc_val, exc_tb)
