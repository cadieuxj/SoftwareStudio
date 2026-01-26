"""Unit tests for agent settings manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.agent_settings import AgentSettingsManager, UsageLimitError


def test_default_settings_created(tmp_path: Path) -> None:
    settings_path = tmp_path / "agent_settings.json"
    manager = AgentSettingsManager(settings_path=settings_path)

    settings = manager.get_settings()
    assert settings_path.exists()
    assert "agents" in settings
    assert "pm" in settings["agents"]


def test_usage_limit_enforced(tmp_path: Path) -> None:
    settings_path = tmp_path / "agent_settings.json"
    manager = AgentSettingsManager(settings_path=settings_path)

    manager.update_agent("pm", {"daily_limit": 1, "hard_limit": True})
    manager.check_and_record_usage("pm", units=1)

    with pytest.raises(UsageLimitError):
        manager.check_and_record_usage("pm", units=1)


def test_prompt_versioning(tmp_path: Path) -> None:
    settings_path = tmp_path / "agent_settings.json"
    manager = AgentSettingsManager(settings_path=settings_path)

    version = manager.save_prompt_version("pm", "Prompt v1", note="first")
    versions = manager.list_prompt_versions("pm")

    assert version.exists()
    assert versions
    manager.set_active_prompt("pm", version)
    assert manager.get_prompt_path("pm") == version
