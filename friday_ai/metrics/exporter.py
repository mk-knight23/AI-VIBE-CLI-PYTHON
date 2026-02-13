"""Metrics exporter for Friday AI.

Collects and exports metrics in Prometheus format.
"""

import logging
import time
import threading
from collections import defaultdict
from typing import Any, Dict, Optional
from enum import Enum

from friday_ai.config.config import Config

logger = logging.getLogger(__name__)


class MetricKind(Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class Metric:
    """Individual metric tracking object."""

    def __init__(self, name: str, kind: MetricKind, description: str):
        """Initialize metric.

        Args:
            name: Metric name
            kind: Metric kind (counter, gauge, histogram)
            description: Metric description
        """
        self.name = name
        self.kind = kind
        self.description = description
        self._count = 0
        self._sum = 0.0
        self._min = float("inf")
        self._max = 0.0
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0) -> None:
        """Increment counter metric."""
        with self._lock:
            self._count += 1
            self._sum += amount

    def set(self, value: float) -> None:
        """Set gauge metric value."""
        with self._lock:
            self._sum = value
            self._max = max(self._max, value)
            self._min = min(self._min, value)

    def observe(self, value: float) -> None:
        """Observe value for histogram/summary."""
        with self._lock:
            self._count += 1
            self._sum += value
            self._max = max(self._max, value)
            self._min = min(self._min, value)

    def get_stats(self) -> Dict[str, Any]:
        """Get metric statistics."""
        with self._lock:
            return {
                "count": self._count,
                "sum": self._sum,
                "min": 0.0 if self._min == float("inf") else self._min,
                "max": self._max,
                "average": self._sum / self._count if self._count else 0.0,
            }


class MetricsCollector:
    """Collects and manages metrics for Friday operations."""

    def __init__(self, config: Config):
        """Initialize metrics collector.

        Args:
            config: Configuration
        """
        self.config = config
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()
        self._start_time = time.time()

    def counter(self, name: str, description: str) -> Metric:
        """Create or get counter metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Metric(name, MetricKind.COUNTER, description)
            return self._metrics[name]

    def gauge(self, name: str, description: str) -> Metric:
        """Create or get gauge metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Metric(name, MetricKind.GAUGE, description)
            return self._metrics[name]

    def histogram(self, name: str, description: str) -> Metric:
        """Create or get histogram metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Metric(name, MetricKind.HISTOGRAM, description)
            return self._metrics[name]

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        lines = []
        with self._lock:
            for name, metric in self._metrics.items():
                lines.append(f"# HELP {name} {metric.description}")
                lines.append(f"# TYPE {name} {metric.kind.value}")

                stats = metric.get_stats()
                if metric.kind == MetricKind.GAUGE:
                    lines.append(f"{name} {stats['sum']}")
                else:
                    lines.append(f"{name}_count {stats['count']}")
                    lines.append(f"{name}_sum {stats['sum']}")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._start_time = time.time()
