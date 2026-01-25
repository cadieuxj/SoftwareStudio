# MCP Integration Guide

## Overview
The Model Context Protocol (MCP) layer lets you declaratively register external tools
and inject them into agent profiles at runtime. This enables dynamic tool access
without hardcoding integrations into the agent runtime.

## Configuration
Server definitions live in `config/mcp_servers.json`.

```json
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
      "description": "Access to project files"
    }
  },
  "agent_assignments": {
    "pm": ["filesystem"]
  }
}
```

### Environment variables
`env` entries support `${VAR_NAME}` expansion. Missing variables cause validation
to fail so secrets are never silently skipped.

## Manager API
The manager is implemented in `src/mcp/server_manager.py`.

- `register_server(name, config)` adds a server definition.
- `unregister_server(name)` removes a server.
- `get_available_servers()` lists registered servers.
- `update_agent_config(agent_profile, servers)` writes `~/.claude/<agent>/mcp_settings.json`.

## CLI Usage
```bash
# Run from the project folder (recommended)
cd autonomous_software_studio

# Validate all server configs
python -m src.mcp.server_manager --validate-all

# Validate a single server
python -m src.mcp.server_manager --test-server filesystem

# Apply agent assignments from config/mcp_servers.json
python -m src.mcp.server_manager --apply-assignments

# List servers
python -m src.mcp.server_manager --list
```

### Required environment variables
The sample `github` server uses `${GITHUB_TOKEN}`. Validation will fail if it is
not set. Export it before running `--validate-all`:

```powershell
$env:GITHUB_TOKEN = "your_token_here"
python -m src.mcp.server_manager --validate-all
```

### Running from the repo root
If you run commands from the repository root (one level above `autonomous_software_studio`),
Python will not find the `src` package. Either `cd` into the project folder or set
`PYTHONPATH`:

```powershell
$env:PYTHONPATH = "$PWD\autonomous_software_studio"
python -m src.mcp.server_manager --validate-all
```

## Agent Config Output
The generated file lives at:

```
~/.claude/<agent_profile>/mcp_settings.json
```

Example output:
```json
{
  "mcpServers": {
    "filesystem": {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
      "env": {},
      "description": "Access to project files"
    }
  }
}
```

## QA Checklist
```bash
pytest tests/integration/test_mcp_manager.py -v
python -m src.mcp.server_manager --validate-all
python -m src.mcp.server_manager --test-server filesystem
```
