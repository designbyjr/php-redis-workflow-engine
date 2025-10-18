"""FastAPI dashboard exposing workflow observability endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from orchestrator.config import PostgresConfig, WorkerConfig
from orchestrator.metrics import MetricsCollector
from orchestrator.storage import PostgresActionLogger

app = FastAPI(title="Redis Workflow Engine Dashboard")


class DashboardState:
    def __init__(self, config: WorkerConfig, postgres: PostgresConfig) -> None:
        self.metrics = MetricsCollector(ttl_seconds=config.metrics_ttl_seconds)
        self.logger = PostgresActionLogger(dsn=postgres.dsn, table=postgres.table)
        self.config = config
        self.postgres = postgres


_state: Optional[DashboardState] = None


def configure_state(
    *,
    metrics: Optional[MetricsCollector] = None,
    config: Optional[WorkerConfig] = None,
    postgres: Optional[PostgresConfig] = None,
) -> DashboardState:
    """Allow external callers to override the dashboard's singleton state."""

    global _state
    worker_config = config or WorkerConfig.from_env()
    postgres_config = postgres or PostgresConfig.from_env()
    _state = DashboardState(worker_config, postgres_config)
    if metrics is not None:
        _state.metrics = metrics
    return _state


def get_state() -> DashboardState:
    global _state
    if _state is None:
        _state = DashboardState(WorkerConfig.from_env(), PostgresConfig.from_env())
    return _state


@app.get("/metrics")
def get_metrics(state: DashboardState = Depends(get_state)) -> JSONResponse:
    return JSONResponse(state.metrics.export())


@app.get("/workflows/{workflow_id}")
def get_workflow_history(
    workflow_id: str,
    limit: int = 200,
    state: DashboardState = Depends(get_state),
) -> JSONResponse:
    history = list(state.logger.fetch_history(workflow_id, limit=limit))
    if not history:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return JSONResponse([
        {
            "workflow_id": action.workflow_id,
            "action": action.action,
            "payload": action.payload,
            "attempt": action.attempt,
            "success": action.success,
            "duration_seconds": action.duration_seconds,
        }
        for action in history
    ])


@app.get("/actions/recent")
def get_recent_actions(
    limit: int = 50,
    state: DashboardState = Depends(get_state),
) -> JSONResponse:
    actions = list(state.logger.recent_actions(limit=limit))
    return JSONResponse([
        {
            "workflow_id": action.workflow_id,
            "action": action.action,
            "payload": action.payload,
            "attempt": action.attempt,
            "success": action.success,
            "duration_seconds": action.duration_seconds,
        }
        for action in actions
    ])
