"""Command-line helpers to bootstrap the orchestrator stack."""

from __future__ import annotations

import argparse
import logging
import threading
from pathlib import Path
from typing import Iterable

import uvicorn

from .config import RedisConfig, WorkerConfig
from .env import EnvironmentManager
from .metrics import MetricsCollector
from .retry import RetryPolicy
from .storage import PostgresActionLogger
from .worker import RedisWorkflowWorker

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Redis workflow engine orchestration utilities",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("env", help="Ensure shared environment variables exist")

    sub.add_parser("worker", help="Run the Redis workflow worker")

    dashboard_parser = sub.add_parser(
        "dashboard", help="Run the FastAPI dashboard in-process"
    )
    dashboard_parser.add_argument("--reload", action="store_true")

    stack_parser = sub.add_parser(
        "stack",
        help="Launch the worker and dashboard together using a shared environment",
    )
    stack_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable FastAPI reload mode (development only)",
    )

    parser.add_argument(
        "--framework-path",
        action="append",
        default=[],
        help=(
            "Optional path(s) to Laravel or Symfony projects; their .env files will "
            "be updated with workflow settings when using the env/stack commands."
        ),
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Path to the shared .env.workflow file (defaults to project root)",
    )
    return parser


def configure_environment(env_file: str | None, frameworks: Iterable[str]) -> EnvironmentManager:
    manager = EnvironmentManager(env_file) if env_file else EnvironmentManager()
    snapshot = manager.ensure()
    logger.info(
        "Environment loaded from %s (%s)",
        snapshot.path,
        "created" if snapshot.created else "existing",
    )
    for framework_path in frameworks:
        discovered = manager.propagate_to_framework_envs(Path(framework_path))
        if discovered:
            logger.info(
                "Propagated workflow variables into %s", ", ".join(map(str, discovered))
            )
    return manager


def run_worker() -> RedisWorkflowWorker:
    worker = RedisWorkflowWorker(
        redis_config=RedisConfig.from_env(),
        worker_config=WorkerConfig.from_env(),
        retry_policy=RetryPolicy.from_env(),
        action_logger=PostgresActionLogger.from_env(),
    )

    def _run() -> None:
        try:
            worker.start()
        except KeyboardInterrupt:  # pragma: no cover - interactive use only
            worker.stop()

    thread = threading.Thread(target=_run, name="workflow-worker", daemon=True)
    thread.start()
    return worker


def run_dashboard(reload: bool = False, metrics: MetricsCollector | None = None) -> None:
    from dashboard import app as dashboard_app

    if metrics is not None:
        dashboard_app.configure_state(metrics=metrics)

    config = WorkerConfig.from_env()
    uvicorn.run(
        "dashboard.app:app",
        host=config.dashboard_host,
        port=config.dashboard_port,
        reload=reload,
        log_level="info",
    )


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    configure_environment(args.env_file, args.framework_path)

    if args.command == "env":
        return

    if args.command == "worker":
        worker = run_worker()
        try:
            while True:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            worker.stop()
        return

    if args.command == "dashboard":
        run_dashboard(reload=args.reload)
        return

    if args.command == "stack":
        metrics = MetricsCollector(ttl_seconds=WorkerConfig.from_env().metrics_ttl_seconds)
        worker = RedisWorkflowWorker(
            redis_config=RedisConfig.from_env(),
            worker_config=WorkerConfig.from_env(),
            retry_policy=RetryPolicy.from_env(),
            action_logger=PostgresActionLogger.from_env(),
            metrics=metrics,
        )

        def _worker_target() -> None:
            try:
                worker.start()
            except KeyboardInterrupt:
                worker.stop()

        thread = threading.Thread(target=_worker_target, daemon=True)
        thread.start()

        try:
            run_dashboard(reload=args.reload, metrics=metrics)
        finally:
            worker.stop()
        return


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
