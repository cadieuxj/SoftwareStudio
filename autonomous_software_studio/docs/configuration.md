# Configuration

## Backend environment (`.env`)

Copy `.env.template` to `.env` and fill in the required values.

### Anthropic API keys (one per agent role)

```bash
ANTHROPIC_API_KEY=sk-ant-...         # fallback used by all agents
ANTHROPIC_API_KEY_PM=sk-ant-...      # PM agent   (optional per-role override)
ANTHROPIC_API_KEY_ARCH=sk-ant-...    # Architect   (optional per-role override)
ANTHROPIC_API_KEY_ENG=sk-ant-...     # Engineer    (optional per-role override)
ANTHROPIC_API_KEY_QA=sk-ant-...      # QA          (optional per-role override)
```

### Database

```bash
POSTGRES_USER=softwarestudio
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=softwarestudio
POSTGRES_PORT=5432
DATABASE_URL=postgresql://softwarestudio:<password>@postgres:5432/softwarestudio
```

### Redis

```bash
REDIS_URL=redis://redis:6379/0
```

### Orchestrator tuning

```bash
LOG_LEVEL=INFO            # DEBUG | INFO | WARNING | ERROR
MAX_SESSIONS=100
SESSION_TIMEOUT=3600      # seconds before a session is timed out
MAX_ITERATIONS=5          # max QA → Engineer repair cycles
SESSION_TTL_DAYS=7
ORCHESTRATOR_PORT=8000
SECRET_KEY=<random-32-char-string>
ENABLE_CORS=true
```

### GitHub

```bash
GITHUB_TOKEN=ghp_...            # classic PAT with repo scope
GITHUB_DEFAULT_ORG=your-org     # optional default org
```

### Optional observability

```bash
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=ls__...       # LangSmith (if enabled)
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_USER=admin
GRAFANA_PASSWORD=<password>
```

---

## Frontend environment (`.env.local`)

Copy `frontend/.env.local.example` to `frontend/.env.local`.

### Clerk B2B auth

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_WEBHOOK_SECRET=whsec_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/
```

### Database (Drizzle / node-postgres)

```bash
DATABASE_URL=postgres://softwarestudio:<password>@localhost:5432/softwarestudio
```

### AI gateway and code execution

```bash
PORTKEY_API_KEY=pk-...
PORTKEY_DEFAULT_VIRTUAL_KEY=anthropic-...   # from Portkey dashboard
E2B_API_KEY=e2b_...
```

### Backend proxy

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000   # Python orchestrator URL
```

### Optional

```bash
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
NEXT_PUBLIC_SENTRY_DSN=...
```

---

## YAML configs

Environment-specific config files live in `config/`:

- `config/production.yaml`
- `config/development.yaml`
- `config/testing.yaml`

Validate with:

```bash
python -m src.config.validator --check-all
```

---

## Agent settings

Agent settings (provider, model, API key references, usage limits, active prompt version) are stored per-org in the PostgreSQL `agentConfigs` table, managed through the `/agents` page in the frontend or directly via the orchestrator API (`PATCH /agents/{role}/settings`).

---

## MCP servers

MCP server definitions are in `config/mcp_servers.json`. See `docs/mcp_integration_guide.md` for the full guide.
