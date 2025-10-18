from __future__ import annotations

import os
from pathlib import Path

import pytest

from orchestrator.env import EnvironmentManager, REQUIRED_KEYS


def test_environment_manager_creates_defaults(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.workflow"
    manager = EnvironmentManager(env_file)
    snapshot = manager.ensure()

    assert snapshot.path == env_file
    assert snapshot.created is True
    for key in REQUIRED_KEYS:
        assert key in snapshot.values
        assert os.environ[key] == snapshot.values[key]


def test_propagate_updates_framework_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env.workflow"
    manager = EnvironmentManager(env_file)
    manager.ensure()

    laravel_env = tmp_path / "laravel" / ".env"
    laravel_env.parent.mkdir()
    laravel_env.write_text("APP_ENV=local\n")

    updated = manager.propagate_to_framework_envs(laravel_env.parent)
    assert laravel_env in updated

    contents = laravel_env.read_text()
    for key in REQUIRED_KEYS:
        assert key in contents


def test_missing_env_populates_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env.workflow"
    env_file.write_text("")
    manager = EnvironmentManager(env_file)

    monkeypatch.delenv("WORKFLOW_REDIS_URL", raising=False)

    snapshot = manager.ensure(required_keys={"WORKFLOW_REDIS_URL": "redis://localhost:6379/0"})
    assert snapshot.values["WORKFLOW_REDIS_URL"] == "redis://localhost:6379/0"
