"""Shared environment management for Python and PHP components."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Mapping
from urllib.parse import urlparse

from dotenv import dotenv_values, set_key

logger = logging.getLogger(__name__)


DEFAULT_ENV_FILE = Path(".env.workflow")


REQUIRED_KEYS: Mapping[str, str] = {
    "WORKFLOW_REDIS_URL": "redis://127.0.0.1:6379/0",
    "WORKFLOW_REDIS_STREAM": "workflow:stream",
    "WORKFLOW_POSTGRES_DSN": "postgresql://workflow:workflow@localhost:5432/workflows",
    "WORKFLOW_DASHBOARD_HOST": "127.0.0.1",
    "WORKFLOW_DASHBOARD_PORT": "8000",
    "WORKFLOW_POLL_INTERVAL": "0.05",
    "WORKFLOW_MAX_RETRY_ATTEMPTS": "5",
}


@dataclass(slots=True)
class EnvironmentSnapshot:
    """Represents the consolidated environment state after validation."""

    path: Path
    values: Dict[str, str]
    created: bool = False
    modified_keys: Iterable[str] = field(default_factory=tuple)


class EnvironmentManager:
    """Loads and validates environment configuration for the stack."""

    def __init__(self, env_file: Path | str = DEFAULT_ENV_FILE) -> None:
        self.env_file = Path(env_file)

    def ensure(self, required_keys: Mapping[str, str] | None = None) -> EnvironmentSnapshot:
        required = dict(REQUIRED_KEYS if required_keys is None else required_keys)
        created = False
        modified: list[str] = []

        if not self.env_file.exists():
            self.env_file.write_text(
                "# Shared Redis workflow environment file\n"
                "# Update the values below or override with real environment variables.\n"
            )
            created = True

        file_values = {
            key: value
            for key, value in dotenv_values(self.env_file).items()
            if value is not None
        }

        for key, default in required.items():
            existing = os.getenv(key) or file_values.get(key)
            if existing is None:
                set_key(str(self.env_file), key, default)
                file_values[key] = default
                modified.append(key)

        for key, value in file_values.items():
            os.environ.setdefault(key, value)

        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise RuntimeError(
                "Missing environment variables: " + ", ".join(sorted(missing))
            )

        self._ensure_php_compatibility()

        if self._running_in_docker() and (created or modified):
            logger.info(
                "Detected Docker runtime; ensure bind-mounted env file %s persists",
                self.env_file,
            )

        snapshot_values = {key: os.environ[key] for key in required}
        return EnvironmentSnapshot(
            path=self.env_file,
            values=snapshot_values,
            created=created,
            modified_keys=tuple(modified),
        )

    def propagate_to_framework_envs(self, project_root: Path | str) -> list[Path]:
        root = Path(project_root)
        discovered: list[Path] = []
        for candidate in (".env", ".env.local", ".env.example"):
            env_path = root / candidate
            if not env_path.exists():
                continue
            self._merge_env_file(env_path)
            discovered.append(env_path)
        return discovered

    def _merge_env_file(self, env_path: Path) -> None:
        values = {
            key: value
            for key, value in dotenv_values(env_path).items()
            if value is not None
        }

        desired = self._current_env_values()
        wrote = False
        for key, value in desired.items():
            if values.get(key) is None:
                set_key(str(env_path), key, value)
                wrote = True

        if wrote:
            logger.info("Updated %s with workflow environment defaults", env_path)

    def _current_env_values(self) -> Dict[str, str]:
        values = {key: os.environ[key] for key in REQUIRED_KEYS}
        redis_components = self._parse_redis(os.environ["WORKFLOW_REDIS_URL"])
        values.update(redis_components)
        return values

    def _ensure_php_compatibility(self) -> None:
        redis_values = self._parse_redis(os.environ["WORKFLOW_REDIS_URL"])
        for key, value in redis_values.items():
            os.environ.setdefault(key, value)
            current = dotenv_values(self.env_file).get(key)
            if current is None:
                set_key(str(self.env_file), key, value)
        # POSTGRES settings are consumed directly from WORKFLOW_POSTGRES_DSN.

    def _parse_redis(self, url: str) -> Dict[str, str]:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = str(parsed.port or 6379)
        password = parsed.password or ""
        path = (parsed.path or "/0").lstrip("/") or "0"
        return {
            "REDIS_WORKFLOW_HOST": host,
            "REDIS_WORKFLOW_PORT": port,
            "REDIS_WORKFLOW_PASSWORD": password,
            "REDIS_WORKFLOW_DATABASE": path,
            "REDIS_WORKFLOW_STREAM": os.environ.get(
                "WORKFLOW_REDIS_STREAM", REQUIRED_KEYS["WORKFLOW_REDIS_STREAM"]
            ),
        }

    @staticmethod
    def _running_in_docker() -> bool:
        return Path("/.dockerenv").exists() or os.environ.get("DOCKER_CONTAINER") == "true"

