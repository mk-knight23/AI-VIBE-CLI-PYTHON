"""Metrics collection for Friday AI.

Provides Prometheus-compatible metrics collection with
support for counters, gauges, histograms, and timers.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """A single metric value with tags."""

    name: str
    type: MetricType
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class HistogramBucket:
    """Histogram bucket for distribution metrics."""

    upper_bound: float
    count: int = 0


class Histogram:
    """Histogram metric for tracking distributions."""

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

    def __init__(self, buckets: list[float] | None = None):
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self.bucket_counts: dict[float, int] = {b: 0 for b in self.buckets}
        self.sum_value: float = 0.0
        self.count: int = 0

    def observe(self, value: float) -> None:
        """Observe a value."""
        self.sum_value += value
        self.count += 1

        for bucket in self.buckets:
            if value <= bucket:
                self.bucket_counts[bucket] += 1

    def get_quantile(self, q: float) -> float:
        """Calculate approximate quantile."""
        if self.count == 0:
            return 0.0

        target = int(self.count * q)
        cumulative = 0

        for bucket in self.buckets:
            cumulative += self.bucket_counts[bucket]
            if cumulative >= target:
                return bucket

        return self.buckets[-1] if self.buckets else 0.0


class MetricsCollector:
    """Prometheus-compatible metrics collector.

    Features:
    - Counter: Monotonically increasing values
    - Gauge: Values that can go up or down
    - Histogram: Distribution of values
    - Labels/tags for dimensionality
    - Export to Prometheus format
    - Export to JSON

    Example:
        metrics = MetricsCollector()

        # Counter
        metrics.counter("tool_executions", 1, {"tool": "shell"})

        # Gauge
        metrics.gauge("active_sessions", 5)

        # Histogram
        metrics.histogram("tool_latency", 0.5, {"tool": "shell"})

        # Timer context manager
        with metrics.timer("operation_duration"):
            do_something()

        # Export
        print(metrics.export_prometheus())
    """

    def __init__(self):
        self._counters: dict[str, dict[frozenset, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: dict[str, dict[frozenset, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: dict[str, dict[frozenset, Histogram]] = defaultdict(dict)
        self._timestamps: dict[str, float] = {}

    def _make_key(self, tags: dict[str, str]) -> frozenset:
        """Create hashable key from tags."""
        return frozenset(tags.items()) if tags else frozenset()

    def counter(self, name: str, value: float = 1, tags: dict[str, str] | None = None) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name
            value: Value to add (default 1)
            tags: Optional tags/labels
        """
        key = self._make_key(tags or {})
        self._counters[name][key] += value
        self._timestamps[name] = time.time()

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Set a gauge metric.

        Args:
            name: Metric name
            value: Value to set
            tags: Optional tags/labels
        """
        key = self._make_key(tags or {})
        self._gauges[name][key] = value
        self._timestamps[name] = time.time()

    def gauge_inc(self, name: str, value: float = 1, tags: dict[str, str] | None = None) -> None:
        """Increment a gauge metric.

        Args:
            name: Metric name
            value: Value to add (default 1)
            tags: Optional tags/labels
        """
        key = self._make_key(tags or {})
        self._gauges[name][key] += value
        self._timestamps[name] = time.time()

    def gauge_dec(self, name: str, value: float = 1, tags: dict[str, str] | None = None) -> None:
        """Decrement a gauge metric.

        Args:
            name: Metric name
            value: Value to subtract (default 1)
            tags: Optional tags/labels
        """
        key = self._make_key(tags or {})
        self._gauges[name][key] -= value
        self._timestamps[name] = time.time()

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Observe a value in a histogram.

        Args:
            name: Metric name
            value: Value to observe
            tags: Optional tags/labels
        """
        key = self._make_key(tags or {})

        if key not in self._histograms[name]:
            self._histograms[name][key] = Histogram()

        self._histograms[name][key].observe(value)
        self._timestamps[name] = time.time()

    def timing(self, name: str, duration_ms: float, tags: dict[str, str] | None = None) -> None:
        """Record a timing in milliseconds.

        Args:
            name: Metric name
            duration_ms: Duration in milliseconds
            tags: Optional tags/labels
        """
        self.histogram(f"{name}_seconds", duration_ms / 1000.0, tags)

    def timer(self, name: str, tags: dict[str, str] | None = None):
        """Context manager for timing operations.

        Args:
            name: Metric name
            tags: Optional tags/labels

        Returns:
            Timer context manager
        """
        return Timer(self, name, tags)

    def get_counter(self, name: str, tags: dict[str, str] | None = None) -> float:
        """Get counter value."""
        key = self._make_key(tags or {})
        return self._counters[name].get(key, 0.0)

    def get_gauge(self, name: str, tags: dict[str, str] | None = None) -> float:
        """Get gauge value."""
        key = self._make_key(tags or {})
        return self._gauges[name].get(key, 0.0)

    def get_histogram_stats(self, name: str, tags: dict[str, str] | None = None) -> dict[str, float] | None:
        """Get histogram statistics."""
        key = self._make_key(tags or {})
        hist = self._histograms[name].get(key)

        if not hist:
            return None

        return {
            "count": hist.count,
            "sum": hist.sum_value,
            "avg": hist.sum_value / hist.count if hist.count > 0 else 0,
            "p50": hist.get_quantile(0.5),
            "p95": hist.get_quantile(0.95),
            "p99": hist.get_quantile(0.99),
        }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []

        # Counters
        for name, tag_values in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            for tags, value in tag_values.items():
                tag_str = self._format_tags(dict(tags))
                lines.append(f"{name}{tag_str} {value}")

        # Gauges
        for name, tag_values in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            for tags, value in tag_values.items():
                tag_str = self._format_tags(dict(tags))
                lines.append(f"{name}{tag_str} {value}")

        # Histograms
        for name, tag_hists in self._histograms.items():
            lines.append(f"# TYPE {name} histogram")
            for tags, hist in tag_hists.items():
                tag_dict = dict(tags)
                for bucket, count in hist.bucket_counts.items():
                    tag_dict["le"] = str(bucket)
                    tag_str = self._format_tags(tag_dict)
                    lines.append(f"{name}_bucket{tag_str} {count}")
                # +Inf bucket
                tag_dict["le"] = "+Inf"
                tag_str = self._format_tags(tag_dict)
                lines.append(f"{name}_bucket{tag_str} {hist.count}")
                # Sum and count
                tag_str = self._format_tags(dict(tags))
                lines.append(f"{name}_sum{tag_str} {hist.sum_value}")
                lines.append(f"{name}_count{tag_str} {hist.count}")

        return "\n".join(lines)

    def export_json(self) -> dict[str, Any]:
        """Export metrics as JSON.

        Returns:
            Dictionary with all metrics
        """
        result = {
            "counters": {},
            "gauges": {},
            "histograms": {},
        }

        for name, tag_values in self._counters.items():
            result["counters"][name] = {
                dict(tags).__repr__(): value for tags, value in tag_values.items()
            }

        for name, tag_values in self._gauges.items():
            result["gauges"][name] = {
                dict(tags).__repr__(): value for tags, value in tag_values.items()
            }

        for name, tag_hists in self._histograms.items():
            result["histograms"][name] = {
                dict(tags).__repr__(): self.get_histogram_stats(name, dict(tags))
                for tags in tag_hists.keys()
            }

        return result

    def _format_tags(self, tags: dict[str, str]) -> str:
        """Format tags for Prometheus output."""
        if not tags:
            return ""
        tag_parts = [f'{k}="{v}"' for k, v in sorted(tags.items())]
        return "{" + ",".join(tag_parts) + "}"

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timestamps.clear()


class Timer:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, name: str, tags: dict[str, str] | None = None):
        self.collector = collector
        self.name = name
        self.tags = tags or {}
        self.start_time: float | None = None
        self.duration_ms: float = 0.0

    def __enter__(self) -> Timer:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is not None:
            self.duration_ms = (time.perf_counter() - self.start_time) * 1000
            self.collector.timing(self.name, self.duration_ms, self.tags)

    async def __aenter__(self) -> Timer:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)
