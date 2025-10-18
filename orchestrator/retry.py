"""Retry policy primitives for workflow execution."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class RetryPolicy:
    """Simple exponential backoff retry policy."""

    max_attempts: int = 5
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    jitter: float = 0.2

    @classmethod
    def from_env(cls) -> "RetryPolicy":
        max_attempts_raw = os.getenv("WORKFLOW_MAX_RETRY_ATTEMPTS")
        max_attempts = int(max_attempts_raw) if max_attempts_raw is not None else cls.max_attempts
        return cls(max_attempts=max_attempts)

    def next_delay(self, attempt: int, max_attempts_override: Optional[int] = None) -> Optional[float]:
        limit = max_attempts_override or self.max_attempts
        if attempt >= limit:
            return None
        delay = self.base_delay_seconds * math.pow(2, attempt)
        delay = min(delay, self.max_delay_seconds)
        return delay

    def describe(self) -> dict[str, float | int]:
        return {
            "max_attempts": self.max_attempts,
            "base_delay_seconds": self.base_delay_seconds,
            "max_delay_seconds": self.max_delay_seconds,
            "jitter": self.jitter,
        }
