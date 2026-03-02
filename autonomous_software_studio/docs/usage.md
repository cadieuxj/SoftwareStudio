# Usage

## Frontend — Next.js Application (Vercel)

The primary interface is the Next.js app deployed at your Vercel URL (or `http://localhost:3000` in dev).

### Pages

| Route | Description |
|---|---|
| `/` | Dashboard — metrics overview, live session counts, recent activity |
| `/sessions` | Full session list with status filtering |
| `/sessions/[id]` | Live phase tracking, artifact preview, approve / reject |
| `/projects` | **Timeline** — Gantt chart of sessions grouped by project (1d / 7d / 30d / all zoom) |
| `/team` | Org member list, roles, session counts, last-active |
| `/approvals` | All sessions in `awaiting_approval` state |
| `/artifacts` | Browse PRDs, tech specs, bug reports |
| `/agents` | Agent config — provider, API keys, prompt editor with version history |
| `/logs` | Live execution log stream |
| `/github` | OAuth status, repo / issue / PR browser, create-session-from-issue |
| `/sandbox` | Interactive E2B code execution environment |

### Starting a session

1. Click **New Session** in the top-right header.
2. Enter a plain-English mission and an optional project name.
3. Click **Start** — the session progresses through PM → Architect.
4. When it reaches the **human gate**, review the PRD and Tech Spec in `/approvals` or `/sessions/[id]`.
5. Click **Approve** to trigger the Engineer → QA pipeline, or **Reject** with feedback to loop back.

### Theme toggle

Click the **Sun / Moon** button in the top-right header to switch between dark and light mode. Preference is stored in `localStorage`.

### User profile

Click your **avatar** (top-right) to access the Clerk profile menu: update name, manage 2FA, sign out.

---

## Backend — Python Orchestrator

### Start the server

```bash
cd autonomous_software_studio
source .venv/bin/activate
python -m src.orchestration.orchestrator --server --host 0.0.0.0 --port 8000
```

### Health endpoints

```bash
curl http://localhost:8000/healthz   # liveness
curl http://localhost:8000/readyz    # readiness (tests DB)
curl http://localhost:8000/metrics   # Prometheus metrics
```

### Start a session programmatically

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"mission": "Build a CSV-to-JSON CLI tool", "project_name": "csv2json"}'
```

---

## Agent Prompt Management

Open `/agents` in the UI to:

- Select an agent tab (PM, Architect, Engineer, QA)
- View and edit the system prompt — the editor pre-fills with the bundled default when the backend is offline
- Save a new prompt version with an optional change note, or reset to the default
- Browse and revert to previous versions via **History**

Direct API:

```bash
# Get active prompt
curl http://localhost:8000/agents/pm/prompt

# Save new version
curl -X POST http://localhost:8000/agents/pm/prompt \
  -H "Content-Type: application/json" \
  -d '{"content": "...", "note": "Tightened user story format"}'

# Revert
curl -X POST http://localhost:8000/agents/pm/prompt/revert \
  -H "Content-Type: application/json" \
  -d '{"path": "data/prompts/pm/v2.md"}'
```

---

## Running Tests

```bash
# Backend
cd autonomous_software_studio
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v

# Frontend type-checking
cd autonomous_software_studio/frontend
npx tsc --noEmit
npm run lint
```
