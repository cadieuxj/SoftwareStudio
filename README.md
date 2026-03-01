# Sovereign AI — Autonomous Software Studio

Internal engineering reference for the Sovereign AI platform. Everything a developer needs to understand, run, extend, and deploy the system.

---

## Table of Contents

1. [What This Is](#1-what-this-is)
2. [System Architecture](#2-system-architecture)
3. [Repository Layout](#3-repository-layout)
4. [Agent Orchestration](#4-agent-orchestration)
5. [Backend — Python Orchestrator](#5-backend--python-orchestrator)
6. [Frontend — Next.js Application](#6-frontend--nextjs-application)
7. [Database Schema](#7-database-schema)
8. [API Reference](#8-api-reference)
9. [Environment Variables](#9-environment-variables)
10. [Local Development Setup](#10-local-development-setup)
11. [Docker Deployment](#11-docker-deployment)
12. [Vercel Deployment (Frontend)](#12-vercel-deployment-frontend)
13. [Testing](#13-testing)
14. [Common Workflows](#14-common-workflows)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. What This Is

Sovereign AI is a **multi-agent software development platform**. Given a plain-English mission statement, it autonomously:

1. Produces a Product Requirements Document (PRD)
2. Derives a Technical Specification from the PRD
3. Pauses for **human approval** before writing any code
4. Implements the software (code, tests, scaffold script)
5. Runs QA — and if it fails, loops the Engineer back for repairs (max 5 iterations)

The four agents (PM, Architect, Engineer, QA) each run as isolated Claude Code CLI invocations, orchestrated by a LangGraph stateful workflow. A Next.js frontend provides session management, approval flows, artifact viewing, and a live code sandbox.

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Browser / Client                          │
│              Next.js 15 (Vercel / self-hosted)                   │
│   Sessions · Approvals · Artifacts · Agents · Logs · Sandbox     │
└──────────────────────┬───────────────────────────────────────────┘
                       │  REST API calls
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  Next.js API Routes  (:3000)                     │
│  /api/sessions  /api/sandbox  /api/ai/chat  /api/metrics         │
│  Auth: Clerk B2B   DB: Drizzle ORM → PostgreSQL                  │
│  AI routing: Portkey Gateway   Code exec: E2B SDK                │
└──────────────────────┬───────────────────────────────────────────┘
                       │  /api/backend/* (reverse proxy)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│            Python Orchestrator  (:8000)                          │
│            LangGraph StateGraph + Checkpointing                  │
│                                                                  │
│  PM Agent → Architect Agent → [HUMAN GATE] → Engineer → QA      │
│                                     ▲              │             │
│                                     └──────────────┘ (repair)   │
│                                                                  │
│  State store: SQLite (data/orchestrator.db)                      │
│  Workflow checkpoints: SQLite (data/checkpoints.db)              │
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

**Key design decisions:**

| Decision | Why |
|---|---|
| Python backend for orchestration | LangGraph, LangChain, and Claude CLI tooling are Python-native |
| Next.js frontend separate from orchestrator | Independent deploy cadence; Vercel for frontend, any Python host for backend |
| Four separate Claude CLI personas | Enforces role separation; each agent has a distinct profile, API key, and system prompt |
| LangGraph with interrupt | Clean stateful pause at human gate without polling hacks |
| Drizzle ORM on PostgreSQL | Type-safe SQL, fast migrations, multi-tenant row-level isolation by `orgId` |
| Clerk B2B auth | Enterprise org management, SSO, and webhook sync out of the box |
| Portkey gateway | LLM provider abstraction, cost tracking, fallback routing |
| E2B sandboxes | Isolated, ephemeral code execution that can't affect the host |

---

## 3. Repository Layout

```
SoftwareStudio/
├── README.md                          ← you are here
├── vercel.json                        ← Vercel build config
├── package.json                       ← root npm scripts
│
└── autonomous_software_studio/
    ├── README.md                      ← legacy stub (superseded by this file)
    ├── docker-compose.yml             ← full-stack service definitions
    ├── Dockerfile                     ← Python orchestrator image
    ├── Dockerfile.dashboard           ← Streamlit image (legacy UI)
    ├── pyproject.toml                 ← Python project metadata & tool config
    ├── requirements.txt               ← Python dependencies
    ├── .env.template                  ← backend env var template
    │
    ├── src/
    │   ├── orchestration/
    │   │   ├── orchestrator.py        ← main entry point, session manager, HTTP server
    │   │   ├── workflow.py            ← LangGraph StateGraph definition
    │   │   └── state.py               ← AgentState TypedDict (workflow schema)
    │   ├── wrappers/
    │   │   ├── base_agent.py          ← abstract agent class
    │   │   ├── claude_wrapper.py      ← Claude CLI subprocess wrapper
    │   │   ├── pm_agent.py
    │   │   ├── architect_agent.py
    │   │   ├── engineer_agent.py
    │   │   └── qa_agent.py
    │   ├── personas/                  ← system prompts per agent role
    │   ├── interfaces/
    │   │   └── dashboard.py           ← Streamlit UI (legacy, being replaced)
    │   ├── config/                    ← config management helpers
    │   └── mcp/                       ← Model Context Protocol integration
    │
    ├── config/
    │   ├── mcp_servers.json           ← MCP server definitions
    │   └── profiles/
    │       ├── pm/                    ← Claude CLI profile for PM
    │       ├── arch/                  ← Claude CLI profile for Architect
    │       ├── eng/                   ← Claude CLI profile for Engineer
    │       └── qa/                    ← Claude CLI profile for QA
    │
    ├── frontend/                      ← Next.js 15 TypeScript app
    │   ├── next.config.ts
    │   ├── tailwind.config.ts
    │   ├── drizzle.config.ts
    │   ├── package.json
    │   ├── .env.local.example
    │   └── src/
    │       ├── app/                   ← App Router (pages + API routes)
    │       │   ├── layout.tsx
    │       │   ├── page.tsx           ← Dashboard
    │       │   ├── sessions/
    │       │   ├── approvals/
    │       │   ├── agents/
    │       │   ├── artifacts/
    │       │   ├── logs/
    │       │   ├── github/
    │       │   ├── sandbox/
    │       │   └── api/               ← Route handlers
    │       ├── components/
    │       │   ├── layout/            ← Sidebar, Header, MainLayout
    │       │   ├── sessions/          ← CreateSessionModal
    │       │   └── ui/                ← Design system primitives
    │       ├── lib/
    │       │   ├── api.ts             ← API client (sessions, metrics, agents, github)
    │       │   ├── db/                ← Drizzle schema + client
    │       │   ├── e2b.ts             ← E2B sandbox helpers
    │       │   ├── portkey.ts         ← Portkey AI gateway client
    │       │   └── utils.ts           ← cn(), formatDateTime(), etc.
    │       ├── store/                 ← Zustand stores
    │       ├── types/
    │       │   └── index.ts           ← All shared TypeScript types
    │       └── providers.tsx          ← React Query, Clerk, toast providers
    │
    ├── data/                          ← Runtime data (git-ignored)
    │   ├── orchestrator.db            ← SQLite session metadata
    │   └── checkpoints.db             ← LangGraph workflow checkpoints
    ├── docs/                          ← Generated artifacts (PRDs, specs)
    ├── logs/                          ← Execution logs
    ├── reports/                       ← QA reports
    └── tests/
        ├── unit/
        └── integration/
```

---

## 4. Agent Orchestration

### Workflow Graph

```
START
  │
  ▼
[PM Agent]──────────────────── Generates PRD
  │                             → docs/PRD.md  (min 500 words)
  ▼
[Architect Agent]────────────── Generates Tech Spec from PRD
  │                             → docs/TECH_SPEC.md
  ▼
[Human Gate] ◄── INTERRUPT ──── Execution pauses here
  │                             UI shows PRD + Tech Spec for review
  │
  ├─ APPROVE ──────────────────► [Engineer Agent]
  │                               Implements code from spec
  │                               → src/, tests/, scaffold.sh
  │                               ▼
  │                              [QA Agent]
  │                               Tests against PRD + Tech Spec
  │                               → docs/BUG_REPORT.md
  │                               │
  │                               ├─ PASS ──► END (completed)
  │                               │
  │                               └─ FAIL ──► iteration_count++
  │                                           if count < max_iterations:
  │                                             → back to Engineer (repair)
  │                                           else:
  │                                             → human_help state
  │
  ├─ REJECT (arch) ────────────► back to Architect with feedback
  │
  └─ REJECT (prd) ─────────────► back to PM with feedback
```

### The Four Agents

| Agent | Role | Env Key | Output | Key Constraint |
|---|---|---|---|---|
| **PM** | Product requirements | `ANTHROPIC_API_KEY_PM` | `docs/PRD.md` | No code discussion; pure requirements |
| **Architect** | System design | `ANTHROPIC_API_KEY_ARCH` | `docs/TECH_SPEC.md` | No implementation details beyond spec |
| **Engineer** | Code implementation | `ANTHROPIC_API_KEY_ENG` | `src/`, `tests/`, `scaffold.sh` | Must follow Tech Spec "Rules of Engagement" section exactly |
| **QA** | Testing & validation | `ANTHROPIC_API_KEY_QA` | `docs/BUG_REPORT.md` | Must not fix code — only report bugs |

All agents share the same base class interface:
- Receive the full `AgentState` TypedDict as input
- Return a partial `AgentState` update
- Are invoked via `claude_wrapper.py` as subprocess Claude CLI calls
- Timeout after **180 seconds** by default
- Track token costs at Claude claude-opus-4-6 pricing

### LangGraph State Schema (`AgentState`)

```python
class AgentState(TypedDict):
    user_mission: str              # required — never mutated
    project_name: str
    session_id: str
    current_phase: str             # pm | arch | human_gate | eng | qa | complete | failed
    path_prd: str                  # path to generated PRD.md
    path_tech_spec: str            # path to generated TECH_SPEC.md
    path_scaffold_script: str      # path to scaffold.sh
    path_bug_report: str           # path to BUG_REPORT.md
    qa_passed: bool
    iteration_count: int
    max_iterations: int            # default 5
    decision: str                  # approve | reject_arch | reject_prd
    reject_phase: str              # which phase to revert to
    architectural_feedback: list   # accumulated rejection notes for Architect
    prd_feedback: list             # accumulated rejection notes for PM
    execution_log: list            # full execution history
    errors: list
    metadata: dict
```

### Checkpointing & Recovery

- **LangGraph checkpoints** — full workflow state saved to `data/checkpoints.db` after every node
- **Session store** — lightweight metadata in `data/orchestrator.db` (status, phase, timestamps)
- On crash: restart the orchestrator; resume a session by `thread_id = session_id` in LangGraph
- In-memory `MemorySaver` is the fallback if SQLite initialisation fails

---

## 5. Backend — Python Orchestrator

### Entry Point

```bash
python -m src.orchestration.orchestrator --server --host 0.0.0.0 --port 8000
```

### Key Classes

**`Orchestrator`** (`src/orchestration/orchestrator.py`)

```python
orchestrator = Orchestrator()

# Create a session
session_id = await orchestrator.start_new_session("Build a REST API for todo management")

# Human approval
await orchestrator.approve_and_continue(session_id)

# Human rejection with feedback
await orchestrator.reject_and_iterate(session_id, feedback="Needs Redis caching", reject_to="arch")

# Get artifacts
artifacts = await orchestrator.get_artifacts(session_id)
# → { prd: "/path/PRD.md", tech_spec: "/path/TECH_SPEC.md", ... }

# List sessions
sessions = await orchestrator.list_sessions(status="awaiting_approval")
```

**`SessionStore`** — SQLite-backed session metadata store (independent of LangGraph):

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    status TEXT,       -- pending | running | awaiting_approval | completed | failed | expired
    phase TEXT,        -- pm | arch | human_gate | engineer | qa | complete | failed
    mission TEXT,
    project_name TEXT,
    work_dir TEXT,
    created_at TEXT,
    updated_at TEXT,
    qa_passed INTEGER,
    iteration_count INTEGER,
    errors TEXT        -- JSON array
);
```

### HTTP Endpoints (Port 8000)

| Method | Path | Description |
|---|---|---|
| `GET` | `/healthz` | Liveness check → `{"status": "ok"}` |
| `GET` | `/readyz` | Readiness check (tests DB) → `{"status": "ready"}` |
| `GET` | `/metrics` | Prometheus-format metrics |
| `GET` | `/sessions` | List sessions (query: `?status=<status>`) |
| `GET` | `/sessions/{id}` | Get session details |
| `POST` | `/sessions` | Create session — body: `{"mission": "...", "project_name": "..."}` |
| `POST` | `/sessions/{id}/approve` | Approve at human gate |
| `POST` | `/sessions/{id}/reject` | Reject — body: `{"feedback": "...", "reject_phase": "arch"}` |
| `GET` | `/sessions/{id}/artifacts` | Get artifact paths |
| `GET` | `/sessions/{id}/logs` | Execution logs (query: `?limit=100`) |
| `GET` | `/agents/settings` | All agent configurations |
| `GET` | `/agents/{role}/settings` | Agent config for `pm|architect|engineer|qa` |
| `PATCH` | `/agents/{role}/settings` | Update agent config |
| `GET` | `/agents/{role}/prompt` | Active prompt content |
| `POST` | `/agents/{role}/prompt` | Save new prompt version |
| `GET` | `/agents/{role}/prompt/history` | List prompt versions |
| `POST` | `/agents/{role}/prompt/revert` | Revert to a previous version |
| `POST` | `/agents/{role}/prompt/reset` | Reset to default prompt |
| `POST` | `/agents/{role}/usage/reset` | Reset daily usage counter |
| `GET` | `/github/auth` | GitHub auth status |
| `GET` | `/github/repos` | List repos (query: `?org=<org>`) |
| `GET` | `/github/repos/{owner}/{repo}/issues` | List issues |
| `GET` | `/github/repos/{owner}/{repo}/pulls` | List pull requests |
| `POST` | `/github/create-session` | Create session from GitHub issue |

### Prometheus Metrics

```
orchestrator_sessions_total
orchestrator_sessions_by_status{status="running|awaiting_approval|completed|failed"}
orchestrator_approvals_total
orchestrator_rejections_total
```

### MCP Integration

MCP server configurations live in `config/mcp_servers.json`. Each agent profile in `config/profiles/<role>/` can specify which MCP servers it uses. This provides agents with additional tools (filesystem, web search, GitHub API, etc.) beyond base Claude capabilities.

---

## 6. Frontend — Next.js Application

### Stack

| Layer | Library | Version |
|---|---|---|
| Framework | Next.js (App Router) | 15.x |
| Language | TypeScript | 5.x |
| Styling | Tailwind CSS + custom design system | 3.4 |
| UI Primitives | Radix UI | latest |
| Animations | Framer Motion | 11.x |
| Server State | TanStack React Query | 5.x |
| Client State | Zustand | 5.x |
| Database ORM | Drizzle ORM | 0.45 |
| Auth | Clerk B2B | latest |
| AI Routing | Portkey | 3.x |
| Code Sandbox | E2B Code Interpreter | 2.x |
| Charts | Recharts | 2.x |

### Pages (App Router)

| Route | Page | Purpose |
|---|---|---|
| `/` | Dashboard | Metrics overview, live session counts, recent activity |
| `/sessions` | Sessions | Full session list with status filtering |
| `/sessions/[id]` | Session Detail | Live phase tracking, artifact preview, approve/reject actions |
| `/approvals` | Approvals Queue | All sessions in `awaiting_approval` state |
| `/artifacts` | Artifacts Browser | Browse PRDs, tech specs, bug reports |
| `/agents` | Agent Config | Provider settings, API keys, prompt editor with version history |
| `/logs` | Logs | Live execution log stream |
| `/github` | GitHub | OAuth status, repo/issue/PR browser, create-from-issue |
| `/sandbox` | Sandbox | Interactive E2B code execution environment |

### Next.js API Routes

**Sessions**

| Method | Route | Body / Query | Description |
|---|---|---|---|
| `GET` | `/api/sessions` | `?status=` | Proxied to Python backend |
| `POST` | `/api/sessions` | `{mission, project_name?}` | Create session |
| `GET` | `/api/sessions/[id]` | — | Session detail |
| `POST` | `/api/sessions/[id]/approve` | — | Approve |
| `POST` | `/api/sessions/[id]/reject` | `{feedback, reject_phase}` | Reject |
| `GET` | `/api/sessions/[id]/logs` | `?limit=100` | Execution logs |
| `GET` | `/api/sessions/[id]/artifacts` | — | Artifact metadata |

**System**

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/metrics` | Aggregate metrics (from DB) |
| `POST` | `/api/webhooks/clerk` | Clerk org sync webhook |

**Sandbox**

| Method | Route | Body | Description |
|---|---|---|---|
| `POST` | `/api/sandbox` | `{language?}` | Create E2B sandbox |
| `POST` | `/api/sandbox/[id]/execute` | `{code, language?}` | Run code |

**AI Chat**

| Method | Route | Body | Description |
|---|---|---|---|
| `POST` | `/api/ai/chat` | `{messages[], model?}` | Proxied through Portkey |

### Data Flow

```
Page Component
  → useQuery(queryKeys.sessions, sessionsApi.list)
  → lib/api.ts  →  fetch("/api/sessions")
  → Next.js route handler
  → Drizzle query (PostgreSQL)  or  fetch(NEXT_PUBLIC_API_BASE_URL + "/sessions")
  ← typed response matching @/types
```

### Design System

The UI uses a custom professional design system built on Tailwind. Tokens are in `tailwind.config.ts`. Key tokens:

| Token | Value | Usage |
|---|---|---|
| `neon-cyan` | `#6366f1` (Indigo 500) | Primary accent, buttons, active states |
| `neon-magenta` | `#8b5cf6` (Violet 500) | Secondary accent, awaiting status |
| `neon-green` | `#10b981` (Emerald 500) | Success, completed status |
| `neon-orange` | `#f59e0b` (Amber 500) | Warning, pending status |
| `background` | `#09090b` (Zinc 950) | Page background |
| `background-secondary` | `#111113` | Cards, sidebar |

Components live in `src/components/ui/` and are re-exported from `src/components/ui/index.ts`. All are built on Radix UI primitives with Tailwind class overrides.

### State Management

Three Zustand stores in `src/store/`:

- **`useUIStore`** — sidebar open/closed, global UI state
- **`useCreateSessionModal`** — modal open state + prefill values
- **`useAgentSettingsStore`** — selected agent, prompt editor content + dirty flag

---

## 7. Database Schema

Managed by Drizzle ORM. Schema defined in `frontend/src/lib/db/schema.ts`. Run migrations with:

```bash
cd autonomous_software_studio/frontend
npm run db:migrate    # apply pending migrations
npm run db:generate   # generate migration files from schema changes
npm run db:studio     # open Drizzle Studio (visual DB browser)
```

### Tables

**`organizations`**
```
id              uuid PK
clerkOrgId      text UNIQUE      ← from Clerk webhook
name, slug      text
plan            enum(free|pro|enterprise)
maxSessions     int DEFAULT 10
maxSandboxes    int DEFAULT 3
portkeyVirtualKeyId  text        ← per-org AI routing key
createdAt, updatedAt  timestamp
```

**`workspaces`**
```
id              uuid PK
orgId           uuid FK → organizations
name, description  text
repoUrl         text             ← GitHub repo URL
defaultBranch   text DEFAULT 'main'
createdByUserId text             ← Clerk user ID
createdAt, updatedAt  timestamp
```

**`sessions`** — core orchestration sessions
```
id                uuid PK
orgId             uuid FK → organizations
workspaceId       uuid FK → workspaces (nullable)
externalSessionId text             ← matches Python orchestrator session_id
mission           text NOT NULL
projectName       text
status            enum(pending|running|awaiting_approval|completed|failed|expired)
phase             enum(pm|arch|human_gate|engineer|qa|complete|failed)
iterationCount    int DEFAULT 0
qaPassed          boolean DEFAULT false
workDir           text
errors            jsonb
metadata          jsonb
createdAt, updatedAt  timestamp

INDEXES: orgId, status, workspaceId
```

**`artifacts`**
```
id              uuid PK
sessionId       uuid FK → sessions UNIQUE  ← one artifact set per session
orgId           uuid FK → organizations
prd             text             ← full PRD content
techSpec        text
scaffoldScript  text
bugReport       text
testResults     jsonb
filesCreated    jsonb[]
createdAt, updatedAt  timestamp
```

**`agentConfigs`** — per-org per-role agent settings
```
id              uuid PK
orgId           uuid FK → organizations
role            enum(pm|architect|engineer|qa)
                UNIQUE (orgId, role)
provider        text DEFAULT 'anthropic'
model           text DEFAULT 'claude-opus-4-6'
authType        text DEFAULT 'api_key'
apiKeyRef       text             ← encrypted reference, not the raw key
authToken, authTokenEnvVar  text
accountLabel, claudeProfileDir  text
dailyLimit      int
dailyLimitUnit  enum(runs|sessions|minutes)
hardLimit       boolean DEFAULT false
usageToday      int DEFAULT 0
lastReset       timestamp
customEnvVars   jsonb
activePromptVersion  text
promptVersionNote    text
createdAt, updatedAt  timestamp
```

**`sandboxSessions`** — E2B code execution sessions
```
id                uuid PK
orgId             uuid FK → organizations
sessionId         uuid FK → sessions (nullable)
createdByUserId   text
e2bSandboxId      text
templateId        text DEFAULT 'base'
language          text DEFAULT 'python'
status            enum(starting|running|stopped|error)
metadata          jsonb
startedAt, stoppedAt  timestamp
```

**`executions`** — code runs within a sandbox session
```
id                uuid PK
sandboxSessionId  uuid FK → sandboxSessions
orgId             uuid FK → organizations
code              text
stdout, stderr    text
exitCode          int
durationMs        int
results           jsonb
error             text
createdAt         timestamp
```

**`aiTraces`** — Portkey LLM call logs
```
id              uuid PK
orgId           uuid FK → organizations
sessionId       uuid FK → sessions (nullable)
portkeyTraceId  text
model, provider text
promptTokens, completionTokens, totalTokens  int
costUsd         decimal(10,6)
latencyMs       int
status          text
metadata        jsonb
createdAt       timestamp
```

---

## 8. API Reference

See [Section 5](#5-backend--python-orchestrator) for the Python orchestrator's HTTP API and [Section 6](#6-frontend--nextjs-application) for Next.js route handlers.

### Type Definitions

All shared types are in `frontend/src/types/index.ts`. The canonical types that both the API client and pages rely on:

```typescript
type SessionStatus = 'pending' | 'running' | 'awaiting_approval' | 'completed' | 'failed' | 'expired'
type SessionPhase  = 'pm' | 'arch' | 'human_gate' | 'engineer' | 'qa' | 'complete' | 'failed'
type AgentRole     = 'pm' | 'architect' | 'engineer' | 'qa'
type Provider      = 'anthropic' | 'claude_code' | 'groq' | 'openai' | 'azure_openai' | 'custom'

interface Session          { session_id, mission, project_name, status, phase, ... }
interface SessionArtifacts { prd?, tech_spec?, scaffold_script?, bug_report?, test_results?, files_created? }
interface Metrics          { total_sessions, running_sessions, awaiting_approval, completed_sessions,
                             failed_sessions, expired_sessions, qa_passed_count, average_qa_iterations,
                             status_breakdown }
interface AgentSettings    { provider, model, auth_type, api_key?, daily_limit?, ... }
interface PromptVersion    { path, timestamp, note?, content? }
interface GitHubRepo       { name, full_name, description?, html_url, stargazers_count, forks_count, ... }
```

---

## 9. Environment Variables

### Backend (`.env` — copy from `.env.template`)

**Anthropic API Keys** — one per agent role, each can be a separate account:
```bash
ANTHROPIC_API_KEY=sk-ant-...           # fallback for all agents
ANTHROPIC_API_KEY_PM=sk-ant-...        # PM agent (optional override)
ANTHROPIC_API_KEY_ARCH=sk-ant-...      # Architect agent (optional override)
ANTHROPIC_API_KEY_ENG=sk-ant-...       # Engineer agent (optional override)
ANTHROPIC_API_KEY_QA=sk-ant-...        # QA agent (optional override)
```

**Database:**
```bash
POSTGRES_USER=softwarestudio
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=softwarestudio
POSTGRES_PORT=5432
DATABASE_URL=postgresql://softwarestudio:<password>@postgres:5432/softwarestudio
```

**Redis:**
```bash
REDIS_URL=redis://redis:6379/0
REDIS_PORT=6379
```

**GitHub:**
```bash
GITHUB_TOKEN=ghp_...                   # classic PAT with repo scope
GITHUB_DEFAULT_ORG=your-org            # optional default org
```

**Orchestrator tuning:**
```bash
LOG_LEVEL=INFO                         # DEBUG | INFO | WARNING | ERROR
DEBUG_MODE=false
MAX_SESSIONS=100                       # max concurrent sessions
SESSION_TIMEOUT=3600                   # seconds before a session times out
MAX_ITERATIONS=5                       # max QA-Engineer repair cycles
SESSION_TTL_DAYS=7                     # days before session is expired
ORCHESTRATOR_PORT=8000
SECRET_KEY=<random-32-char-string>     # used for session signing
ENABLE_CORS=true                       # set true in dev
```

**Optional observability:**
```bash
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=ls__...              # LangSmith tracing (if enabled)
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_USER=admin
GRAFANA_PASSWORD=<password>
```

### Frontend (`.env.local` — copy from `frontend/.env.local.example`)

**Clerk B2B Authentication:**
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_WEBHOOK_SECRET=whsec_...         # from Clerk dashboard → Webhooks
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/
```

**Database (same PostgreSQL, different connection string format for node-postgres):**
```bash
DATABASE_URL=postgres://softwarestudio:<password>@localhost:5432/softwarestudio
```

**AI & Code Execution:**
```bash
PORTKEY_API_KEY=pk-...
PORTKEY_DEFAULT_VIRTUAL_KEY=anthropic-...   # from Portkey dashboard
E2B_API_KEY=e2b_...
```

**Backend proxy:**
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000   # Python orchestrator URL
```

**Optional:**
```bash
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
NEXT_PUBLIC_SENTRY_DSN=...
```

---

## 10. Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose v2
- `claude` CLI installed (`npm install -g @anthropic-ai/claude-code`)
- PostgreSQL 16 (local or via Docker)
- Redis 7 (local or via Docker)

### Step 1 — Start infrastructure

```bash
cd autonomous_software_studio

# Start only the databases (not the app services)
docker compose up postgres redis -d

# Verify they are healthy
docker compose ps
```

### Step 2 — Backend setup

```bash
cd autonomous_software_studio

# Create virtual environment
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env — at minimum set ANTHROPIC_API_KEY and DATABASE_URL

# Start the orchestrator
python -m src.orchestration.orchestrator --server --host 0.0.0.0 --port 8000

# Verify:
curl http://localhost:8000/healthz
```

### Step 3 — Frontend setup

```bash
cd autonomous_software_studio/frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local — set Clerk keys, DATABASE_URL, PORTKEY_API_KEY, E2B_API_KEY

# Run database migrations
npm run db:migrate

# Start the dev server
npm run dev
# → http://localhost:3000
```

### Step 4 — Clerk webhook (optional for local dev)

Use [ngrok](https://ngrok.com) to forward the Clerk webhook to your local machine:

```bash
ngrok http 3000

# Then in Clerk Dashboard → Webhooks:
# URL: https://<your-ngrok-url>/api/webhooks/clerk
# Events: organization.created, organizationMembership.created
```

### Useful dev commands

```bash
# Frontend
npm run dev          # dev server with hot reload
npm run build        # production build
npm run lint         # ESLint
npx tsc --noEmit     # type check without emitting

# Database
npm run db:generate  # generate new migration from schema changes
npm run db:migrate   # apply migrations
npm run db:studio    # visual DB explorer at http://localhost:4983

# Backend
pytest tests/unit/           # unit tests
pytest tests/integration/    # integration tests (requires running services)
python -m src.orchestration.orchestrator --help
```

---

## 11. Docker Deployment

### Quick Start

```bash
cd autonomous_software_studio

cp .env.template .env
# Fill in all required secrets

docker compose up -d

# Check everything is up
docker compose ps
docker compose logs orchestrator --tail 50
```

### Services

| Service | Image | Port | Health check |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | `pg_isready` |
| `redis` | redis:7-alpine | 6379 | `PING` |
| `orchestrator` | `./Dockerfile` | 8000 | `GET /healthz` |
| `dashboard` | `./Dockerfile.dashboard` | 8501 | Streamlit endpoint |

### With monitoring stack

```bash
docker compose --profile monitoring up -d
# Prometheus → http://localhost:9090
# Grafana    → http://localhost:3000  (admin / <GRAFANA_PASSWORD>)
```

### Common Docker operations

```bash
# View logs
docker compose logs -f orchestrator
docker compose logs -f dashboard

# Restart a single service
docker compose restart orchestrator

# Rebuild after code changes
docker compose build orchestrator
docker compose up -d orchestrator

# Access PostgreSQL shell
docker compose exec postgres psql -U softwarestudio softwarestudio

# Access Redis CLI
docker compose exec redis redis-cli

# Full teardown (preserves volumes)
docker compose down

# Full teardown including data volumes (destructive!)
docker compose down -v
```

### Dockerfile notes

The orchestrator image (`Dockerfile`):
- Base: `python:3.11-slim`
- Installs: PostgreSQL client libs, Node.js, Git, curl
- Installs Claude CLI globally via npm
- Runs as non-root `appuser` (uid 1000)
- Mounts: `data/`, `logs/`, `docs/`, `reports/`, `projects/`
- Default command: `python -m src.orchestration.orchestrator --server --host 0.0.0.0 --port 8000`

---

## 12. Vercel Deployment (Frontend)

The frontend deploys to Vercel independently of the Python backend.

### Build configuration (`vercel.json`)

```json
{
  "buildCommand": "npm run vercel-build",
  "outputDirectory": "autonomous_software_studio/frontend/.next",
  "devCommand": "cd autonomous_software_studio/frontend && npm run dev",
  "regions": ["iad1"]
}
```

`npm run vercel-build` resolves to:
```bash
cd autonomous_software_studio/frontend && npm install && npm run build
```

### Vercel environment variables to set

Set all of the [Frontend environment variables](#frontend-envlocal--copy-from-frontendenvlocalexample) in the Vercel project dashboard under **Settings → Environment Variables**. The key ones:

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
CLERK_SECRET_KEY
CLERK_WEBHOOK_SECRET
DATABASE_URL                        # Neon / Supabase / any hosted Postgres
PORTKEY_API_KEY
PORTKEY_DEFAULT_VIRTUAL_KEY
E2B_API_KEY
NEXT_PUBLIC_API_BASE_URL            # URL of deployed Python backend
```

### Backend hosting for production

The Python orchestrator can run on any host that supports Docker:

| Provider | Notes |
|---|---|
| **Railway** | `railway up` with Dockerfile, easy env var management |
| **Fly.io** | `fly deploy`, supports persistent volumes for `data/` |
| **GCP Cloud Run** | Stateless warning: checkpoints need GCS-backed volume |
| **AWS ECS** | Full control, mount EFS for persistent state |

Set `NEXT_PUBLIC_API_BASE_URL` in Vercel to the deployed backend URL.

### Clerk webhook for production

After deploying, update the Clerk webhook endpoint in the Clerk dashboard to:
```
https://<your-vercel-domain>/api/webhooks/clerk
```

---

## 13. Testing

### Backend tests

```bash
cd autonomous_software_studio
source .venv/bin/activate

# All tests
pytest

# Unit tests only (no external services needed)
pytest tests/unit/ -v

# Integration tests (needs running postgres + redis)
pytest tests/integration/ -v

# With coverage
pytest --cov=src --cov-report=html
```

Test structure:
```
tests/
├── unit/
│   ├── test_orchestrator.py      # session lifecycle
│   ├── test_workflow.py          # LangGraph routing logic
│   ├── test_state.py             # state transitions
│   └── test_agents.py            # agent wrapper logic
└── integration/
    ├── test_full_pipeline.py     # end-to-end with mocked Claude
    └── test_api_endpoints.py     # HTTP endpoint tests
```

### Frontend type checking

Before every commit, run:

```bash
cd autonomous_software_studio/frontend
npx tsc --noEmit      # must exit 0
npm run lint          # ESLint — warnings OK, errors block build
npm run build         # final proof the Vercel build won't fail
```

The CI-equivalent local check that matches Vercel exactly:

```bash
npm run vercel-build  # from repo root
```

---

## 14. Common Workflows

### Create a session programmatically

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"mission": "Build a CLI tool that converts CSV to JSON", "project_name": "csv2json"}'

# Response: { "session_id": "sess_abc123", "status": "pending" }
```

### Poll until human gate

```bash
SESSION_ID="sess_abc123"

while true; do
  STATUS=$(curl -s http://localhost:8000/sessions/$SESSION_ID | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  [ "$STATUS" = "awaiting_approval" ] && break
  sleep 5
done
```

### Approve and wait for completion

```bash
curl -X POST http://localhost:8000/sessions/$SESSION_ID/approve

# Poll for completion
while true; do
  STATUS=$(curl -s http://localhost:8000/sessions/$SESSION_ID | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  [[ "$STATUS" = "completed" || "$STATUS" = "failed" ]] && break
  sleep 10
done
```

### Reject and send feedback

```bash
curl -X POST http://localhost:8000/sessions/$SESSION_ID/reject \
  -H "Content-Type: application/json" \
  -d '{"feedback": "The tech spec needs to use FastAPI, not Flask", "reject_phase": "arch"}'
```

### Update an agent's prompt

```bash
# Save a new version
curl -X POST http://localhost:8000/agents/pm/prompt \
  -H "Content-Type: application/json" \
  -d '{"content": "You are a senior PM...", "note": "Add more emphasis on user stories"}'

# Revert to a previous version
curl -X POST http://localhost:8000/agents/pm/prompt/revert \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/v1.md"}'
```

### Database migration workflow

```bash
# 1. Edit schema in frontend/src/lib/db/schema.ts
# 2. Generate migration
cd autonomous_software_studio/frontend
npm run db:generate

# 3. Review the generated SQL in drizzle/
# 4. Apply to dev
npm run db:migrate

# 5. Apply to production (set DATABASE_URL to prod connection string)
DATABASE_URL=postgres://... npm run db:migrate
```

---

## 15. Troubleshooting

### Build fails: `tsc --noEmit` errors

The most common cause is a mismatch between the API return type and what the page expects. All API types are canonical in `frontend/src/lib/api.ts` and must use types from `frontend/src/types/index.ts`.

```bash
cd autonomous_software_studio/frontend
npx tsc --noEmit 2>&1 | head -40   # look at the first errors
```

Common patterns:
- **`Property 'X' does not exist on type 'Y'`** — the API function returns a raw inline type that doesn't match the shared type. Fix by importing and using the shared type in `api.ts`.
- **`Property 'timestamp' is missing`** — `PromptVersion` requires `timestamp`; the API history endpoint must return `timestamp`, not `date`.

### Orchestrator not starting

```bash
# Check Python dependencies
pip install -r requirements.txt

# Check database connection
psql $DATABASE_URL -c "SELECT 1"

# Check Claude CLI
claude --version

# Run with debug logging
LOG_LEVEL=DEBUG python -m src.orchestration.orchestrator --server
```

### Session stuck in `running`

1. Check orchestrator logs for the thread: `docker compose logs orchestrator | grep <session_id>`
2. If the agent timed out, the session may need to be manually marked failed via direct DB update
3. To recover: restart the orchestrator — LangGraph will resume from the last checkpoint

### Frontend can't reach the backend

Verify `NEXT_PUBLIC_API_BASE_URL` is correct. In dev it should be `http://localhost:8000`. In production it must be the public URL of the deployed Python orchestrator (not `localhost`).

### Clerk webhook not firing

1. Check the endpoint URL in Clerk Dashboard → Webhooks is correct
2. Verify `CLERK_WEBHOOK_SECRET` matches
3. Look at Next.js logs for `/api/webhooks/clerk` — common issue is the raw body not being preserved (must use `req.text()` not `req.json()` for Svix signature verification)

### Docker: postgres fails health check

```bash
docker compose logs postgres | tail -20

# Common fix: remove stale data volume if schema has changed
docker compose down
docker volume rm autonomous_software_studio_postgres_data
docker compose up -d
```

### E2B sandbox creation fails

- Verify `E2B_API_KEY` is set and valid
- E2B sandboxes have a default timeout — create a new one rather than re-using stale sandbox IDs
- Check `frontend/src/lib/e2b.ts` for the `createSandbox()` function — it's server-only

### Portkey errors

- Verify `PORTKEY_API_KEY` and `PORTKEY_DEFAULT_VIRTUAL_KEY` are correct
- The virtual key in Portkey must be mapped to a valid Anthropic (or other) provider key in the Portkey dashboard
- Check AI trace logs in the `aiTraces` table for failed calls

---

*Last updated: 2026-03-01 | Branch: `claude/sovereign-ai-development-0cr6w`*
