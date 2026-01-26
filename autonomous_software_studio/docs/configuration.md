# Configuration

## Environment Files
Copy `.env.template` to `.env` and set the required API keys.

Key variables:
- `ANTHROPIC_API_KEY_PM`
- `ANTHROPIC_API_KEY_ARCH`
- `ANTHROPIC_API_KEY_ENG`
- `ANTHROPIC_API_KEY_QA`
- `ORCHESTRATOR_DB_PATH` (optional override for SQLite path)

## YAML Configs
Environment-specific config files live in `config/`:
- `config/production.yaml`
- `config/development.yaml`
- `config/testing.yaml`

Validate configs with:
```bash
python -m src.config.validator --check-all
```

## Agent Settings
Agent account settings and prompt versions are stored in:
- `data/agent_settings.json`
- `data/agent_settings.history/`
- `data/prompts/<agent>/`

These files are managed via the dashboard "Agent Account Management" page.

## MCP Servers
MCP server definitions are stored in `config/mcp_servers.json`. See
`docs/mcp_integration_guide.md` for details.
