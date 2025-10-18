"""Postgres-backed action logging."""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable

from psycopg import Connection, connect

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkflowAction:
    workflow_id: str
    action: str
    payload: dict[str, Any]
    attempt: int
    success: bool
    duration_seconds: float


class PostgresActionLogger:
    """Persists workflow actions to Postgres for replay and observability."""

    def __init__(self, dsn: str, table: str = "workflow_actions") -> None:
        self._dsn = dsn
        self._table = table
        self._ensure_table()

    @classmethod
    def from_env(cls) -> "PostgresActionLogger":
        from .config import PostgresConfig

        config = PostgresConfig.from_env()
        return cls(dsn=config.dsn, table=config.table)

    def _ensure_table(self) -> None:
        try:
            with connect(self._dsn) as conn, conn.cursor() as cur:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._table} (
                        id BIGSERIAL PRIMARY KEY,
                        workflow_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        attempt INTEGER NOT NULL,
                        success BOOLEAN NOT NULL,
                        duration_seconds DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                conn.commit()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to ensure action log table exists: %s", exc)

    def log(self, action: WorkflowAction) -> None:
        try:
            with connect(self._dsn) as conn, conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._table} (
                        workflow_id, action, payload, attempt, success, duration_seconds
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        action.workflow_id,
                        action.action,
                        json.dumps(action.payload),
                        action.attempt,
                        action.success,
                        action.duration_seconds,
                    ),
                )
                conn.commit()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to persist workflow action: %s", exc)

    def fetch_history(self, workflow_id: str, limit: int = 200) -> Iterable[WorkflowAction]:
        with contextlib.closing(connect(self._dsn)) as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT workflow_id, action, payload, attempt, success, duration_seconds
                FROM {self._table}
                WHERE workflow_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (workflow_id, limit),
            )
            for row in cur.fetchall():
                payload = row[2]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                yield WorkflowAction(
                    workflow_id=row[0],
                    action=row[1],
                    payload=payload,
                    attempt=row[3],
                    success=row[4],
                    duration_seconds=row[5],
                )

    def recent_actions(self, limit: int = 50) -> Iterable[WorkflowAction]:
        with contextlib.closing(connect(self._dsn)) as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT workflow_id, action, payload, attempt, success, duration_seconds
                FROM {self._table}
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            for row in cur.fetchall():
                payload = row[2]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                yield WorkflowAction(
                    workflow_id=row[0],
                    action=row[1],
                    payload=payload,
                    attempt=row[3],
                    success=row[4],
                    duration_seconds=row[5],
                )

    def connection(self) -> Connection[Any]:
        return connect(self._dsn)
