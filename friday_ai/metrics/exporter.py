"""Metrics exporter for Friday AI.

Collects and exports metrics in Prometheus format.
"""

import logging
import time
from collections import defaultdict
from typing import Any, Callable
from datetime import datetime, timedelta

from friday_ai.config.config import Config

logger = logging.getLogger(__name__)


class MetricType:
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"

    def __init__(self, name: str, metric_type: str, description: str):
        """Initialize metric.

        Args:
            name: Metric name (e.g., "tool_executions")
            metric_type: Counter, gauge, histogram
            description: Human-readable description
        """
        self.name = name
        self.type = metric_type
        self.description = description
        self._value = 0
        self._count = 0
        self._sum = 0
        self._min = float('inf')
        self._max = 0
        self._buckets: dict[int, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    def inc(self) -> None:
        """Increment counter."""
        with self._lock:
            self._count += 1
            self._sum += 1

    def set(self, value: float) -> None:
        """Set gauge value."""
        self._value = value
        if value > self._max:
            self._max = value
        elif value < self._min:
            self._min = value

    def observe(self, value: float) -> None:
        """Observe value for histogram."""
        if value < self._min:
            self._min = value
        if value > self._max:
            self._max = value
        bucket_index = int(value / 10)
        self._buckets[bucket_index] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get metric statistics.

        Returns:
            Dictionary with metric statistics
        """
        return {
            "count": self._count,
            "sum": self._sum,
            "min": self._min,
            "max": self._max,
            "average": self._sum / self._count if self._count else 0,
        }


class MetricsCollector:
    """Collects and manages metrics for Friday operations."""

    def __init__(self, config: Config):
        """Initialize metrics collector.

        Args:
            config: Configuration
        """
        self.config = config
        self.metrics = defaultdict(lambda: MetricType: dict[str, MetricType])
        self._start_time = time.time()
        self._lock = asyncio.Lock()

    def counter(self, name: str, description: str) -> MetricType.COUNTER:
        """Create or get counter metric.

        Args:
            name: Metric name
            description: Metric description

        Returns:
            Counter metric
        """
        metric = MetricType.COUNTER(name, description)
        self.metrics[metric_type][name] = metric
        return metric

    def gauge(self, name: str, description: str) -> MetricType.GAUGE:
        """Create or get gauge metric.

        Args:
            name: Metric name
            description: Metric description

        Returns:
            Gauge metric
        """
        metric = MetricType.GAUGE(name, description)
        self.metrics[metric_type][name] = metric
        return metric

    def histogram(self, name: str, description: str, buckets: int = 10) -> MetricType.HISTOGRAM:
        """Create or get histogram metric.

        Args:
            name: Metric name
            description: Metric description
            buckets: Number of histogram buckets

        Returns:
            Histogram metric
        """
        metric = MetricType.HISTOGRAM(name, description, buckets=buckets)
        self.metrics[metric_type][name] = metric
        return metric

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus format.

        Returns:
            Prometheus text format
        """
        lines = []

        for metric_type, metrics in self.metrics.items():
            for name, metric in metrics.items():
                if metric.type == MetricType.COUNTER:
                    lines.append(
                        f"{metric.get_stats().get('count', 0)}"
                    )
                elif metric.type == MetricType.GAUGE:
                    lines.append(
                        f"{metric.get_stats().get('sum', 0)}"
                    )
                elif metric.type == MetricType.HISTOGRAM:
                    lines.append(
                        f"{metric.get_stats().get('count', 0)}"
                    )

        return '\n'.join(lines)

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self._start_time = time.time()
