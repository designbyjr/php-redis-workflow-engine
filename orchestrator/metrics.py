"""In-memory metrics aggregation for the orchestrator."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, Tuple


@dataclass(slots=True)
class MetricSample:
    timestamp: float
    value: float


class MetricsCollector:
    """Thread-safe rolling metrics storage."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.RLock()
        self._counters: Dict[str, float] = {}
        self._timers: Dict[str, Deque[MetricSample]] = {}

    def increment(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + value

    def observe_duration(self, name: str, seconds: float) -> None:
        sample = MetricSample(timestamp=time.time(), value=seconds)
        with self._lock:
            samples = self._timers.setdefault(name, deque())
            samples.append(sample)
            self._prune(samples)

    def _prune(self, samples: Deque[MetricSample]) -> None:
        cutoff = time.time() - self._ttl
        while samples and samples[0].timestamp < cutoff:
            samples.popleft()

    def counters(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._counters)

    def timer_averages(self) -> Dict[str, float]:
        with self._lock:
            return {
                name: (sum(sample.value for sample in samples) / len(samples))
                for name, samples in self._timers.items()
                if samples
            }

    def export(self) -> Dict[str, float | Dict[str, float]]:
        return {
            "counters": self.counters(),
            "timer_averages": self.timer_averages(),
        }

    def timeline(self, name: str) -> Iterable[Tuple[float, float]]:
        with self._lock:
            return tuple((sample.timestamp, sample.value) for sample in self._timers.get(name, ()))
