# Troubleshooting

> For a comprehensive troubleshooting guide see also `docs/guides/TROUBLESHOOTING.md`.

## Orchestrator health checks failing

- Verify the server started: `python -m src.orchestration.orchestrator --server`
- Check logs in `logs/` or `docker compose logs orchestrator`
- Confirm `DATABASE_URL` (or SQLite path) is set correctly

## Frontend not loading (Vercel / local)

- Confirm `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` are set
- In dev: make sure `npm run dev` is running and the port (3000) is free
- Check the browser console for Clerk or API errors
- Run `npx tsc --noEmit` to catch TypeScript errors before deploying

## Prompt editor is empty on the Agents page

The `/agents` page calls the Python orchestrator to fetch the active prompt. If the backend is offline, the editor pre-fills with the **bundled default prompt** from `src/lib/defaultPrompts.ts`. An amber banner reads *"Showing default template — backend offline."* — this is expected behaviour; no action needed.

## MCP validation errors

- Ensure required env vars are set (e.g., `GITHUB_TOKEN`)
- Validate with: `python -m src.mcp.server_manager --validate-all`

## Claude CLI not found

Install via npm:

```bash
npm install -g @anthropic-ai/claude-code
```

Or point to a custom binary:

```bash
# Linux / macOS
export CLAUDE_BINARY="/path/to/claude"

# Windows (PowerShell)
$env:CLAUDE_BINARY = "C:\path\to\claude.exe"
```

## Configuration validation errors

```bash
python -m src.config.validator --check-all
```

Verify all `${VAR}` placeholders in `config/*.yaml` are defined in your environment.

## Session stuck in `running`

1. Check orchestrator logs: `docker compose logs orchestrator | grep <session_id>`
2. If the agent timed out, restart the orchestrator — LangGraph resumes from the last checkpoint
3. As a last resort, update the session status directly in the DB

## Clerk webhook not firing

1. Verify the endpoint URL in Clerk Dashboard → Webhooks is `https://<domain>/api/webhooks/clerk`
2. Confirm `CLERK_WEBHOOK_SECRET` matches the value shown in Clerk
3. Check Next.js logs — the route must use `req.text()` (not `req.json()`) for Svix signature verification

## E2B sandbox errors

- Verify `E2B_API_KEY` is valid
- Create a new sandbox rather than re-using a stale sandbox ID (sandboxes time out)

## Portkey / AI routing errors

- Verify `PORTKEY_API_KEY` and `PORTKEY_DEFAULT_VIRTUAL_KEY` are correct
- The virtual key in Portkey must map to a valid provider key in the Portkey dashboard
- Check `aiTraces` table for failed calls
