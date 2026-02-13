"""Shared HTTP client with connection pooling.

Provides a singleton HTTP client for efficient connection reuse across
all HTTP-based tools. Uses httpx with connection pooling and proper
lifecycle management.
"""

import asyncio
import logging
from typing import Final

import httpx

logger = logging.getLogger(__name__)

# Connection pool limits
# These balances performance and resource usage
MAX_CONNECTIONS: Final = 100
MAX_KEEPALIVE_CONNECTIONS: Final = 20
DEFAULT_TIMEOUT: Final = 30.0


class HttpClient:
    """Shared HTTP client with connection pooling.

    Provides a singleton AsyncClient instance configured for optimal
    connection reuse. The client is created on first access and properly
    closed on cleanup.

    Attributes:
        client: The underlying httpx.AsyncClient instance
    """

    _instance: "HttpClient | None" = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self) -> None:
        """Initialize the HTTP client (use get_client() instead)."""
        self._client: httpx.AsyncClient | None = None
        self._initialized: bool = False

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Get the shared HTTP client instance.

        Creates the client on first call with connection pooling configured.
        Subsequent calls return the same client instance.

        Returns:
            Shared httpx.AsyncClient instance

        Example:
            client = await HttpClient.get_client()
            response = await client.get("https://api.example.com")
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()

        if cls._instance._client is None:
            async with cls._lock:
                if cls._instance._client is None:
                    await cls._instance._initialize()

        return cls._instance._client  # type: ignore

    async def _initialize(self) -> None:
        """Initialize the underlying httpx.AsyncClient.

        Configures connection pooling with limits appropriate for
        a CLI tool that may make multiple HTTP requests.
        """
        if self._initialized:
            return

        limits = httpx.Limits(
            max_connections=MAX_CONNECTIONS,
            max_keepalive_connections=MAX_KEEPALIVE_CONNECTIONS,
        )

        timeout = httpx.Timeout(DEFAULT_TIMEOUT)

        self._client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            follow_redirects=True,
        )

        self._initialized = True
        logger.debug(
            f"HTTP client initialized with max_connections={MAX_CONNECTIONS}, "
            f"max_keepalive={MAX_KEEPALIVE_CONNECTIONS}"
        )

    async def close(self) -> None:
        """Close the HTTP client and release resources.

        Should be called during application shutdown. Safe to call
        multiple times.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._initialized = False
            logger.debug("HTTP client closed")

    @classmethod
    async def shutdown(cls) -> None:
        """Shutdown the shared HTTP client.

        Class method for convenient cleanup during application shutdown.
        Safe to call even if client was never initialized.

        Example:
            await HttpClient.shutdown()
        """
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None


async def get_http_client() -> httpx.AsyncClient:
    """Convenience function to get the shared HTTP client.

    This is the preferred way to access the client from tool code.

    Returns:
        Shared httpx.AsyncClient instance

    Example:
        client = await get_http_client()
        response = await client.get("https://api.example.com")
    """
    return await HttpClient.get_client()


async def shutdown_http_client() -> None:
    """Convenience function to shutdown the HTTP client.

    Should be called during application cleanup.

    Example:
        await shutdown_http_client()
    """
    await HttpClient.shutdown()
