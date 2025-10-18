"""Redis workflow worker that orchestrates PHP activities."""

from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

import redis

from .config import RedisConfig, WorkerConfig
from .metrics import MetricsCollector
from .retry import RetryPolicy
from .storage import PostgresActionLogger, WorkflowAction

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkflowJob:
    workflow_id: str
    action: str
    payload: dict[str, Any]
    attempt: int = 0
    max_attempts: Optional[int] = None

    @classmethod
    def from_redis(cls, entry_id: str, data: Dict[bytes, bytes]) -> "WorkflowJob":
        payload_raw = data.get(b"payload", b"{}")
        try:
            payload = json.loads(payload_raw.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {"raw": payload_raw.decode("utf-8", errors="ignore")}
        max_attempts_raw = data.get(b"max_attempts")
        max_attempts = int(max_attempts_raw) if max_attempts_raw else None
        return cls(
            workflow_id=data.get(b"workflow_id", b"unknown").decode("utf-8"),
            action=data.get(b"action", b"unknown").decode("utf-8"),
            payload=payload,
            attempt=int(data.get(b"attempt", b"0")),
            max_attempts=max_attempts,
        )


class RedisWorkflowWorker:
    """Consumes Redis streams and dispatches PHP work via callbacks."""

    def __init__(
        self,
        redis_config: RedisConfig,
        worker_config: WorkerConfig,
        retry_policy: RetryPolicy,
        action_logger: Optional[PostgresActionLogger] = None,
        metrics: Optional[MetricsCollector] = None,
        handler: Optional[Callable[[WorkflowJob], None]] = None,
    ) -> None:
        self._redis_config = redis_config
        self._worker_config = worker_config
        self._retry_policy = retry_policy
        self._action_logger = action_logger
        self._metrics = metrics or MetricsCollector(worker_config.metrics_ttl_seconds)
        self._handler = handler or self.default_handler

        self._redis = redis.Redis.from_url(redis_config.url)
        self._executor = ThreadPoolExecutor(max_workers=worker_config.max_workers)
        self._stop_event = threading.Event()

        self._ensure_consumer_group()

    def _ensure_consumer_group(self) -> None:
        try:
            self._redis.xgroup_create(
                self._redis_config.stream,
                self._redis_config.consumer_group,
                id="$",
                mkstream=True,
            )
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def default_handler(self, job: WorkflowJob) -> None:
        logger.info("Received job for workflow %s -> %s", job.workflow_id, job.action)

    def start(self) -> None:
        logger.info("Starting workflow worker")
        while not self._stop_event.is_set():
            try:
                entries = self._redis.xreadgroup(
                    self._redis_config.consumer_group,
                    self._redis_config.consumer_name,
                    {self._redis_config.stream: ">"},
                    count=self._redis_config.batch_size,
                    block=int(self._worker_config.poll_interval_seconds * 1000),
                )
                if not entries:
                    continue
                for _, items in entries:
                    for entry_id, data in items:
                        job = WorkflowJob.from_redis(entry_id, data)
                        self._dispatch(entry_id, job)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Worker loop error: %s", exc)
                time.sleep(self._worker_config.poll_interval_seconds)

    def stop(self) -> None:
        logger.info("Stopping workflow worker")
        self._stop_event.set()
        self._executor.shutdown(wait=True)
        self._redis.close()

    def _dispatch(self, entry_id: str, job: WorkflowJob) -> None:
        logger.debug("Dispatching job %s", entry_id)
        self._metrics.increment("jobs_received")
        future = self._executor.submit(self._execute_job, entry_id, job)
        future.add_done_callback(lambda f: self._handle_completion(entry_id, job, f))

    def _execute_job(self, entry_id: str, job: WorkflowJob) -> WorkflowAction:
        start = time.perf_counter()
        success = False
        try:
            self._handler(job)
            success = True
        except Exception as exc:
            logger.exception("Job execution failed: %s", exc)
            raise
        finally:
            duration = time.perf_counter() - start
            self._metrics.observe_duration("job_duration", duration)
        return WorkflowAction(
            workflow_id=job.workflow_id,
            action=job.action,
            payload=job.payload,
            attempt=job.attempt,
            success=success,
            duration_seconds=duration,
        )

    def _handle_completion(
        self, entry_id: str, job: WorkflowJob, future: Future[WorkflowAction]
    ) -> None:
        try:
            action = future.result()
            self._redis.xack(
                self._redis_config.stream,
                self._redis_config.consumer_group,
                entry_id,
            )
            self._metrics.increment("jobs_completed")
            if self._action_logger:
                self._action_logger.log(action)
        except Exception as exc:
            self._metrics.increment("jobs_failed")
            self._retry_job(entry_id, job, exc)

    def _retry_job(self, entry_id: str, job: WorkflowJob, error: Exception) -> None:
        attempt = job.attempt + 1
        limit = job.max_attempts or self._worker_config.max_retry_attempts
        delay = self._retry_policy.next_delay(attempt, max_attempts_override=limit)
        if delay is None:
            logger.error(
                "Max attempts reached for workflow %s, action %s", job.workflow_id, job.action
            )
            self._redis.xack(
                self._redis_config.stream,
                self._redis_config.consumer_group,
                entry_id,
            )
            if self._action_logger:
                self._action_logger.log(
                    WorkflowAction(
                        workflow_id=job.workflow_id,
                        action=job.action,
                        payload={"error": str(error), **job.payload},
                        attempt=attempt,
                        success=False,
                        duration_seconds=0.0,
                    )
                )
            return

        self._redis.xack(
            self._redis_config.stream,
            self._redis_config.consumer_group,
            entry_id,
        )
        timer = threading.Timer(delay, self._requeue_job, args=(job, attempt, error))
        timer.daemon = True
        timer.start()
        self._metrics.increment("jobs_retried")
        logger.info(
            "Retrying workflow %s action %s in %.2fs (attempt %s)",
            job.workflow_id,
            job.action,
            delay,
            attempt,
        )

    def _requeue_job(self, job: WorkflowJob, attempt: int, error: Exception) -> None:
        payload = {
            "workflow_id": job.workflow_id,
            "action": job.action,
            "payload": json.dumps({"error": str(error), **job.payload}),
            "attempt": attempt,
        }
        if job.max_attempts is not None:
            payload["max_attempts"] = job.max_attempts
        self._redis.xadd(self._redis_config.stream, payload, id="*")

    def pending_jobs(self) -> Iterable[WorkflowJob]:
        pending = self._redis.xpending_range(
            self._redis_config.stream,
            self._redis_config.consumer_group,
            min="-",
            max="+",
            count=100,
        )
        for entry in pending:
            entry_id = entry[0]
            data = self._redis.xrange(self._redis_config.stream, entry_id, entry_id)
            if data:
                _, payload = data[0]
                yield WorkflowJob.from_redis(entry_id, payload)

    def metrics(self) -> Dict[str, Any]:
        return self._metrics.export()
