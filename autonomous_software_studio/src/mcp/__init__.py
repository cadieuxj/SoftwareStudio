"""MCP integration layer for dynamic tool injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.mcp.server_manager import MCPServerConfig, MCPServerManager

__all__ = ["MCPServerConfig", "MCPServerManager"]


def __getattr__(name: str):  # noqa: D401
    """Lazily import manager types to avoid side effects on module run."""
    if name == "MCPServerConfig":
        from src.mcp.server_manager import MCPServerConfig

        return MCPServerConfig
    if name == "MCPServerManager":
        from src.mcp.server_manager import MCPServerManager

        return MCPServerManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
