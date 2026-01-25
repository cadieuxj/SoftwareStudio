"""Integration tests for MCP server manager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.mcp.server_manager import MCPServerConfig, MCPServerManager


def _set_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


def test_server_registration(tmp_path: Path) -> None:
    manager = MCPServerManager(config_path=tmp_path / "mcp.json")

    config = MCPServerConfig(
        name="local",
        command="python",
        args=["-V"],
        env={},
        description="Test server",
    )
    manager.register_server("local", config)
    assert manager.get_available_servers() == ["local"]

    manager.unregister_server("local")
    assert manager.get_available_servers() == []


def test_configuration_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = MCPServerManager(config_path=tmp_path / "mcp.json")
    _set_home(monkeypatch, tmp_path)
    monkeypatch.setenv("TEST_TOKEN", "abc123")

    config = MCPServerConfig(
        name="local",
        command="python",
        args=["-V"],
        env={"TOKEN": "${TEST_TOKEN}"},
        description="Test server",
    )
    manager.register_server("local", config)
    manager.update_agent_config("pm", ["local"])

    config_path = tmp_path / ".claude" / "pm" / "mcp_settings.json"
    assert config_path.exists()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert "local" in data["mcpServers"]


def test_environment_variable_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = MCPServerManager(config_path=tmp_path / "mcp.json")
    _set_home(monkeypatch, tmp_path)
    monkeypatch.setenv("TOKEN_VALUE", "expanded")

    config = MCPServerConfig(
        name="envtest",
        command="python",
        args=["-V"],
        env={"TOKEN": "${TOKEN_VALUE}"},
        description="Env server",
    )
    manager.register_server("envtest", config)
    manager.update_agent_config("qa", ["envtest"])

    config_path = tmp_path / ".claude" / "qa" / "mcp_settings.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["mcpServers"]["envtest"]["env"]["TOKEN"] == "expanded"


def test_invalid_server_detection(tmp_path: Path) -> None:
    manager = MCPServerManager(config_path=tmp_path / "mcp.json")

    config = MCPServerConfig(
        name="bad",
        command="definitely-not-a-command-xyz",
        args=[],
        env={},
        description="Invalid server",
    )
    manager.register_server("bad", config)

    with pytest.raises(ValueError, match="Command not available"):
        manager.validate_server("bad")


def test_dynamic_tool_injection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = MCPServerManager(config_path=tmp_path / "mcp.json")
    _set_home(monkeypatch, tmp_path)

    server_a = MCPServerConfig(
        name="one",
        command="python",
        args=["-V"],
        env={},
        description="Server one",
    )
    server_b = MCPServerConfig(
        name="two",
        command="python",
        args=["-V"],
        env={},
        description="Server two",
    )
    manager.register_server("one", server_a)
    manager.register_server("two", server_b)

    manager.update_agent_config("eng", ["one", "two"])
    config_path = tmp_path / ".claude" / "eng" / "mcp_settings.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))

    assert set(data["mcpServers"].keys()) == {"one", "two"}


def test_missing_env_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = MCPServerManager(config_path=tmp_path / "mcp.json")
    _set_home(monkeypatch, tmp_path)

    config = MCPServerConfig(
        name="envfail",
        command="python",
        args=["-V"],
        env={"TOKEN": "${MISSING_TOKEN}"},
        description="Missing env server",
    )
    manager.register_server("envfail", config)

    with pytest.raises(ValueError, match="Missing environment variable"):
        manager.update_agent_config("pm", ["envfail"])
