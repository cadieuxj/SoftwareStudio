# Architecture Documentation

## Overview

Sovereign AI is a multi-agent platform for autonomous software development. It uses LangGraph for stateful workflow orchestration, Claude CLI for agent execution, and a Next.js frontend (deployed on Vercel) for the human-in-the-loop control plane.

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Browser / Client                          │
│              Next.js 15 (Vercel / self-hosted)                   │
│   Sessions · Approvals · Artifacts · Agents · Timeline · Team    │
└──────────────────────┬───────────────────────────────────────────┘
                       │  REST API calls + Clerk auth (JWT)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│              Next.js API Routes  (:3000)                         │
│  /api/sessions  /api/sandbox  /api/ai/chat  /api/metrics         │
│  /api/team  /api/webhooks/clerk                                  │
│                                                                  │
│  Auth: Clerk B2B   DB: Drizzle ORM → PostgreSQL                  │
│  AI routing: Portkey Gateway   Code exec: E2B SDK                │
└──────────────────────┬───────────────────────────────────────────┘
                       │  /api/backend/* (reverse proxy)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│            Python Orchestrator  (:8000)                          │
│            LangGraph StateGraph + SQLite checkpointing           │
│                                                                  │
│  PM Agent → Architect Agent → [HUMAN GATE] → Engineer → QA      │
│                                     ▲              │             │
│                                     └──────────────┘ (repair)   │
└──────────────────────────────────────────────────────────────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
┌─────────────────┐    ┌─────────────────────┐
│  PostgreSQL 16  │    │     Redis 7          │
│  (sessions,     │    │  (caching, session   │
│   artifacts,    │    │   management)        │
│   configs,      │    │                      │
│   AI traces)    │    └─────────────────────┘
└─────────────────┘
```

## Key design decisions

| Decision | Reason |
|---|---|
| Python backend for orchestration | LangGraph, LangChain, and Claude CLI tooling are Python-native |
| Next.js frontend, independently deployed | Separate deploy cadence; Vercel for frontend, any Docker host for backend |
| Four isolated Claude CLI personas | Role separation; each agent has its own profile, API key, and system prompt |
| LangGraph `interrupt` | Clean stateful pause at the human gate without polling hacks |
| Drizzle ORM on PostgreSQL | Type-safe SQL, fast migrations, org-level row isolation |
| Clerk B2B auth | Enterprise org management, SSO, and webhook sync out of the box |
| Portkey gateway | LLM provider abstraction, cost tracking, fallback routing |
| E2B sandboxes | Isolated, ephemeral code execution that cannot affect the host |

## Frontend stack

| Layer | Library |
|---|---|
| Framework | Next.js 15 App Router |
| Language | TypeScript 5 |
| Styling | Tailwind CSS — CSS variable token system, dark + light mode |
| UI Primitives | Radix UI |
| Animations | Framer Motion |
| Server State | TanStack React Query 5 |
| Client State | Zustand 5 (persisted to `localStorage`) |
| Database ORM | Drizzle ORM 0.45 |
| Auth | Clerk B2B |
| AI Routing | Portkey 3 |
| Code Sandbox | E2B Code Interpreter 2 |

## Agent layer

Four Claude CLI persona agents, each implemented as a Python class extending `BaseAgent`:

| Agent | Output | Key constraint |
|---|---|---|
| PM | `docs/PRD.md` | No code discussion |
| Architect | `docs/TECH_SPEC.md` | No implementation, interfaces only |
| Engineer | `src/`, `tests/`, `scaffold.sh` | Follows Tech Spec Rules of Engagement |
| QA | `reports/BUG_REPORT.md` | Must not fix code — report only |

## Data stores

| Store | Technology | Purpose |
|---|---|---|
| `data/orchestrator.db` | SQLite | Lightweight session metadata |
| `data/checkpoints.db` | SQLite | LangGraph workflow checkpoints |
| PostgreSQL | Managed / Docker | Sessions, artifacts, org configs, AI traces |
| Redis | Managed / Docker | Caching, session management |

## Theme system

The frontend uses CSS custom properties (`--background`, `--foreground`, `--border`, etc.) for all semantic colors. Tailwind utility classes reference these variables. The `ThemeSync` component (inside `Providers`) applies `html.dark` or `html.light` based on the persisted Zustand `theme` value.
