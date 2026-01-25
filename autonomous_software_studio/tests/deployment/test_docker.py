"""Deployment tests for Docker configuration."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
DOCKERFILE_DASH = PROJECT_ROOT / "Dockerfile.dashboard"
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


def test_dockerfile_exists() -> None:
    assert DOCKERFILE.exists()
    assert DOCKERFILE_DASH.exists()


def test_dockerfile_contains_security_controls() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert "python:3.11-slim" in content
    assert "USER appuser" in content
    assert "HEALTHCHECK" in content


def test_compose_has_services() -> None:
    data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    services = data.get("services", {})
    assert "orchestrator" in services
    assert "dashboard" in services


def test_compose_env_vars_present() -> None:
    data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    env = data["services"]["orchestrator"].get("environment", [])
    expected = {
        "ANTHROPIC_API_KEY_PM",
        "ANTHROPIC_API_KEY_ARCH",
        "ANTHROPIC_API_KEY_ENG",
        "ANTHROPIC_API_KEY_QA",
    }
    env_keys = {entry.split("=")[0] for entry in env}
    assert expected.issubset(env_keys)


def _docker_available() -> bool:
    return shutil.which("docker") is not None


@pytest.mark.skipif(not _docker_available(), reason="Docker is not available")
@pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_TESTS") != "1",
    reason="Set RUN_DOCKER_TESTS=1 to enable Docker integration tests",
)
def test_docker_compose_build() -> None:
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "build"],
        cwd=PROJECT_ROOT,
        check=True,
    )
