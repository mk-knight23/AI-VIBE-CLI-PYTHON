"""Observability package for Friday AI.

Provides metrics collection, distributed tracing, and structured logging
for production monitoring and debugging.
"""

from friday_ai.observability.metrics import MetricsCollector, MetricType

__all__ = [
    "MetricsCollector",
    "MetricType",
]
