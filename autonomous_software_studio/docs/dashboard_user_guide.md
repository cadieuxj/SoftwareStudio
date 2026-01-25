# Streamlit Dashboard User Guide

## Overview
The Streamlit control panel is the human-in-the-loop interface for monitoring, reviewing, and approving autonomous software sessions. It provides five pages:

- Session Management
- Artifact Review
- Approval Interface
- Live Logs
- Metrics & Analytics

The dashboard is read-only for artifacts: it displays files but does not edit them.

## Quick Start
Run the dashboard from the project root:

```bash
streamlit run src/interfaces/dashboard.py
```

## Session Management
- Lists all sessions with status, phase, and progress.
- Expands each session to show mission, project, and last update.
- Includes a kanban-style board grouped by status for quick triage.

## Artifact Review
- Select a session to review its artifacts.
- PRD and Tech Spec are rendered as Markdown.
- Code tab shows scaffold scripts and work directory files (read-only).

## Approval Interface
- Approve a session at the human gate with a single click.
- Request changes by sending feedback back to PM or Architect.
- Actions are disabled when the session is not awaiting approval.

## Live Logs
- Polls recent execution logs for a session.
- Use "Auto refresh" to poll every 2 seconds.
- Use "Refresh now" to pull the latest snapshot on demand.

## Metrics & Analytics
- High-level counts of total, running, awaiting approval, completed, and failed sessions.
- QA pass rate and average iteration metrics.
- Status breakdown table for operational monitoring.

## Screenshots
Placeholder screenshots are stored in `docs/screenshots/`. To regenerate them:

```bash
python scripts/generate_screenshots.py
```

## QA Checklist
```bash
pytest tests/integration/test_dashboard.py -v
streamlit run src/interfaces/dashboard.py
python scripts/dashboard_load_test.py --sessions 10
python scripts/generate_screenshots.py
```

## Troubleshooting
- If sessions do not appear, verify the orchestrator database exists in `data/`.
- If artifacts are missing, confirm the session has completed the relevant phase.
- If logs are empty, confirm log files exist under `logs/`.
