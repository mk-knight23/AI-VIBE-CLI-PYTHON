"""Database package for Friday AI.

Provides connection pooling, transaction management, and health checks
for production database operations.
"""

from friday_ai.database.memory_backend import MemorySessionBackend
from friday_ai.database.pool import ConnectionPool, DatabaseConnectionPool, PoolStats
from friday_ai.database.redis_backend import RedisSessionBackend

__all__ = [
    "ConnectionPool",
    "DatabaseConnectionPool",
    "MemorySessionBackend",
    "PoolStats",
    "RedisSessionBackend",
]
