"""Model Context Protocol (MCP) server manager.

Provides registration, validation, and per-agent MCP configuration updates.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "mcp_servers.json"

_ENV_PATTERN = re.compile(r"\$\{[^}]+\}")


class MCPServerConfig(BaseModel):
    """Schema for MCP server definitions."""

    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a dict representation compatible with pydantic v1/v2."""
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()  # type: ignore[no-any-return,attr-defined]


class MCPServerManager:
    """Manage MCP server registrations and per-agent configurations."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.servers: dict[str, MCPServerConfig] = {}
        self.agent_assignments: dict[str, list[str]] = {}

        if self.config_path.exists():
            self.load_config()

    def load_config(self) -> None:
        """Load server definitions and assignments from config."""
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        servers_data = data.get("servers", {})
        assignments = data.get("agent_assignments", {})

        self.servers = {}
        for name, raw in servers_data.items():
            if not isinstance(raw, dict):
                raise ValueError(f"Invalid server definition for {name}")
            if "name" in raw and raw["name"] != name:
                raise ValueError(f"Server name mismatch: {name} vs {raw['name']}")
            config = MCPServerConfig(name=name, **raw)
            self.servers[name] = config

        if not isinstance(assignments, dict):
            raise ValueError("agent_assignments must be a dictionary")
        self.agent_assignments = {
            agent: list(servers) for agent, servers in assignments.items()
        }

    def save_config(self) -> None:
        """Persist current server definitions and assignments to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "servers": {
                name: self._strip_name_field(config.to_dict())
                for name, config in self.servers.items()
            },
            "agent_assignments": self.agent_assignments,
        }
        self.config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def register_server(self, name: str, config: MCPServerConfig) -> None:
        """Register a new MCP server definition."""
        if config.name != name:
            raise ValueError(f"Config name {config.name} does not match '{name}'")
        self.servers[name] = config

    def unregister_server(self, name: str) -> None:
        """Remove a server definition and any assignments."""
        if name not in self.servers:
            raise KeyError(f"Server not found: {name}")
        del self.servers[name]
        for agent, servers in self.agent_assignments.items():
            self.agent_assignments[agent] = [srv for srv in servers if srv != name]

    def get_available_servers(self) -> list[str]:
        """Return a sorted list of server names."""
        return sorted(self.servers.keys())

    def update_agent_config(self, agent_profile: str, servers: list[str]) -> None:
        """Write MCP config for an agent profile."""
        missing = [srv for srv in servers if srv not in self.servers]
        if missing:
            raise ValueError(f"Unknown MCP servers: {', '.join(missing)}")

        for server in servers:
            self.validate_server(server)

        config_dir = Path(f"~/.claude/{agent_profile}").expanduser()
        config_dir.mkdir(parents=True, exist_ok=True)
        mcp_config = config_dir / "mcp_settings.json"

        expanded_servers: dict[str, dict[str, Any]] = {}
        for server in servers:
            config = self.servers[server]
            expanded_env = self._expand_env_dict(config.env, allow_missing=False)
            config_dict = config.to_dict()
            config_dict["env"] = expanded_env
            expanded_servers[server] = config_dict

        payload = {"mcpServers": expanded_servers}
        mcp_config.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def apply_assignments(self) -> None:
        """Apply MCP server assignments for all agents."""
        for agent, servers in self.agent_assignments.items():
            self.update_agent_config(agent, servers)

    def validate_server(self, name: str) -> None:
        """Validate a server configuration and command availability."""
        if name not in self.servers:
            raise ValueError(f"Unknown MCP server: {name}")
        config = self.servers[name]
        self._ensure_command_available(config.command)
        self._expand_env_dict(config.env, allow_missing=False)

    def validate_all(self) -> None:
        """Validate all configured servers."""
        errors: list[str] = []
        for name in self.get_available_servers():
            try:
                self.validate_server(name)
            except ValueError as exc:
                errors.append(str(exc))

        if errors:
            raise ValueError("MCP validation failed: " + "; ".join(errors))

    def _ensure_command_available(self, command: str) -> None:
        if shutil.which(command) is None:
            raise ValueError(f"Command not available on PATH: {command}")

    def _expand_env_dict(self, env: dict[str, str], allow_missing: bool) -> dict[str, str]:
        expanded: dict[str, str] = {}
        for key, value in env.items():
            expanded_value = os.path.expandvars(value)
            if not allow_missing and _ENV_PATTERN.search(expanded_value):
                raise ValueError(f"Missing environment variable for {key}: {value}")
            expanded[key] = expanded_value
        return expanded

    @staticmethod
    def _strip_name_field(data: dict[str, Any]) -> dict[str, Any]:
        stripped = dict(data)
        stripped.pop("name", None)
        return stripped


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP Server Manager")
    parser.add_argument("--config", type=str, help="Path to MCP config file")
    parser.add_argument("--list", action="store_true", help="List available servers")
    parser.add_argument("--validate-all", action="store_true", help="Validate all servers")
    parser.add_argument("--test-server", type=str, help="Validate a single server")
    parser.add_argument("--apply-assignments", action="store_true", help="Apply agent assignments")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config_path = Path(args.config).expanduser() if args.config else DEFAULT_CONFIG_PATH
    manager = MCPServerManager(config_path=config_path)

    if args.list:
        for name in manager.get_available_servers():
            print(name)
        return

    if args.validate_all:
        manager.validate_all()
        print("All MCP servers validated.")
        return

    if args.test_server:
        manager.validate_server(args.test_server)
        print(f"Server validated: {args.test_server}")
        return

    if args.apply_assignments:
        manager.apply_assignments()
        print("Agent MCP configs updated.")
        return

    print("No action provided. Use --help for options.")


if __name__ == "__main__":
    main()
