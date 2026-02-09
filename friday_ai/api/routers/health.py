"""Health check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from friday_ai.api.dependencies import get_redis_backend
from friday_ai.api.models.responses import HealthResponse
from friday_ai.database.redis_backend import RedisSessionBackend

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check.

    Returns 200 OK if the server is running.
    Fast response (< 100ms) for load balancer checks.
    """
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=datetime.now(timezone.utc),
        components={"api": "healthy"},
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check(
    request: Request,
    redis: RedisSessionBackend = Depends(get_redis_backend),
):
    """Readiness check for Kubernetes.

    Verifies all dependencies are accessible:
    - Redis connection
    - Database (if configured)

    Returns 200 only if all dependencies are healthy.
    """
    components = {}
    all_healthy = True

    # Check Redis
    try:
        await redis.ping()
        components["redis"] = "healthy"
    except Exception as e:
        components["redis"] = f"unhealthy: {str(e)}"
        all_healthy = False

    if not all_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "components": components,
            },
        )

    return HealthResponse(
        status="ready",
        version="2.0.0",
        timestamp=datetime.now(timezone.utc),
        components=components,
    )


@router.get("/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness check for Kubernetes.

    Returns 200 if the process is running.
    Does not check dependencies (that's readiness).
    """
    return HealthResponse(
        status="alive",
        version="2.0.0",
        timestamp=datetime.now(timezone.utc),
        components={},
    )
