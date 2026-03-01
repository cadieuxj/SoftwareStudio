# Architecture

## Overview
The system implements a multi-agent waterfall pipeline orchestrated by LangGraph:
PM → Architect → Human Gate → Engineer → QA → Complete.

## Core Components
- **Orchestrator**: Manages sessions, checkpoints, and approvals.
- **Workflow**: LangGraph state machine for phase transitions.
- **Agents**: PM, Architect, Engineer, and QA wrappers.
- **Frontend**: Next.js 15 application (Vercel / Docker) providing session management, approval flows, a project Gantt timeline, team management, and a live code sandbox. The legacy Streamlit UI has been removed.
- **MCP Layer**: Declarative tool injection via `config/mcp_servers.json`.

## Persistence
- Session metadata stored in SQLite via `SessionStore`.
- Checkpoints stored via LangGraph checkpointer (SQLite or memory).

## Monitoring
- Health endpoints exposed by orchestrator server.
- Metrics exported in Prometheus format at `/metrics`.
