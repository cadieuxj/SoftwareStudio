"""Integration tests for configuration validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.validator import validate_config


def test_validate_development_config() -> None:
    config_path = Path(__file__).resolve().parents[2] / "config" / "development.yaml"
    config = validate_config(config_path)
    assert config.orchestrator.max_sessions > 0


def test_validate_testing_config() -> None:
    config_path = Path(__file__).resolve().parents[2] / "config" / "testing.yaml"
    config = validate_config(config_path)
    assert config.monitoring.enabled is False


def test_validate_production_config_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_HOST", "db.example.com")
    config_path = Path(__file__).resolve().parents[2] / "config" / "production.yaml"
    config = validate_config(config_path)
    assert config.database.host == "db.example.com"
