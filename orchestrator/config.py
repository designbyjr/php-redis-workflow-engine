"""Configuration dataclasses used by the orchestrator."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class RedisConfig:
    """Connection configuration for Redis."""

    url: str = "redis://localhost:6379/0"
    stream: str = "workflow:stream"
    consumer_group: str = "workflow-orchestrator"
    consumer_name: str = "python-worker"
    batch_size: int = 32

    @classmethod
    def from_env(cls) -> "RedisConfig":
        return cls(
            url=os.getenv("WORKFLOW_REDIS_URL", cls.url),
            stream=os.getenv("WORKFLOW_REDIS_STREAM", cls.stream),
            consumer_group=os.getenv(
                "WORKFLOW_REDIS_CONSUMER_GROUP", cls.consumer_group
            ),
            consumer_name=os.getenv("WORKFLOW_REDIS_CONSUMER", cls.consumer_name),
            batch_size=int(os.getenv("WORKFLOW_REDIS_BATCH", cls.batch_size)),
        )


@dataclass(slots=True)
class PostgresConfig:
    """Connection configuration for Postgres logging."""

    dsn: str = "postgresql://workflow:workflow@localhost:5432/workflows"
    table: str = "workflow_actions"

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        return cls(
            dsn=os.getenv("WORKFLOW_POSTGRES_DSN", cls.dsn),
            table=os.getenv("WORKFLOW_POSTGRES_TABLE", cls.table),
        )


@dataclass(slots=True)
class WorkerConfig:
    """Runtime behaviour for the Python worker."""

    max_workers: int = 256
    poll_interval_seconds: float = 0.05
    visibility_timeout_seconds: float = 60.0
    metrics_ttl_seconds: int = 300
    log_batch_size: int = 100
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000
    debug: bool = False
    php_stacktrace_basepath: Optional[str] = None
    max_retry_attempts: int = 5
    frameworks: tuple[str, ...] = field(
        default_factory=lambda: ("laravel", "symfony")
    )

    def __post_init__(self) -> None:
        if self.poll_interval_seconds <= 0:
            raise ValueError("WORKFLOW_POLL_INTERVAL must be greater than zero")
        if self.max_retry_attempts <= 0:
            raise ValueError("WORKFLOW_MAX_RETRY_ATTEMPTS must be greater than zero")

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        poll_interval_raw = os.getenv("WORKFLOW_POLL_INTERVAL")
        if poll_interval_raw is None:
            raise RuntimeError(
                "WORKFLOW_POLL_INTERVAL must be configured before starting the worker"
            )

        max_retry_raw = os.getenv("WORKFLOW_MAX_RETRY_ATTEMPTS")
        if max_retry_raw is None:
            raise RuntimeError(
                "WORKFLOW_MAX_RETRY_ATTEMPTS must be configured before starting the worker"
            )

        return cls(
            max_workers=int(os.getenv("WORKFLOW_MAX_WORKERS", cls.max_workers)),
            poll_interval_seconds=float(poll_interval_raw),
            visibility_timeout_seconds=float(
                os.getenv(
                    "WORKFLOW_VISIBILITY_TIMEOUT",
                    cls.visibility_timeout_seconds,
                )
            ),
            metrics_ttl_seconds=int(
                os.getenv("WORKFLOW_METRICS_TTL", cls.metrics_ttl_seconds)
            ),
            log_batch_size=int(os.getenv("WORKFLOW_LOG_BATCH", cls.log_batch_size)),
            dashboard_host=os.getenv("WORKFLOW_DASHBOARD_HOST", cls.dashboard_host),
            dashboard_port=int(
                os.getenv("WORKFLOW_DASHBOARD_PORT", cls.dashboard_port)
            ),
            debug=os.getenv("WORKFLOW_DEBUG", "false").lower() in {"1", "true", "yes"},
            php_stacktrace_basepath=os.getenv("WORKFLOW_PHP_STACKTRACE", None),
            max_retry_attempts=int(max_retry_raw),
        )
