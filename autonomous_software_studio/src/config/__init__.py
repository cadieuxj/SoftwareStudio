"""Configuration management utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.validator import (
        AgentConfig,
        AppConfig,
        DatabaseConfig,
        MonitoringConfig,
        OrchestratorConfigModel,
        load_config,
        validate_config,
    )

__all__ = [
    "AgentConfig",
    "AppConfig",
    "DatabaseConfig",
    "MonitoringConfig",
    "OrchestratorConfigModel",
    "load_config",
    "validate_config",
]


def __getattr__(name: str):
    if name in __all__:
        from src.config import validator

        return getattr(validator, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
