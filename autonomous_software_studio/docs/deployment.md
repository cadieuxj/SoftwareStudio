# Deployment Guide

## Architecture overview

The platform has two independently deployed components:

| Component | Hosting | Notes |
|---|---|---|
| **Next.js frontend** | Vercel | Auto-deploys from `main`; see `vercel.json` in repo root |
| **Python orchestrator** | Docker (Railway / Fly.io / ECS / self-hosted) | Port 8000 |
| **PostgreSQL** | Managed DB or Docker | Used by both frontend (Drizzle) and orchestrator |
| **Redis** | Managed or Docker | Caching, session management |

---

## Docker Compose (local / self-hosted)

```bash
cd autonomous_software_studio

# Copy and fill in all secrets
cp .env.template .env

# Start services (orchestrator + postgres + redis)
docker compose up -d

# Verify
docker compose ps
curl http://localhost:8000/healthz
```

### Services defined in `docker-compose.yml`

| Service | Port | Health check |
|---|---|---|
| `postgres` | 5432 | `pg_isready` |
| `redis` | 6379 | `PING` |
| `orchestrator` | 8000 | `GET /healthz` |

> The compose file mounts `./data`, `./logs`, `./docs`, `./reports`, and `./projects`
> into the orchestrator container for state persistence.

### With monitoring stack

```bash
docker compose --profile monitoring up -d
# Prometheus → http://localhost:9090
# Grafana    → http://localhost:3000  (admin / <GRAFANA_PASSWORD>)
```

### Common operations

```bash
docker compose logs -f orchestrator
docker compose restart orchestrator
docker compose build orchestrator && docker compose up -d orchestrator

# Postgres shell
docker compose exec postgres psql -U softwarestudio softwarestudio

# Full teardown (keeps data volumes)
docker compose down

# Full teardown including data (destructive!)
docker compose down -v
```

---

## Vercel deployment (frontend)

The frontend deploys automatically when `main` is updated.

**Required Vercel environment variables** (Settings → Environment Variables):

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
CLERK_SECRET_KEY
CLERK_WEBHOOK_SECRET
DATABASE_URL                  # Neon / Supabase / any managed Postgres
PORTKEY_API_KEY
PORTKEY_DEFAULT_VIRTUAL_KEY
E2B_API_KEY
NEXT_PUBLIC_API_BASE_URL      # URL of the deployed Python orchestrator
```

After deploying, set the Clerk webhook URL in the Clerk dashboard to:
```
https://<your-vercel-domain>/api/webhooks/clerk
```

See the root `README.md` [§12 Vercel Deployment](../../README.md#12-vercel-deployment-frontend) for full details.

---

## Manual local deployment

```bash
# Terminal 1 — Orchestrator
cd autonomous_software_studio
source .venv/bin/activate
python -m src.orchestration.orchestrator --server --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd autonomous_software_studio/frontend
npm run dev
# → http://localhost:3000
```
