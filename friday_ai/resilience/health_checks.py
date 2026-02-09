"""Health check system for Friday AI.

Provides Kubernetes-style health checks for monitoring
system health and dependencies.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    last_check: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "last_check": self.last_check,
            "metadata": self.metadata,
        }


@dataclass
class DependencyHealth:
    """Health status of a dependency."""

    name: str
    status: HealthStatus
    required: bool = True
    check_interval: float = 30.0
    timeout: float = 5.0
    last_check: float = field(default_factory=float)
    result: HealthCheckResult | None = None


HealthCheckFn = Callable[[], Awaitable[HealthCheckResult]]


class HealthCheckSystem:
    """Kubernetes-style health check system.

    Provides liveness, readiness, and dependency health checks
    for monitoring and orchestration.

    Example:
        health = HealthCheckSystem()

        # Register custom health check
        @health.check("database")
        async def check_database():
            await db.ping()
            return HealthCheckResult("database", HealthStatus.HEALTHY)

        # Get health status
        status = await health.liveness_check()
        readiness = await health.readiness_check()
    """

    def __init__(
        self,
        check_interval: float = 30.0,
        timeout: float = 5.0,
    ):
        self.check_interval = check_interval
        self.timeout = timeout
        self._checks: dict[str, HealthCheckFn] = {}
        self._dependencies: dict[str, DependencyHealth] = {}
        self._cache: dict[str, HealthCheckResult] = {}
        self._last_check: dict[str, float] = {}

    def check(self, name: str) -> Callable[[HealthCheckFn], HealthCheckFn]:
        """Decorator to register a health check.

        Args:
            name: Name of the health check

        Returns:
            Decorator function
        """
        def decorator(fn: HealthCheckFn) -> HealthCheckFn:
            self._checks[name] = fn
            return fn
        return decorator

    def register_dependency(
        self,
        name: str,
        check_fn: HealthCheckFn,
        required: bool = True,
        check_interval: float | None = None,
        timeout: float | None = None,
    ) -> None:
        """Register a dependency health check.

        Args:
            name: Dependency name
            check_fn: Async function that returns HealthCheckResult
            required: Whether this dependency is required for readiness
            check_interval: How often to check (uses default if None)
            timeout: Check timeout (uses default if None)
        """
        self._checks[name] = check_fn
        self._dependencies[name] = DependencyHealth(
            name=name,
            status=HealthStatus.UNKNOWN,
            required=required,
            check_interval=check_interval or self.check_interval,
            timeout=timeout or self.timeout,
        )

    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a single health check.

        Args:
            name: Name of the check to run

        Returns:
            HealthCheckResult
        """
        if name not in self._checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not registered",
            )

        # Check cache
        now = time.time()
        if name in self._last_check:
            elapsed = now - self._last_check[name]
            if elapsed < self.check_interval and name in self._cache:
                return self._cache[name]

        check_fn = self._checks[name]
        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                check_fn(),
                timeout=self.timeout,
            )
            result.latency_ms = (time.time() - start_time) * 1000

        except asyncio.TimeoutError:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                latency_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {type(e).__name__}: {e}",
                latency_ms=(time.time() - start_time) * 1000,
            )

        # Cache result
        self._cache[name] = result
        self._last_check[name] = now

        # Update dependency status if applicable
        if name in self._dependencies:
            self._dependencies[name].status = result.status
            self._dependencies[name].last_check = now
            self._dependencies[name].result = result

        return result

    async def liveness_check(self) -> HealthCheckResult:
        """Check if the application is alive.

        Liveness checks should be lightweight and only detect
        if the process is running and responsive.

        Returns:
            HealthCheckResult
        """
        return HealthCheckResult(
            name="liveness",
            status=HealthStatus.HEALTHY,
            message="Application is alive",
        )

    async def readiness_check(self) -> HealthCheckResult:
        """Check if the application is ready to accept traffic.

        Readiness checks should verify all dependencies are available.

        Returns:
            HealthCheckResult
        """
        if not self._dependencies:
            return HealthCheckResult(
                name="readiness",
                status=HealthStatus.HEALTHY,
                message="No dependencies configured",
            )

        unhealthy_deps = []
        degraded_deps = []

        for name, dep in self._dependencies.items():
            result = await self.run_check(name)

            if result.status == HealthStatus.UNHEALTHY:
                if dep.required:
                    unhealthy_deps.append(name)
                else:
                    degraded_deps.append(name)
            elif result.status == HealthStatus.DEGRADED:
                degraded_deps.append(name)

        if unhealthy_deps:
            return HealthCheckResult(
                name="readiness",
                status=HealthStatus.UNHEALTHY,
                message=f"Required dependencies unhealthy: {', '.join(unhealthy_deps)}",
                metadata={
                    "unhealthy": unhealthy_deps,
                    "degraded": degraded_deps,
                },
            )

        if degraded_deps:
            return HealthCheckResult(
                name="readiness",
                status=HealthStatus.DEGRADED,
                message=f"Some dependencies degraded: {', '.join(degraded_deps)}",
                metadata={"degraded": degraded_deps},
            )

        return HealthCheckResult(
            name="readiness",
            status=HealthStatus.HEALTHY,
            message="All dependencies healthy",
        )

    async def dependency_check(self, name: str) -> HealthCheckResult:
        """Check health of a specific dependency.

        Args:
            name: Dependency name

        Returns:
            HealthCheckResult
        """
        if name not in self._checks and name not in self._dependencies:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Dependency '{name}' not registered",
            )

        return await self.run_check(name)

    async def run_all_checks(self) -> dict[str, HealthCheckResult]:
        """Run all registered health checks.

        Returns:
            Dictionary of check results by name
        """
        results = {}
        results["liveness"] = await self.liveness_check()
        results["readiness"] = await self.readiness_check()

        for name in self._checks:
            if name not in results:
                results[name] = await self.run_check(name)

        return results

    def get_health_endpoint(self) -> str:
        """Get health endpoint path."""
        return "/health"

    def get_ready_endpoint(self) -> str:
        """Get readiness endpoint path."""
        return "/ready"

    def get_live_endpoint(self) -> str:
        """Get liveness endpoint path."""
        return "/live"

    def to_dict(self) -> dict[str, Any]:
        """Convert health status to dictionary."""
        return {
            "checks": {
                name: result.to_dict() if result else None
                for name, result in self._cache.items()
            },
            "dependencies": {
                name: {
                    "status": dep.status.value,
                    "required": dep.required,
                    "last_check": dep.last_check,
                }
                for name, dep in self._dependencies.items()
            },
        }
