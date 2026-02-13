"""Dependency injection for FastAPI.

Provides dependencies for authentication, rate limiting, database access,
and other cross-cutting concerns.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from friday_ai.auth.api_keys import APIKeyManager
from friday_ai.ratelimit.middleware import RateLimiter
from friday_ai.utils.errors import AuthenticationError, RateLimitError

# Security scheme for API key auth
security = HTTPBearer(auto_error=False)


class User:
    """Authenticated user context."""

    def __init__(self, user_id: str, api_key: str, tier: str = "free"):
        self.id = user_id
        self.api_key = api_key
        self.tier = tier


async def get_api_key_manager(request: Request) -> APIKeyManager:
    """Get API key manager from app state."""
    if not hasattr(request.app.state, 'api_key_manager'):
        from friday_ai.utils.errors import DependencyError
        raise DependencyError(
            message="API not fully initialized",
            dependency="api_key_manager",
        )
    return request.app.state.api_key_manager


async def get_redis_backend(request: Request):
    """Get session backend from app state."""
    if not hasattr(request.app.state, 'redis_backend'):
        from friday_ai.utils.errors import DependencyError
        raise DependencyError(
            message="API not fully initialized",
            dependency="redis_backend",
        )
    return request.app.state.redis_backend


async def get_rate_limiter(request: Request) -> RateLimiter:
    """Get rate limiter from app state."""
    if not hasattr(request.app.state, 'rate_limiter'):
        from friday_ai.utils.errors import DependencyError
        raise DependencyError(
            message="API not fully initialized",
            dependency="rate_limiter",
        )
    return request.app.state.rate_limiter


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    key_manager: APIKeyManager = Depends(get_api_key_manager),
) -> User:
    """Validate API key and return user context.

    Args:
        credentials: Bearer token from Authorization header
        key_manager: API key manager for validation

    Returns:
        User context for the authenticated user

    Raises:
        AuthenticationError: If authentication fails
    """
    if not credentials:
        raise AuthenticationError(
            message="Missing Authorization header",
        )

    api_key = credentials.credentials

    # Validate key
    key_info = await key_manager.validate_key(api_key)
    if not key_info:
        raise AuthenticationError(
            message="Invalid or revoked API key",
        )

    return User(
        user_id=key_info["user_id"],
        api_key=api_key,
        tier=key_info.get("tier", "free"),
    )


async def check_rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    """Check rate limit for the current request.

    Args:
        request: FastAPI request object
        user: Authenticated user
        limiter: Rate limiter instance

    Raises:
        RateLimitError: If rate limit exceeded
    """
    # Different limits per tier
    limits = {
        "free": (100, 60),      # 100 requests per minute
        "pro": (1000, 60),      # 1000 requests per minute
        "enterprise": (10000, 60),  # 10000 requests per minute
    }

    max_requests, window = limits.get(user.tier, limits["free"])

    # Create key based on user and endpoint
    key = f"ratelimit:{user.id}:{request.url.path}"

    is_allowed, retry_after = await limiter.is_allowed(key, max_requests, window)

    if not is_allowed:
        raise RateLimitError(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            limit=max_requests,
            reset_after=retry_after,
        )


# Compose auth + rate limiting
AuthWithRateLimit = Depends(get_current_user), Depends(check_rate_limit)
