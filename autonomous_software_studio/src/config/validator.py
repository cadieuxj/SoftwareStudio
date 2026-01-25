"""Configuration validation utilities for environment-specific settings."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIGS = [
    PROJECT_ROOT / "config" / "production.yaml",
    PROJECT_ROOT / "config" / "development.yaml",
    PROJECT_ROOT / "config" / "testing.yaml",
]

_ENV_PATTERN = re.compile(r"\$\{[^}]+\}")


class OrchestratorConfigModel(BaseModel):
    max_sessions: int = Field(..., ge=1)
    session_timeout: int = Field(..., ge=1)
    checkpoint_interval: int = Field(..., ge=1)
    log_level: str


class AgentConfig(BaseModel):
    timeout: int = Field(..., ge=1)
    max_retries: int = Field(..., ge=0)


class DatabaseConfig(BaseModel):
    type: Literal["postgresql", "sqlite"]
    host: str
    port: int


class MonitoringConfig(BaseModel):
    enabled: bool
    prometheus_port: int = Field(..., ge=0)


class AppConfig(BaseModel):
    orchestrator: OrchestratorConfigModel
    agents: AgentConfig
    database: DatabaseConfig
    monitoring: MonitoringConfig


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        expanded = os.path.expandvars(value)
        if _ENV_PATTERN.search(expanded):
            raise ValueError(f"Missing environment variable in value: {value}")
        return expanded
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(path: Path) -> dict[str, Any]:
    """Load and expand a YAML config file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config must be a dictionary")
    return _expand_env(raw)


def validate_config(path: Path) -> AppConfig:
    """Validate a single config file."""
    data = load_config(path)
    return AppConfig(**data)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configuration validator")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--check-all", action="store_true", help="Validate all configs")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.check_all:
        for config_path in DEFAULT_CONFIGS:
            validate_config(config_path)
        print("All configs validated.")
        return

    if args.config:
        path = Path(args.config).expanduser()
        validate_config(path)
        print(f"Config validated: {path}")
        return

    print("No config provided. Use --help for options.")


if __name__ == "__main__":
    main()
