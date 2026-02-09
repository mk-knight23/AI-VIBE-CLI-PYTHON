"""FastAPI server factory and application setup."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from friday_ai.api.routers import health, runs, sessions, tools
from friday_ai.auth.api_keys import APIKeyManager
from friday_ai.config.config import Config
from friday_ai.database.memory_backend import MemorySessionBackend
from friday_ai.database.redis_backend import RedisSessionBackend
from friday_ai.ratelimit.middleware import RateLimiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager (startup/shutdown).

    Initializes all shared resources on startup and cleans up on shutdown.
    Falls back to memory backend if Redis is unavailable.
    """
    config = Config()

    # Try Redis first, fall back to memory
    redis_url = config.redis_url or "redis://localhost:6379"
    redis_available = False

    try:
        redis_backend = RedisSessionBackend(redis_url=redis_url)
        await redis_backend.connect()
        await redis_backend.ping()
        app.state.redis_backend = redis_backend
        redis_available = True
        logger.info("Connected to Redis")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}), using in-memory backend")
        memory_backend = MemorySessionBackend()
        await memory_backend.connect()
        app.state.redis_backend = memory_backend

    # Initialize rate limiter (fails open if Redis unavailable)
    rate_limiter = RateLimiter(redis_url=redis_url)
    try:
        await rate_limiter.connect()
        await rate_limiter._redis.ping()
        app.state.rate_limiter = rate_limiter
        logger.info("Rate limiter connected to Redis")
    except Exception as e:
        logger.warning(f"Rate limiter Redis unavailable ({e}), requests will not be rate limited")
        # Create a no-op rate limiter
        app.state.rate_limiter = RateLimiter(redis_url="")
        app.state.rate_limiter._redis = None

    # Initialize API key manager
    app.state.api_key_manager = APIKeyManager(
        redis_backend=app.state.redis_backend
    )

    yield

    # Cleanup
    try:
        await app.state.rate_limiter.close()
    except Exception:
        pass
    try:
        await app.state.redis_backend.close()
    except Exception:
        pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Friday AI API",
        description="Enterprise AI coding assistant API",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(
        sessions.router,
        prefix="/api/v2/sessions",
        tags=["sessions"],
    )
    app.include_router(
        tools.router,
        prefix="/api/v2/tools",
        tags=["tools"],
    )
    app.include_router(
        runs.router,
        prefix="/api/v2/runs",
        tags=["runs"],
    )

    # Exception handlers
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        logger.exception("Unhandled exception")
        error_msg = str(exc) if app.debug else "An unexpected error occurred"
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": error_msg,
                },
            },
        )

    return app
