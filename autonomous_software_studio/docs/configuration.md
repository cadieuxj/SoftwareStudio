# Configuration

## Environment Files
Copy `.env.template` to `.env` and set the required API keys.

Key variables:
- `ANTHROPIC_API_KEY_PM`
- `ANTHROPIC_API_KEY_ARCH`
- `ANTHROPIC_API_KEY_ENG`
- `ANTHROPIC_API_KEY_QA`

## YAML Configs
Environment-specific config files live in `config/`:
- `config/production.yaml`
- `config/development.yaml`
- `config/testing.yaml`

Validate configs with:
```bash
python -m src.config.validator --check-all
```

## MCP Servers
MCP server definitions are stored in `config/mcp_servers.json`. See
`docs/mcp_integration_guide.md` for details.
