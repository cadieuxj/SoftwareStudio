# Troubleshooting

## Orchestrator Health Checks Failing
- Verify the server is running with `--server`.
- Check logs in `logs/` and container logs if deployed via Docker.

## Dashboard Not Loading
- Confirm Streamlit dependencies are installed.
- Ensure port 8501 is not in use.
- Run `streamlit run src/interfaces/dashboard.py`.

## MCP Validation Errors
- Ensure required environment variables are set (e.g., `GITHUB_TOKEN`).
- Validate servers with `python -m src.mcp.server_manager --validate-all`.

## Claude CLI not found
If you see `Claude CLI not found`, install claude-code or point the system to the
binary path:

```powershell
$env:CLAUDE_BINARY = "C:\\path\\to\\claude.exe"
streamlit run src/interfaces/dashboard.py
```

Linux/macOS install:
```bash
bash scripts/install_claude_cli.sh
```

## Configuration Validation Errors
- Run `python -m src.config.validator --check-all`.
- Verify `${VAR}` placeholders are defined in your environment.
